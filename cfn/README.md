# AWS CFN templates 

various cfn templates to create vpc subnets in multi availability zones, NAT instances and Bastionhost

###Things note:

I had VPNGateway setup to connect to office network, which is why there's a VPN gateway section. remove this if you don't need it.

Order of run :
````
- create the VPC first, thats simple to do. I didn't bother with CFN for that.
- if have VPN connection into your office, and have VPN gateway, then enter the vpngateway details,  otherwise remove this from the template, This gateway is only there to create a static route for your internal supernet into private routing table.

launch aws-vpc.json (provide your vpcid) - creates subnets you specify

launch aws-nat-ha.json  ( provide vpcid and VpcSubnets created by aws-vpc.json)
launch basitionhost.json (if you want a basition/jumphost, provide vpcid and VpcSubnets created by aws-vpc.json)
````

##NOTES on HA NAT isntances:
You will need the amazon provided ha-nat.sh script, uploaded to an s3 location, and allowed thorugh instance profile

I also used the ipassign script from  http://jsianes.blogspot.co.uk/2014/06/aws-how-to-auto-attach-public-ip-from.html
with some subtle modification to suit my needs.

both scripts are avaiable in scripts directory. 
Please note, I did not write them and would not like to take any credit for it.  I did make subtle modification to suit my requirements.
