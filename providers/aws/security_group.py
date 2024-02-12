import os
from utils.hcl import HCL
from tqdm import tqdm
import sys


class SECURITY_GROUP:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.aws_account_id = aws_account_id
        self.workspace_id = workspace_id
        self.modules = modules
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.s3Bucket = s3Bucket
        self.dynamoDBTable = dynamoDBTable
        self.state_key = state_key
        if not hcl:
            self.hcl = HCL(self.schema_data, self.provider_name)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


        self.processed_security_groups = {}


    def get_vpc_name(self, vpc_id):
        response = self.aws_clients.ec2_client.describe_vpcs(VpcIds=[vpc_id])
        
        # Check if 'Tags' key exists and if it has any tags
        if 'Tags' in response['Vpcs'][0] and response['Vpcs'][0]['Tags']:
            vpc_name = next(
                (tag['Value'] for tag in response['Vpcs'][0]['Tags'] if tag['Key'] == 'Name'), None)
        else:
            # If 'Tags' key doesn't exist or is empty, set vpc_name to None or a default value
            vpc_name = None

        return vpc_name

    def security_group(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_security_group()

        self.hcl.refresh_state()
        
        self.hcl.request_tf_code()


    def aws_security_group(self, security_group_id=None, ftstack=None):
        resource_type = "aws_security_group"

        # If security_group_id is provided, process only that specific security group
        if security_group_id:
            if ftstack and self.hcl.id_resource_processed(resource_type, security_group_id, ftstack):
                tqdm.write(f"  Skipping Security Group: {security_group_id} - already processed")
                return

            try:
                response = self.aws_clients.ec2_client.describe_security_groups(GroupIds=[security_group_id])
                for security_group in response["SecurityGroups"]:
                    self.process_security_group(security_group, ftstack)
                    return security_group["GroupName"]
            except Exception as e:
                tqdm.write(f"Error fetching Security Group {security_group_id}: {e}")
            return

        tqdm.write("Processing Security Groups...")
        response = self.aws_clients.ec2_client.describe_security_groups()
        progress_bar = tqdm(response["SecurityGroups"], desc="Processing Security Groups")
        for security_group in progress_bar:
            progress_bar.set_postfix(security_group=security_group["GroupName"], refresh=True)
            sys.stdout.flush()
            self.process_security_group(security_group, ftstack)

    def process_security_group(self, security_group, ftstack=None):
        resource_type = "aws_security_group"
        if security_group["GroupName"] == "default":
            return

        # Check for Elastic Beanstalk or EKS AutoScaling group
        is_elasticbeanstalk = any(tag['Key'].startswith('elasticbeanstalk:') for tag in security_group.get('Tags', []))
        is_eks = any(tag['Key'].startswith('eks:') for tag in security_group.get('Tags', []))
        if is_elasticbeanstalk or is_eks:
            tqdm.write(f"  Skipping Elastic Beanstalk or EKS AutoScaling Group: {security_group['GroupName']}")
            return

        tqdm.write(f"Processing Security Group: {security_group['GroupName']}")
        vpc_id = security_group.get("VpcId", "")
        id = security_group["GroupId"]

        attributes = {
            "id": id,
            "name": security_group["GroupName"],
            "description": security_group.get("Description", ""),
            "vpc_id": vpc_id,
            "owner_id": security_group.get("OwnerId", ""),
        }

        self.hcl.process_resource(resource_type, security_group["GroupId"].replace("-", "_"), attributes)
        if not ftstack:
            ftstack = "security_group"
        self.hcl.add_stack(resource_type, id, ftstack)

        vpc_name = self.get_vpc_name(vpc_id)
        if vpc_name:
            self.hcl.add_additional_data(resource_type, id, "vpc_name", vpc_name)

        self.aws_vpc_security_group_ingress_rule(security_group["GroupId"], ftstack)
        self.aws_vpc_security_group_egress_rule(security_group["GroupId"], ftstack)


    def aws_vpc_security_group_ingress_rule(self, security_group_id, ftstack=None):
        # Fetch security group rules
        response = self.aws_clients.ec2_client.describe_security_group_rules(
            Filters=[{'Name': 'group-id', 'Values': [security_group_id]}]
        )

        # Process each ingress rule
        for rule in response.get('SecurityGroupRules', []):
            # Filter for ingress rules
            if not rule.get('IsEgress', False):
                rule_id = rule['SecurityGroupRuleId']
                tqdm.write(f"Processing VPC Security Group Ingress Rule {rule_id}...")

                attributes = {
                    "id": rule_id,
                }

                # Process the rule as needed, e.g., storing attributes or creating resources
                self.hcl.process_resource(
                    "aws_vpc_security_group_ingress_rule", rule_id, attributes)
                
                if 'ReferencedGroupInfo' in rule:
                    referenced_security_group_id = rule['ReferencedGroupInfo']['GroupId']
                    self.aws_security_group(referenced_security_group_id, ftstack)

    def aws_vpc_security_group_egress_rule(self, security_group_id, ftstack=None):
        # Fetch security group rules
        response = self.aws_clients.ec2_client.describe_security_group_rules(
            Filters=[{'Name': 'group-id', 'Values': [security_group_id]}]
        )

        # Process each egress rule
        for rule in response.get('SecurityGroupRules', []):
            # Filter for egress rules
            if rule.get('IsEgress', True):
                rule_id = rule['SecurityGroupRuleId']
                tqdm.write(f"Processing VPC Security Group Egress Rule {rule_id}...")

                attributes = {
                    "id": rule_id,
                }

                # Process the rule as needed, e.g., storing attributes or creating resources
                self.hcl.process_resource(
                    "aws_vpc_security_group_egress_rule", rule_id, attributes)
                
                if 'ReferencedGroupInfo' in rule:
                    referenced_security_group_id = rule['ReferencedGroupInfo']['GroupId']
                    self.aws_security_group(referenced_security_group_id, ftstack)
