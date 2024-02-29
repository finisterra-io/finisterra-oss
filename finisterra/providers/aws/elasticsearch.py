import botocore
from ...utils.hcl import HCL
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.kms import KMS
from ...providers.aws.acm import ACM
from ...providers.aws.logs import Logs
from ...providers.aws.utils import get_subnet_names
import logging
import inspect

logger = logging.getLogger('finisterra')


class Elasticsearch:
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

        self.security_group_instance = SECURITY_GROUP(self.progress,  self.aws_clients, script_dir, provider_name, provider_name_short, provider_source, provider_version, schema_data,
                                                      region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, output_dir, account_name, self.hcl)
        self.kms_instance = KMS(self.progress,  self.aws_clients, script_dir, provider_name, provider_name_short, provider_source, provider_version, schema_data, region,
                                s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, output_dir, account_name, self.hcl)
        self.acm_instance = ACM(self.progress,  self.aws_clients, script_dir, provider_name, provider_name_short, provider_source, provider_version, schema_data, region,
                                s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, output_dir, account_name, self.hcl)
        self.logs_instance = Logs(self.progress,  self.aws_clients, script_dir, provider_name, provider_name_short, provider_source, provider_version, schema_data, region,
                                  s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, output_dir, account_name, self.hcl)

    def get_vpc_name(self, vpc_options):
        vpc_name = None
        vpc_id = None
        if vpc_options:
            subnets = vpc_options.get("SubnetIds")
            if subnets:
                # get the vpc id for the first subnet
                subnet_id = subnets[0]
                response = self.aws_clients.ec2_client.describe_subnets(SubnetIds=[
                                                                        subnet_id])
                vpc_id = response['Subnets'][0]['VpcId']
        if vpc_id:
            response = self.aws_clients.ec2_client.describe_vpcs(VpcIds=[
                                                                 vpc_id])
            if not response or 'Vpcs' not in response or not response['Vpcs']:
                # Handle this case as required, for example:
                logger.debug(f"No VPC information found for VPC ID: {vpc_id}")
                return None

            vpc_tags = response['Vpcs'][0].get('Tags', [])
            vpc_name = next((tag['Value']
                            for tag in vpc_tags if tag['Key'] == 'Name'), None)
        return vpc_name

    def get_kms_alias(self, kms_key_id):
        try:
            value = ""
            response = self.aws_clients.kms_client.list_aliases()
            aliases = response.get('Aliases', [])
            while 'NextMarker' in response:
                response = self.aws_clients.kms_client.list_aliases(
                    Marker=response['NextMarker'])
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
        self.hcl.prepare_folder()

        self.aws_elasticsearch_domain()
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

    def aws_elasticsearch_domain(self):
        resource_type = "aws_elasticsearch_domain"
        logger.debug("Processing OpenSearch Domain...")

        domains = self.aws_clients.elasticsearch_client.list_domain_names()[
            "DomainNames"]
        if len(domains) > 0:
            self.task = self.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=len(domains))

        for domain in domains:
            domain_name = domain["DomainName"]
            self.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{domain_name}[/]")
            domain_info = self.aws_clients.elasticsearch_client.describe_elasticsearch_domain(DomainName=domain_name)[
                "DomainStatus"]
            arn = domain_info["ARN"]
            logger.debug(f"Processing OpenSearch Domain: {domain_name}")

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
                self.hcl.add_additional_data(
                    resource_type, id, "tags", formated_tags)

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
                    self.security_group_instance.aws_security_group(
                        sg, ftstack)

                vpc_name = self.get_vpc_name(vpc_options)
                if vpc_name:
                    self.hcl.add_additional_data(
                        resource_type, id, "vpc_name", vpc_name)

                subnet_ids = vpc_options.get(
                    'SubnetIds', [])
                if subnet_ids:
                    subnet_names = get_subnet_names(
                        self.aws_clients, subnet_ids)
                    if subnet_names:
                        self.hcl.add_additional_data(
                            resource_type, id, "subnet_names", subnet_names)

            encrypt_at_rest = domain_info.get('EncryptionAtRestOptions', {})
            if encrypt_at_rest:
                kmsKeyId = encrypt_at_rest.get('KmsKeyId', None)
                if kmsKeyId:
                    self.kms_instance.aws_kms_key(kmsKeyId, ftstack)
                    kms_key_alias = self.get_kms_alias(kmsKeyId)
                    if kms_key_alias:
                        self.hcl.add_additional_data(
                            resource_type, id, "kms_key_alias", kms_key_alias)

            domain_endpoint_options = domain_info.get(
                'DomainEndpointOptions', {})
            if domain_endpoint_options:
                custom_endpoint_certificate_arn = domain_endpoint_options.get(
                    'CustomEndpointCertificateArn', None)
                if custom_endpoint_certificate_arn:
                    self.acm_instance.aws_acm_certificate(
                        custom_endpoint_certificate_arn, ftstack)

            log_publishing_options = domain_info.get(
                'LogPublishingOptions', {})
            for key, data in log_publishing_options.items():
                cloudwatch_log_group_arn = data.get(
                    'CloudWatchLogsLogGroupArn', None)
                if cloudwatch_log_group_arn:
                    log_group_name = cloudwatch_log_group_arn.split(':')[-1]
                    self.logs_instance.aws_cloudwatch_log_group(
                        log_group_name, ftstack)

            # self.aws_elasticsearch_domain_policy(domain_name)

    # Updated function signature

    def aws_elasticsearch_domain_policy(self, domain_name):
        logger.debug("Processing OpenSearch Domain Policy...")

        # Since the domain is already known, we don't need to retrieve all domains
        domain_info = self.aws_clients.elasticsearch_client.describe_elasticsearch_domain(DomainName=domain_name)[
            "DomainStatus"]
        arn = domain_info["ARN"]
        # access_policy = domain_info["AccessPolicies"]
        logger.debug(f"Processing OpenSearch Domain Policy: {domain_name}")

        id = domain_name

        attributes = {
            "id": id,
            "domain_name": id,
        }

        # Process the policy resource
        self.hcl.process_resource(
            "aws_elasticsearch_domain_policy", id, attributes)
