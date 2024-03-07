import os
from utils.hcl import HCL
from providers.aws.security_group import SECURITY_GROUP
from providers.aws.acm import ACM
from providers.aws.s3 import S3
from tqdm import tqdm
import sys
# from providers.aws.target_group import TargetGroup


class ELBV2:
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
        self.s3Bucket = s3Bucket
        self.dynamoDBTable = dynamoDBTable
        self.state_key = state_key
        self.aws_account_id = aws_account_id

        self.modules = modules
        if not hcl:
            self.hcl = HCL(self.schema_data, self.provider_name)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.account_id = aws_account_id

        self.listeners = {}


        self.security_group_instance = SECURITY_GROUP(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.acm_instance = ACM(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.s3_instance = S3(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        # self.target_group_instance = TargetGroup(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        
    def get_subnet_names(self, subnet_ids):
        subnets_info = []
        for subnet_id in subnet_ids:
            response = self.aws_clients.ec2_client.describe_subnets(SubnetIds=[subnet_id])

            # Check if 'Subnets' key exists and it's not empty
            if not response or 'Subnets' not in response or not response['Subnets']:
                tqdm.write(f"No subnet information found for Subnet ID: {subnet_id}")
                continue

            subnet_info = response['Subnets'][0]
            subnet_tags = subnet_info.get('Tags', [])

            # Extract the subnet name from the tags
            subnet_name = next(
                (tag['Value'] for tag in subnet_tags if tag['Key'] == 'Name'), None)

            # Extract the CIDR block
            subnet_cidr = subnet_info.get('CidrBlock', None)

            if subnet_name and subnet_cidr:
                subnets_info.append({'name': subnet_name, 'cidr_block': subnet_cidr})
            else:
                tqdm.write(f"No 'Name' tag or CIDR block found for Subnet ID: {subnet_id}")

        return subnets_info
    
    def get_vpc_name(self, vpc_id):
        response = self.aws_clients.ec2_client.describe_vpcs(VpcIds=[vpc_id])

        if not response or 'Vpcs' not in response or not response['Vpcs']:
            # Handle this case as required, for example:
            tqdm.write(f"No VPC information found for VPC ID: {vpc_id}")
            return None

        vpc_tags = response['Vpcs'][0].get('Tags', [])
        vpc_name = next((tag['Value']
                        for tag in vpc_tags if tag['Key'] == 'Name'), None)

        if vpc_name is None:
            tqdm.write(f"No 'Name' tag found for VPC ID: {vpc_id}")

        return vpc_name    

    def elbv2(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_lb()

        self.hcl.refresh_state()

        self.hcl.request_tf_code()


    def aws_lb(self, selected_lb_arn=None, ftstack=None):
        resource_type = "aws_lb"
        tqdm.write("Processing Load Balancers...")

        if selected_lb_arn and ftstack:
            if self.hcl.id_resource_processed(resource_type, selected_lb_arn, ftstack):
                tqdm.write(f"  Skipping Elbv2: {selected_lb_arn} already processed")
                return
            self.process_single_lb(selected_lb_arn, ftstack)
            return

        load_balancers = self.aws_clients.elbv2_client.describe_load_balancers()["LoadBalancers"]
        self.task = self.progress.add_task(f"[cyan]Processing {self.__class__.__name__}...", total=len(load_balancers)+2)
        
        for lb in load_balancers:
            lb_arn = lb["LoadBalancerArn"]
            self.progress.update(self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{lb['LoadBalancerName']}[/]")
            self.process_single_lb(lb_arn, ftstack)

    def process_single_lb(self, lb_arn, ftstack=None):
        resource_type = "aws_lb"
        lb_response = self.aws_clients.elbv2_client.describe_load_balancers(LoadBalancerArns=[lb_arn])
        if not lb_response["LoadBalancers"]:
            return

        lb = lb_response["LoadBalancers"][0]
        lb_name = lb["LoadBalancerName"]

        # if lb_name != "a2279fadf4d074581a4f67afec193962":
        #     return

        # Check tags of the load balancer
        tags_response = self.aws_clients.elbv2_client.describe_tags(ResourceArns=[lb_arn])
        tags = tags_response["TagDescriptions"][0]["Tags"]

        # Filter out load balancers created by Elastic Beanstalk or Kubernetes Ingress
        is_ebs_created = any(tag["Key"] == "elasticbeanstalk:environment-name" for tag in tags)
        is_k8s_created = any(tag["Key"] in ["kubernetes.io/ingress-name", "kubernetes.io/ingress.class", "elbv2.k8s.aws/cluster"] for tag in tags)

        if is_ebs_created:
            tqdm.write(f"  Skipping Elastic Beanstalk Load Balancer: {lb_name}")
            return
        elif is_k8s_created:
            tqdm.write(f"  Skipping Kubernetes Load Balancer: {lb_name}")
            return

        tqdm.write(f"Processing Load Balancer: {lb_name}")

        if not ftstack:
            ftstack = "elbv2"
            for tag in tags:
                if tag['Key'] == 'ftstack':
                    if tag['Value'] != 'elbv2':
                        ftstack = "stack_" + tag['Value']
                    break

        id = lb_arn

        attributes = {
            "id": id,
        }

        self.hcl.process_resource(resource_type, lb_name, attributes)
        self.hcl.add_stack(resource_type, id, ftstack)

        AvailabilityZones = lb.get("AvailabilityZones", [])
        if AvailabilityZones:
            subnets = self.get_subnet_names([az["SubnetId"] for az in AvailabilityZones])
            if subnets:
                if resource_type not in self.hcl.additional_data:
                    self.hcl.additional_data[resource_type] = {}
                if id not in self.hcl.additional_data[resource_type]:
                    self.hcl.additional_data[resource_type][id] = {}
                self.hcl.additional_data[resource_type][id]["subnet_names"] = subnets

        VpcId = lb.get("VpcId", "")
        if VpcId:
            vpc_name = self.get_vpc_name(VpcId)
            if vpc_name:
                if resource_type not in self.hcl.additional_data:
                    self.hcl.additional_data[resource_type] = {}
                if id not in self.hcl.additional_data[resource_type]:
                    self.hcl.additional_data[resource_type][id] = {}
                self.hcl.additional_data[resource_type][id]["vpc_name"] = vpc_name

        # load_balancer_arns.append(lb_arn)

        # Extract the security group IDs associated with this load balancer
        security_group_ids = lb.get("SecurityGroups", [])

        # Call the aws_security_group function for each security group ID
        # Block because we want to create the security groups in their own module
        for sg in security_group_ids:
            self.security_group_instance.aws_security_group(sg, ftstack)

        access_logs = self.aws_clients.elbv2_client.describe_load_balancer_attributes(
            LoadBalancerArn=lb_arn
        )['Attributes']

        s3_access_logs_enabled = False
        s3_access_lobs_bucket = ""
        for attribute in access_logs:
            if attribute['Key'] == 'access_logs.s3.enabled' and attribute['Value'] == 'true':
                s3_access_logs_enabled = True
            if attribute['Key'] == 'access_logs.s3.bucket':
                s3_access_lobs_bucket = attribute['Value']
        if s3_access_logs_enabled and s3_access_lobs_bucket:
            self.s3_instance.aws_s3_bucket(s3_access_lobs_bucket, ftstack)
        self.aws_lb_listener([lb_arn], ftstack)

    def aws_lb_listener(self, load_balancer_arns, ftstack=None):
        tqdm.write("Processing Load Balancer Listeners...")

        for lb_arn in load_balancer_arns:
            paginator = self.aws_clients.elbv2_client.get_paginator("describe_listeners")
            for page in paginator.paginate(LoadBalancerArn=lb_arn):
                for listener in page["Listeners"]:
                    listener_arn = listener["ListenerArn"]                    
                    # listener_arns.append(listener_arn)

                    tqdm.write(f"Processing Listener: {listener_arn}")

                    attributes = {
                        "id": listener_arn,
                    }

                    self.hcl.process_resource(
                        "aws_lb_listener", listener_arn.split("/")[-1], attributes)
                    
                    for certificate in listener.get('Certificates', []):
                        self.acm_instance.aws_acm_certificate(certificate['CertificateArn'], ftstack)

                    # default_action = listener.get('DefaultActions', [])
                    # for action in default_action:
                    #     target_group_arn = action.get('TargetGroupArn')
                    #     if target_group_arn:
                    #         self.target_group_instance.aws_lb_target_group(target_group_arn, ftstack)
                    #         exit()


    def aws_lb_listener_certificate(self, listener_arns, ftstack):
        tqdm.write("Processing Load Balancer Listener Certificates...")

        for listener_arn in listener_arns:
            listener_certificates = self.aws_clients.elbv2_client.describe_listener_certificates(
                ListenerArn=listener_arn)

            if "Certificates" in listener_certificates:
                certificates = listener_certificates["Certificates"]

                for cert in certificates:
                    if cert.get("IsDefault", False):  # skip default certificates
                        continue

                    cert_arn = cert["CertificateArn"]
                    cert_id = cert_arn.split("/")[-1]
                    tqdm.write(
                        f"Processing Load Balancer Listener Certificate: {cert_id} for Listener ARN: {listener_arn}")

                    id = listener_arn + "_" + cert_arn
                    attributes = {
                        "id": id,
                        "certificate_arn": cert_arn,
                        "listener_arn": listener_arn,
                    }

                    self.hcl.process_resource(
                        "aws_lb_listener_certificate", id, attributes)
                    
                    self.acm_instance.aws_acm_certificate(cert_arn, ftstack)
            else:
                tqdm.write(
                    f"No certificates found for Listener ARN: {listener_arn}")

