from ...utils.hcl import HCL
import logging
import inspect

logger = logging.getLogger('finisterra')


class SECURITY_GROUP:
    def __init__(self, progress, aws_clients, script_dir, provider_name, provider_name_short,
                 provider_source, provider_version, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id, output_dir, account_name, hcl=None):
        self.progress = progress

        self.aws_clients = aws_clients
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.aws_account_id = aws_account_id

        self.workspace_id = workspace_id
        self.modules = modules
        if not hcl:
            self.hcl = HCL(self.schema_data)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.output_dir = output_dir
        self.hcl.account_id = aws_account_id

        self.hcl.provider_name = provider_name
        self.hcl.provider_name_short = provider_name_short
        self.hcl.provider_source = provider_source
        self.hcl.provider_version = provider_version
        self.hcl.account_name = account_name

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
        self.hcl.prepare_folder()

        self.aws_security_group()
        self.hcl.module = inspect.currentframe().f_code.co_name
        if self.hcl.count_state():
            self.progress.update(
                self.task, description=f"[cyan]{self.__class__.__name__} [bold]Refreshing state[/]", total=self.progress.tasks[self.task].total+1)
            self.hcl.refresh_state()
            if self.hcl.request_tf_code():
                self.progress.update(
                    self.task, advance=1, description=f"[green]{self.__class__.__name__} [bold]Code Generated[/]")
            else:
                self.progress.update(
                    self.task, advance=1, description=f"[orange3]{self.__class__.__name__} [bold]No code generated[/]")
        else:
            self.task = self.progress.add_task(
                f"[orange3]{self.__class__.__name__} [bold]No resources found[/]", total=1)
            self.progress.update(self.task, advance=1)

    def aws_security_group(self, security_group_id=None, ftstack=None):
        resource_type = "aws_security_group"

        # If security_group_id is provided, process only that specific security group
        if security_group_id:
            if ftstack and self.hcl.id_resource_processed(resource_type, security_group_id, ftstack):
                logger.debug(
                    f"  Skipping Security Group: {security_group_id} - already processed")
                return

            try:
                response = self.aws_clients.ec2_client.describe_security_groups(GroupIds=[
                                                                                security_group_id])
                for security_group in response["SecurityGroups"]:
                    self.process_security_group(security_group, ftstack)
                    return security_group["GroupName"]
            except Exception as e:
                logger.error(
                    f"Error fetching Security Group {security_group_id}: {e}")
            return

        logger.debug("Processing Security Groups...")
        response = self.aws_clients.ec2_client.describe_security_groups()
        if len(response["SecurityGroups"]) > 0:
            self.task = self.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=len(response["SecurityGroups"]))
        for security_group in response["SecurityGroups"]:
            self.process_security_group(security_group, ftstack)
            self.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{security_group['GroupName']}[/]")

    def process_security_group(self, security_group, ftstack=None):
        resource_type = "aws_security_group"
        if security_group["GroupName"] == "default":
            return

        # Check for Elastic Beanstalk or EKS AutoScaling group
        is_elasticbeanstalk = any(tag['Key'].startswith(
            'elasticbeanstalk:') for tag in security_group.get('Tags', []))
        is_eks = any(tag['Key'].startswith('eks:')
                     for tag in security_group.get('Tags', []))
        if is_elasticbeanstalk or is_eks:
            logger.debug(
                f"  Skipping Elastic Beanstalk or EKS AutoScaling Group: {security_group['GroupName']}")
            return

        logger.debug(
            f"Processing Security Group: {security_group['GroupName']}")
        vpc_id = security_group.get("VpcId", "")
        id = security_group["GroupId"]

        attributes = {
            "id": id,
            "name": security_group["GroupName"],
            "description": security_group.get("Description", ""),
            "vpc_id": vpc_id,
            "owner_id": security_group.get("OwnerId", ""),
        }

        self.hcl.process_resource(
            resource_type, security_group["GroupId"].replace("-", "_"), attributes)
        if not ftstack:
            ftstack = "security_group"
        self.hcl.add_stack(resource_type, id, ftstack)

        vpc_name = self.get_vpc_name(vpc_id)
        if vpc_name:
            self.hcl.add_additional_data(
                resource_type, id, "vpc_name", vpc_name)

        self.aws_vpc_security_group_ingress_rule(
            security_group["GroupId"], ftstack)
        self.aws_vpc_security_group_egress_rule(
            security_group["GroupId"], ftstack)

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
                logger.debug(
                    f"Processing VPC Security Group Ingress Rule {rule_id}...")

                attributes = {
                    "id": rule_id,
                }

                # Process the rule as needed, e.g., storing attributes or creating resources
                self.hcl.process_resource(
                    "aws_vpc_security_group_ingress_rule", rule_id, attributes)

                if 'ReferencedGroupInfo' in rule:
                    referenced_security_group_id = rule['ReferencedGroupInfo']['GroupId']
                    self.aws_security_group(
                        referenced_security_group_id, ftstack)

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
                logger.debug(
                    f"Processing VPC Security Group Egress Rule {rule_id}...")

                attributes = {
                    "id": rule_id,
                }

                # Process the rule as needed, e.g., storing attributes or creating resources
                self.hcl.process_resource(
                    "aws_vpc_security_group_egress_rule", rule_id, attributes)

                if 'ReferencedGroupInfo' in rule:
                    referenced_security_group_id = rule['ReferencedGroupInfo']['GroupId']
                    self.aws_security_group(
                        referenced_security_group_id, ftstack)
