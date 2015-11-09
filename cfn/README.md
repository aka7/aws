# AWS CFN templates 

various cfn templates to create vpc subnets in multi availability zones, NAT instances and Bastionhost

Mainly for my reference but may be useful to others as a starting point

###Things to note:

I had VPNGateway setup to connect to office network, which is why there's a VPN gateway section. remove this if you don't need it.

aws-vpc.json 

creates publici & private subnets in 3 AZ.
````
- create the VPC first, thats simple to do. I didn't bother with CFN for that.
- modify the subnetconfig to suit your vpc subnet allocation, ones here are an example subnets
"SubnetConfig" : {
      "VPC"     : { "CIDR" : "10.248.0.0/16" },
      "public-subnet-1a"  : { "CIDR" : "10.248.1.0/24" },
      "private-subnet-1a" : { "CIDR" : "10.248.2.0/24" },
      "public-subnet-1b"  : { "CIDR" : "10.248.3.0/24" },
      "private-subnet-1b" : { "CIDR" : "10.248.4.0/24" },
      "public-subnet-1c"  : { "CIDR" : "10.248.5.0/24" },
      "private-subnet-1c" : { "CIDR" : "10.248.6.0/24" }
    },

- if you have a VPN gateway, then enter the VpnGatewayID, otherwise remove this from the template, 
you will need remove the following.

    "privateVPNGatewayRouteProp" : {
        "Type" : "AWS::EC2::VPNGatewayRoutePropagation",
        "Properties" : {
                "RouteTableIds" : [{"Ref" : "PrivateRouteTableA"},{"Ref" : "PrivateRouteTableB"},{"Ref" : "PrivateRouteTableC"}],
                "VpnGatewayId" : { "Ref" : "VpnGatewayID" }
        }
     },




This gateway is only there to create a static route for your internal supernet into private routing table.

launch aws-vpc.json (provide your vpcid) - creates subnets you specify


launch aws-nat-ha.json  ( provide vpcid and VpcSubnets created by aws-vpc.json)
launch basitionhost.json (if you want a basition/jumphost, provide vpcid and VpcSubnets created by aws-vpc.json)
````

##NOTES on HA NAT isntances:
You will need the amazon provided ha-nat.sh script, uploaded to an private s3 location, and allowed through instance profile see http://docs.aws.amazon.com/codedeploy/latest/userguide/how-to-create-iam-instance-profile.html#getting-started-create-ec2-role-cli

I also used the ipassign script from  http://jsianes.blogspot.co.uk/2014/06/aws-how-to-auto-attach-public-ip-from.html
with some subtle modification to suit my needs.

both scripts are avaiable in scripts directory. 
Please note, I did not write them and would not like to take any credit for it.  I did make subtle modification to suit my requirements.
