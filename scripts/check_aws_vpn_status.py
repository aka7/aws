#!/usr/bin/env python
'''
modified for orignal script done by @author Bommarito Consulting, LLC; http://bommaritollc.com/
@date 20131029
This script monitors and logs to CSV the status of all tunnels for all VPNs for a single EC2 region.
Abdul Karim @1akarim - Modified to iterate through multiple accounts
'''

# Imports
import boto
import boto.ec2
import boto.vpc
import datetime
import csv
import sys,json, yaml, os,re, tempfile
from alerta.api import ApiClient
from alerta.alert import Alert
 
# Set your AWS creds if you aren't using a dotfile or some other boto auth method
aws_access_key_id=None
aws_secret_access_key=None
ec2_region='eu-west-1'

# readonly vpn monitor account
#awsaccounts = {"aws" => {"access_key_id" => "test","secret_access_key" => "test"}}
 
# CSV output file
logpath = "/var/log/"
tempdir = tempfile.gettempdir()

def getAccounts(yfile):
	'''
	load account details from yaml file
	'''
	if not os.path.isfile (yfile):
	  return "" 
	
	f = open(yfile)
	dataMap = yaml.load(f)
	f.close()
	return dataMap
 
def report_tunnel_down(tunnel, vpnid=None):
	'''
	Report and possibly take corrective action.
	'''
	#if vpnid == None:
	#    sys.stderr.write("Tunnel {0} is down since {1}\n"
	#	.format(tunnel.outside_ip_address, tunnel.last_status_change))
	#else:
	#    sys.stderr.write(vpnid+": Tunnel {0} is down since {1}\n"
	#	.format(tunnel.outside_ip_address, tunnel.last_status_change))

def record_status(file,resource):
	'''
	records note of when a tunnel is down
	'''
	f=  open(file,'w')
	f.write(resource)
	f.close()
def get_down_count(file):
	'''
	count number of times its down.
	'''
	f=  open(file,'r')
	num = f.readline()
	f.close()
	return num


def alert_tunnel_down(outside_ip,status_message,last_status_change, aws_acc=None,gwid=None,gwip=None,vpnid=None,severity='minor'):
	'''
	Report tunnel down status to alerta
	only if we haven't already sent an alert
	'''
	api = ApiClient(endpoint='http://monitoring.guprod.gnm:8080')
	alertres = vpnid+','+gwid+','+outside_ip
	status_file =tempdir+'/'+alertres.replace(',','_')+'.down' 
	count = 1
	if os.path.exists(status_file) and not severity == 'critical':
		# if file does exists, it means its already down and an alert has been sent, check number of counts and send again after 10min
		try:
			count = get_down_count(status_file)
			count = int(count) + 1
		except Exception as e:
		  	count = 10
		record_status(status_file,str(count))
		if count >= 5:
			#assume cron is running every 2 min, send down alert every 10 min.	
			count = 1
		else:
			return
	alert = Alert(
	    resource=alertres,
	    event='TunnelDown',
	    correlate=['TunnelUp'],
	    group='aws',
	    environment='PROD',
	    service=[aws_acc],
    	    severity=severity,
    	    value=status_message,
    	    text=aws_acc+' : Tunnel '+outside_ip +' Down since '+last_status_change+'.'+' Guardian endpoint: '+gwip,
    	    tags=['aws'],
    	    attributes={'customer': 'The Guardian', 'account' : aws_acc,'GatewayId' : gwid+' [ '+gwip+' ]','vpnId' : vpnid, 'TunnelOutsideIp' : outside_ip}
	    )
	#print alert
	try:
    		api.send(alert)
		record_status(status_file,str(count))
	except Exception as e:
    		print e
def alert_tunnel_up(outside_ip,status_message,last_status_change, aws_acc=None,gwid=None,gwip=None,vpnid=None):
	'''
	Report tunnel up status to alerta
	only if a down status was sent
	'''
	api = ApiClient(endpoint='http://monitoring.guprod.gnm:8080')
	alertres = vpnid+','+gwid+','+outside_ip
	status_file =tempdir+'/'+alertres.replace(',','_')+'.down' 
	if not os.path.exists(status_file):
	# if file does not exists it means it wasn't down. no point in sending the alert.
		return
	alert = Alert(
	    resource=alertres,
	    event='TunnelUp',
	    correlate=['TunnelDown'],
	    group='aws',
	    environment='PROD',
	    service=[aws_acc],
    	    severity='normal',
    	    value=status_message,
    	    text=aws_acc+' : Tunnel '+outside_ip +' up since '+last_status_change+'.'+'Guardian endpoint: '+gwip,
    	    tags=['aws'],
    	    attributes={'customer': 'The Guardian', 'account' : aws_acc,'GatewayId' : gwid+' [ '+gwip+' ]','vpnId' : vpnid, 'TunnelOutsideIp' : outside_ip}
	    )
	#print alert
	try:
    		api.send(alert)
		os.remove (status_file )
	except Exception as e:
    		print e

def test_tunnel_status(tunnel,aws_acc=None,gwid=None,gwip=None,vpnid=None):
	'''
	Run a test on tunnel status.
	For now, this just trusts the AWS API status and does not perform network-level test.
	'''
	# Check by status string
	if tunnel.status == 'DOWN':
		alert_severity = "major"
		alert_tunnel_down(tunnel.outside_ip_address, tunnel.status_message, str(tunnel.last_status_change),aws_acc,gwid,gwip,vpnid,alert_severity)
		return "DOWN"
	else:
		alert_tunnel_up(tunnel.outside_ip_address, tunnel.status_message, str(tunnel.last_status_change),aws_acc,gwid,gwip,vpnid)
		return "UP"

def change_tunnel_alert_severity(tunnels):
	'''
	 if both tunnels are down, change severity to critical
	'''
	for tunnel in tunnels:
		alert_tunnel_down(tunnel['outside_ip'],tunnel['last_status_change'],tunnel['status_message'],tunnel['accountname'],tunnel['customer_gateway_id'],tunnel['customer_gateway_ip'],tunnel['vpnid'],'critical')
 
def test_vpc_status():
	'''
	Output VPC tunnel status of single account
	'''
	# Create EC2 connection
	ec2_conn = boto.vpc.connect_to_region(ec2_region, 
	aws_access_key_id= aws_access_key_id,
	aws_secret_access_key=aws_secret_access_key)
		
	# Setup the CSV file writer
	with open(csv_file_name, 'a') as csv_file:
		csv_writer = csv.writer(csv_file)
		# Iterate over all VPC connections
		for vpn_connection in ec2_conn.get_all_vpn_connections():
			# Handle connection and its tunnels
			for tunnel in vpn_connection.tunnels:
				# Test the tunnel and output
				status = test_tunnel_status(tunnel,vpn_connection.vpn_gateway_id)
				row = [datetime.datetime.now(), vpn_connection.id, vpn_connection.customer_gateway_id,
					tunnel.outside_ip_address, status, 
					tunnel.status_message, tunnel.last_status_change]
				csv_writer.writerow(row)
def test_multi_vpc_status(awsaccounts):
	'''
	Output VPC tunnel status of multiple account, defined as json 
	exmaple
	awsaccounts = [{"account" :  "aws-account1", "access_key_id" : "test","secret_access_key" : "test"}, {"account" : "aws-account2", "access_key_id" : "test","secret_access_key" : "test"}]
	
	'''
	# Create EC2 connection
	#print json.dumps(awsaccounts, indent=4)
	for acc in awsaccounts:
	    accountname=acc['account']
	    aws_access_key_id=acc['access_key_id']
	    aws_secret_access_key=acc['secret_access_key']
	    
	    ec2_conn = boto.vpc.connect_to_region(ec2_region, 
		aws_access_key_id= aws_access_key_id,
		aws_secret_access_key=aws_secret_access_key)
	
	    # Setup the CSV file writer
	    with open(csv_file_name, 'a') as csv_file:
		csv_writer = csv.writer(csv_file)
		# Iterate over all VPC connections
		for vpn_connection in ec2_conn.get_all_vpn_connections():
			# Handle connection and its tunnels
			downcount = 0 
			downtunnels = []

			for tunnel in vpn_connection.tunnels:
				# Test the tunnel and output
				outside_ip = tunnel.outside_ip_address
				last_status_change = str(tunnel.last_status_change)
				status_message = tunnel.status_message
				customer_gateway_ip = ec2_conn.get_all_customer_gateways(vpn_connection.customer_gateway_id)[0].ip_address
				status = test_tunnel_status(tunnel,accountname,vpn_connection.customer_gateway_id,customer_gateway_ip,vpn_connection.id)

				row = [accountname,datetime.datetime.now(), vpn_connection.id, vpn_connection.customer_gateway_id,
					tunnel.outside_ip_address, status, 
					tunnel.status_message, last_status_change]
				csv_writer.writerow(row)

				if status == "DOWN":
					# keep record of the tunnels down, if all tunnels  are down, we want to increase severity
    	    				downtunnels.append ({'accountname': accountname,'outside_ip' : outside_ip,'last_status_change':last_status_change,'status_message':status_message,'customer_gateway_id':vpn_connection.customer_gateway_id,'customer_gateway_ip': customer_gateway_ip,'vpnid':vpn_connection.id})
					downcount = downcount + 1

			if downcount == len(vpn_connection.tunnels):
				# if both tunnels are down, change severity major
				change_tunnel_alert_severity(downtunnels)
 
if __name__ == "__main__":
	today = str(datetime.date.today())
	csv_file_name = logpath+"aws_vpn_status-"+today+".log"
	awsaccounts = getAccounts('/opt/etc/awsvpnaccounts.yaml')
	if awsaccounts == "":
		test_vpc_status()
	else:
		test_multi_vpc_status(awsaccounts)
	    
