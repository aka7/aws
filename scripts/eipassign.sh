#!/bin/bash
# description: Set Public IP from ElasticIP pool during instance startup
# processname: eipassign
# Provides:             eipassign
# Short-Description:    Set Public IP from ElasticIP pool during instance startup
# modified version of Original script taken from : https://gist.github.com/jsianes/034a4e15a8be422c6814
# Abdul Karim - akarim786@gmail.com
# 
 
OUTPUT="text"
REGION="eu-west-1"
IPLOGFILE="/var/log/eipassign.log"
export PATH=/usr/share/pear:/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/opt/aws/bin:/home/ec2-user/bin
 
timestamp() {
  TIMESTAMP=`date -u +"%Y-%m-%dT%H:%M:%S.000Z"`
}
 
write_log() {
  timestamp
  echo "${TIMESTAMP} - ${LOG}" >> ${IPLOGFILE}
}
 
valid_ip() {
  RX='([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])'
  
  if [[ ${EC2PUBLICIP} =~ ^${RX}\.${RX}\.${RX}\.${RX}$ ]]
  then
    VALIDIP=1
  else
    VALIDIP=0
  fi
}
 
check_ec2metadata() {
  ec2-metadata >/dev/null 2>&1
  if [ $? -eq 0 ]
  then
    # Amazon Linux ec2-metadata command found
    EC2INSTANCE=`ec2-metadata -i | awk '{ print $NF; }'`
    EC2PUBLICIP=`ec2-metadata -v | awk '{ print $NF; }'`
  else
    # Checking ec2metadata command
    ec2metadata >/dev/null 2>&1
    if [ $? -eq 0 ]
    then
      # ec2metadata command found
      EC2INSTANCE=`ec2metadata --instance-id`
      EC2PUBLICIP=`ec2metadata --public-ipv4`
    else
      # No ec2metadata/ec2-metadata command found. Trying to obtain using curl requests directly
      IP_AVAILABLE=`curl --connect-timeout 5 -i http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null | grep "200 OK" | wc -l`
      IS_AVAILABLE=`curl --connect-timeout 5 -i http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null | grep "200 OK" | wc -l`
      (( INFO=${IP_AVAILABLE}+${IS_AVAILABLE} ))
  
      if [ ${INFO} -eq 2 ]
      then
        EC2INSTANCE=`curl --connect-timeout 5 http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null`
        EC2PUBLICIP=`curl --connect-timeout 5 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null`
      else
        # ec2metadata/ec2-metadata command not found and unable to obtain metadata info using curl
        LOG="ERROR: Unable to obtain metadata information using ec2metadata/ec2-metadata command or curl requests"; write_log
        exit 127
      fi
    fi
  fi
}
 
check_awscli() {
  aws ec2 describe-addresses --region=${REGION} >/dev/null 2>&1
  
  if [ $? -ne 0 ]
  then
    # Incorrect instance role or invalid AWS CLI configuration
    LOG="ERROR: AWS CLI command not available. Check instance role or AWS CLI installation/configuration"; write_log
    exit 128
  fi
}
 
eipassign() {
  check_ec2metadata
 
  # Check Public IP
  valid_ip
 
  if [ ${VALIDIP} -eq 0 ]
  then
    # No Public IP available. So, AWS CLI unavailable
    LOG="ERROR: There is no Public IP address attached to ${EC2INSTANCE} instance. Unable to use AWS CLI."; write_log
    exit 3
  fi
  
  # Check if AWS CLI is available
  check_awscli
 
  # Check if instance has a public IP from Elastic pool assigned
  PUBLICIPASSIGNED=`aws ec2 describe-addresses --output ${OUTPUT} --region ${REGION} | grep ${EC2INSTANCE} | wc -l`
 
  if [ ${PUBLICIPASSIGNED} -gt 0 ]
  then
    # Instance has (at least) one Pulic IP associated from Elastic pool
    IP=`aws ec2 describe-addresses --output ${OUTPUT} --region ${REGION} | grep ${EC2INSTANCE} | head -1 | awk '{ print $NF; }'`
    LOG="Instance ${EC2INSTANCE} has (at least) one Public IP address from Elastic pool in ${REGION} region (${IP})"; write_log
    exit 4
  else
    # Get IP address from Elastic pool
    IP=`aws ec2 describe-addresses --output ${OUTPUT} --region ${REGION} | grep -v 'i-' | head -1 | awk '{ print $NF; }'`
    AllocationID=`aws ec2 describe-addresses --output ${OUTPUT} --region ${REGION} | grep -v 'i-' | head -1 | awk '{ print $2 }'`
 
    if [ "${IP}" = "" ]
    then
      # Public IP on Elastic pool unavailable
      LOG="ERROR: Free Public IP inside Elastic pool in ${REGION} region unavailable"; write_log
      exit 5
    else
      # Attach Public IP from Elastic pool
      BOOL=0
      aws ec2 associate-address --output ${OUTPUT} --region ${REGION} --instance-id ${EC2INSTANCE} --allocation-id ${AllocationID} >/dev/null 2>&1
      EXITCODE=$?
 
      if [ ${EXITCODE} -eq 0 ]
      then
        LOG="${IP} Public IP from Elastic pool assigned to ${EC2INSTANCE} instance"; write_log
      else
        LOG="ERROR: (${EXITCODE}) Unable to attach ${IP} Public IP from Elastic pool to ${EC2INSTANCE} instance"; write_log
        BOOL=1
      fi
 
      if [ ${BOOL} -eq 0 ]
      then
        # Detaching default Public IP
        aws ec2 disassociate-address --output ${OUTPUT} --region ${REGION} --instance-id ${EC2INSTANCE} --public-ip ${EC2PUBLICIP} >/dev/null 2>&1
        EXITCODE=$?
 
        if [ ${EXITCODE} -eq 0 ] || [ ${EXITCODE} -eq 255 ]
        then
          LOG="Default public IP ${EC2PUBLICIP} outside Elastic pool detached from ${EC2INSTANCE} instance"; write_log
        else
          LOG="ERROR: (${EXITCODE}) Unable to detach default public IP ${EC2PUBLICIP} from ${EC2INSTANCE} instance"; write_log
          BOOL=2
        fi
      fi
      exit ${BOOL}
    fi
  fi
}
eipassign
