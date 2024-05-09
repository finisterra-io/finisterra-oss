from ...utils.hcl import HCL
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.acm import ACM
from ...providers.aws.s3 import S3
from ...providers.aws.target_group import TargetGroup
from ...providers.aws.utils import get_subnet_names
import logging
import inspect

logger = logging.getLogger('finisterra')


class ELBV2:
    def __init__(self, provider_instance, hcl=None):
        self.provider_instance=provider_instance
        if not hcl:
            self.hcl = HCL(self.provider_instance.schema_data)
        else:
            self.hcl = hcl

        self.hcl.region = self.provider_instance.region
        self.hcl.output_dir = self.provider_instance.output_dir
        self.hcl.account_id = self.provider_instance.aws_account_id

        self.hcl.provider_name = self.provider_instance.provider_name
        self.hcl.provider_name_short = self.provider_instance.provider_name_short
        self.hcl.provider_source = self.provider_instance.provider_source
        self.hcl.provider_version = self.provider_instance.provider_version
        self.hcl.account_name = self.provider_instance.account_name

        self.listeners = {}

        self.security_group_instance = SECURITY_GROUP(self.provider_instance, self.hcl)
        self.acm_instance = ACM(self.provider_instance, self.hcl)
        self.s3_instance = S3(self.provider_instance, self.hcl)
        self.target_group_instance = TargetGroup(self.provider_instance, self.hcl)

    def get_vpc_name(self, vpc_id):
        response = self.provider_instance.aws_clients.ec2_client.describe_vpcs(VpcIds=[vpc_id])

        if not response or 'Vpcs' not in response or not response['Vpcs']:
            # Handle this case as required, for example:
            logger.debug(f"No VPC information found for VPC ID: {vpc_id}")
            return None

        vpc_tags = response['Vpcs'][0].get('Tags', [])
        vpc_name = next((tag['Value']
                        for tag in vpc_tags if tag['Key'] == 'Name'), None)

        if vpc_name is None:
            logger.debug(f"No 'Name' tag found for VPC ID: {vpc_id}")

        return vpc_name

    def elbv2(self):
        self.hcl.prepare_folder()

        self.aws_lb()
        self.hcl.module = inspect.currentframe().f_code.co_name
        if self.hcl.count_state():
            self.provider_instance.progress.update(
                self.task, description=f"[cyan]{self.__class__.__name__} [bold]Refreshing state[/]", total=self.provider_instance.progress.tasks[self.task].total+1)
            self.hcl.refresh_state()
            if self.hcl.request_tf_code():
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[green]{self.__class__.__name__} [bold]Code Generated[/]")
            else:
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[orange3]{self.__class__.__name__} [bold]No code generated[/]")
        else:
            self.task = self.provider_instance.progress.add_task(
                f"[orange3]{self.__class__.__name__} [bold]No resources found[/]", total=1)
            self.provider_instance.progress.update(self.task, advance=1)

    def aws_lb(self, selected_lb_arn=None, ftstack=None):
        resource_type = "aws_lb"
        logger.debug("Processing Load Balancers...")

        if selected_lb_arn and ftstack:
            if self.hcl.id_resource_processed(resource_type, selected_lb_arn, ftstack):
                logger.debug(
                    f"  Skipping Elbv2: {selected_lb_arn} already processed")
                return

        if selected_lb_arn:
            load_balancers = self.provider_instance.aws_clients.elbv2_client.describe_load_balancers(LoadBalancerArns=[selected_lb_arn])[
                "LoadBalancers"]
        else:
            load_balancers = self.provider_instance.aws_clients.elbv2_client.describe_load_balancers()[
                "LoadBalancers"]

        self.task = None

        total = 0
        for lb in load_balancers:
            lb_arn = lb["LoadBalancerArn"]
            lb_name = lb["LoadBalancerName"]

            # Check tags of the load balancer
            tags_response = self.provider_instance.aws_clients.elbv2_client.describe_tags(ResourceArns=[
                                                                        lb_arn])
            tags = tags_response["TagDescriptions"][0]["Tags"]

            # Filter out load balancers created by Elastic Beanstalk or Kubernetes Ingress
            is_ebs_created = any(
                tag["Key"] == "elasticbeanstalk:environment-name" for tag in tags)
            is_k8s_created = any(tag["Key"] in ["kubernetes.io/ingress-name",
                                                "kubernetes.io/ingress.class", "elbv2.k8s.aws/cluster"] for tag in tags)

            if is_ebs_created:
                continue
            elif is_k8s_created:
                logger.debug(f"  Skipping Kubernetes Load Balancer: {lb_name}")
                continue

            total = total + 1

        for lb in load_balancers:
            resource_type = "aws_lb"
            lb_arn = lb["LoadBalancerArn"]
            lb_name = lb["LoadBalancerName"]

            # Check tags of the load balancer
            tags_response = self.provider_instance.aws_clients.elbv2_client.describe_tags(ResourceArns=[
                                                                        lb_arn])
            tags = tags_response["TagDescriptions"][0]["Tags"]

            # Filter out load balancers created by Elastic Beanstalk or Kubernetes Ingress
            is_ebs_created = any(
                tag["Key"] == "elasticbeanstalk:environment-name" for tag in tags)
            is_k8s_created = any(tag["Key"] in ["kubernetes.io/ingress-name",
                                                "kubernetes.io/ingress.class", "elbv2.k8s.aws/cluster"] for tag in tags)

            if is_ebs_created:
                logger.debug(
                    f"  Skipping Elastic Beanstalk Load Balancer: {lb_name}")
                continue
            elif is_k8s_created:
                logger.debug(f"  Skipping Kubernetes Load Balancer: {lb_name}")
                continue

            logger.debug(f"Processing Load Balancer: {lb_name}")

            if not selected_lb_arn:
                if not self.task:
                    self.task = self.provider_instance.progress.add_task(
                        f"[cyan]Processing {self.__class__.__name__}...", total=total)

                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{lb['LoadBalancerName']}[/]")

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
                subnets = get_subnet_names(self.provider_instance.aws_clients,
                                           [az["SubnetId"] for az in AvailabilityZones])
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

            access_logs = self.provider_instance.aws_clients.elbv2_client.describe_load_balancer_attributes(
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
        logger.debug("Processing Load Balancer Listeners...")

        for lb_arn in load_balancer_arns:
            paginator = self.provider_instance.aws_clients.elbv2_client.get_paginator(
                "describe_listeners")
            for page in paginator.paginate(LoadBalancerArn=lb_arn):
                for listener in page["Listeners"]:
                    listener_arn = listener["ListenerArn"]
                    # listener_arns.append(listener_arn)

                    logger.debug(f"Processing Listener: {listener_arn}")

                    attributes = {
                        "id": listener_arn,
                    }

                    self.hcl.process_resource(
                        "aws_lb_listener", listener_arn.split("/")[-1], attributes)

                    for certificate in listener.get('Certificates', []):
                        self.acm_instance.aws_acm_certificate(
                            certificate['CertificateArn'], ftstack)

                    default_action = listener.get('DefaultActions', [])
                    for action in default_action:
                        target_group_arn = action.get('TargetGroupArn')
                        if target_group_arn:
                            self.target_group_instance.aws_lb_target_group(
                                target_group_arn, ftstack)

    def aws_lb_listener_certificate(self, listener_arns, ftstack):
        logger.debug("Processing Load Balancer Listener Certificates...")

        for listener_arn in listener_arns:
            listener_certificates = self.provider_instance.aws_clients.elbv2_client.describe_listener_certificates(
                ListenerArn=listener_arn)

            if "Certificates" in listener_certificates:
                certificates = listener_certificates["Certificates"]

                for cert in certificates:
                    if cert.get("IsDefault", False):  # skip default certificates
                        continue

                    cert_arn = cert["CertificateArn"]
                    cert_id = cert_arn.split("/")[-1]
                    logger.debug(
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
                logger.debug(
                    f"No certificates found for Listener ARN: {listener_arn}")
