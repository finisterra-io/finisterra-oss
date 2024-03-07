import os
import botocore
from utils.hcl import HCL
from providers.aws.security_group import SECURITY_GROUP
from providers.aws.kms import KMS
from providers.aws.acm import ACM
from providers.aws.logs import Logs

class Elasticsearch:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.workspace_id = workspace_id
        self.modules = modules
        self.hcl = HCL(self.schema_data, self.provider_name)
        self.aws_account_id = aws_account_id

        self.hcl.region = region
        self.hcl.account_id = aws_account_id



        self.security_group_instance = SECURITY_GROUP(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.kms_instance = KMS(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.acm_instance = ACM(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.logs_instance = Logs(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        
    def get_vpc_name(self, vpc_options):
        vpc_name = None
        vpc_id = None
        if vpc_options:
            subnets = vpc_options.get("SubnetIds")
            if subnets:
                #get the vpc id for the first subnet
                subnet_id = subnets[0]
                response = self.aws_clients.ec2_client.describe_subnets(SubnetIds=[subnet_id])
                vpc_id = response['Subnets'][0]['VpcId']
        if vpc_id:
            response = self.aws_clients.ec2_client.describe_vpcs(VpcIds=[vpc_id])
            if not response or 'Vpcs' not in response or not response['Vpcs']:
                # Handle this case as required, for example:
                print(f"No VPC information found for VPC ID: {vpc_id}")
                return None

            vpc_tags = response['Vpcs'][0].get('Tags', [])
            vpc_name = next((tag['Value']
                            for tag in vpc_tags if tag['Key'] == 'Name'), None)
        return vpc_name
        
    def get_subnet_names(self, subnet_ids):
        subnet_names = []
        for subnet_id in subnet_ids:
            response = self.aws_clients.ec2_client.describe_subnets(SubnetIds=[subnet_id])

            # Check if 'Subnets' key exists and it's not empty
            if not response or 'Subnets' not in response or not response['Subnets']:
                print(
                    f"No subnet information found for Subnet ID: {subnet_id}")
                continue

            # Extract the 'Tags' key safely using get
            subnet_tags = response['Subnets'][0].get('Tags', [])

            # Extract the subnet name from the tags
            subnet_name = next(
                (tag['Value'] for tag in subnet_tags if tag['Key'] == 'Name'), None)

            if subnet_name:
                subnet_names.append(subnet_name)
            else:
                print(f"No 'Name' tag found for Subnet ID: {subnet_id}")

        return subnet_names
        
    def get_kms_alias(self, kms_key_id):
        try:
            value = ""
            response = self.aws_clients.kms_client.list_aliases()
            aliases = response.get('Aliases', [])
            while 'NextMarker' in response:
                response = self.aws_clients.kms_client.list_aliases(Marker=response['NextMarker'])
                aliases.extend(response.get('Aliases', []))
            for alias in aliases:
                if 'TargetKeyId' in alias and alias['TargetKeyId'] == kms_key_id.split('/')[-1]:
                    value = alias['AliasName']
                    break
            return value
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'AccessDeniedException':
                return ""
            else:
                raise e
        
    def elasticsearch(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_elasticsearch_domain()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()

    def aws_elasticsearch_domain(self):
        resource_type = "aws_elasticsearch_domain"
        print("Processing OpenSearch Domain...")

        domains = self.aws_clients.elasticsearch_client.list_domain_names()["DomainNames"]
        for domain in domains:
            domain_name = domain["DomainName"]
            domain_info = self.aws_clients.elasticsearch_client.describe_elasticsearch_domain(DomainName=domain_name)[
                "DomainStatus"]
            arn = domain_info["ARN"]
            print(f"Processing OpenSearch Domain: {domain_name}")

            id = arn

            attributes = {
                "id": id,
                "domain_name": domain_name,
            }

            # Get the tags of the domain
            tags_response = self.aws_clients.elasticsearch_client.list_tags(
                ARN=arn
            )
            tags = tags_response.get("TagList", [])

            formated_tags = {}
            for tag in tags:
                key = tag["Key"]
                value = tag["Value"]
                formated_tags[key] = value
            if formated_tags:
                self.hcl.add_additional_data(resource_type, id, "tags", formated_tags)

            ftstack = "elasticsearch"    
            for tag in tags:
                key = tag["Key"]
                if key == "ftstack":
                    ftstack = tag["Value"]
                    break

            # Process the domain resource
            self.hcl.process_resource(
                resource_type, id, attributes)

            self.hcl.add_stack(resource_type, id, ftstack)

            vpc_options = domain_info.get('VPCOptions', {})
            if vpc_options:
                security_groups = vpc_options.get(
                    'SecurityGroupIds', [])
                for sg in security_groups:
                    self.security_group_instance.aws_security_group(sg, ftstack)

                vpc_name = self.get_vpc_name(vpc_options)
                if vpc_name:
                    self.hcl.add_additional_data(resource_type, id, "vpc_name", vpc_name)

                subnet_ids = vpc_options.get(
                    'SubnetIds', [])
                if subnet_ids:
                    subnet_names = self.get_subnet_names(subnet_ids)
                    if subnet_names:
                        self.hcl.add_additional_data(resource_type, id, "subnet_names", subnet_names)

            encrypt_at_rest = domain_info.get('EncryptionAtRestOptions', {})
            if encrypt_at_rest:
                kmsKeyId = encrypt_at_rest.get('KmsKeyId', None)
                if kmsKeyId:
                    self.kms_instance.aws_kms_key(kmsKeyId, ftstack)
                    kms_key_alias = self.get_kms_alias(kmsKeyId)
                    if kms_key_alias:
                        self.hcl.add_additional_data(resource_type, id, "kms_key_alias", kms_key_alias)      

            domain_endpoint_options = domain_info.get('DomainEndpointOptions', {})
            if domain_endpoint_options:
                custom_endpoint_certificate_arn = domain_endpoint_options.get(
                    'CustomEndpointCertificateArn', None)
                if custom_endpoint_certificate_arn:
                    self.acm_instance.aws_acm_certificate(custom_endpoint_certificate_arn, ftstack)

            log_publishing_options = domain_info.get('LogPublishingOptions', {})
            for key,data  in log_publishing_options.items():
                cloudwatch_log_group_arn = data.get(
                    'CloudWatchLogsLogGroupArn', None)
                if cloudwatch_log_group_arn:
                    log_group_name = cloudwatch_log_group_arn.split(':')[-1]
                    self.logs_instance.aws_cloudwatch_log_group(log_group_name, ftstack)

            

            # self.aws_elasticsearch_domain_policy(domain_name)

    # Updated function signature
    def aws_elasticsearch_domain_policy(self, domain_name):
        print("Processing OpenSearch Domain Policy...")

        # Since the domain is already known, we don't need to retrieve all domains
        domain_info = self.aws_clients.elasticsearch_client.describe_elasticsearch_domain(DomainName=domain_name)[
            "DomainStatus"]
        arn = domain_info["ARN"]
        # access_policy = domain_info["AccessPolicies"]
        print(f"Processing OpenSearch Domain Policy: {domain_name}")

        id = domain_name

        attributes = {
            "id": id,
            "domain_name": id,
        }

        # Process the policy resource
        self.hcl.process_resource(
            "aws_elasticsearch_domain_policy", id, attributes)

