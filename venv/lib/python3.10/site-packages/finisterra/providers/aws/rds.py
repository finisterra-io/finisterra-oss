from ...utils.hcl import HCL
from ...providers.aws.iam_role import IAM
from ...providers.aws.logs import Logs
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.kms import KMS
from ...providers.aws.utils import get_subnet_names
import botocore
import logging
import inspect

logger = logging.getLogger('finisterra')


class RDS:
    def __init__(self, provider_instance, hcl=None):
        self.provider_instance = provider_instance
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

        self.iam_role_instance = IAM(self.provider_instance, self.hcl)
        self.logs_instance = Logs(self.provider_instance, self.hcl)
        self.security_group_instance = SECURITY_GROUP(
            self.provider_instance, self.hcl)
        self.kms_instance = KMS(self.provider_instance, self.hcl)

    def get_kms_alias(self, kms_key_id):
        try:
            value = ""
            response = self.provider_instance.aws_clients.kms_client.list_aliases()
            aliases = response.get('Aliases', [])
            while 'NextMarker' in response:
                response = self.provider_instance.aws_clients.kms_client.list_aliases(
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

    def get_vpc_name(self, vpc_id):
        response = self.provider_instance.aws_clients.ec2_client.describe_vpcs(VpcIds=[
                                                                               vpc_id])

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

    def get_vpc_name_by_subnet(self, subnet_ids):
        vpc_id = ""
        vpc_name = ""
        if subnet_ids:
            subnet_id = subnet_ids[0]
            # get the vpc id for the subnet_id
            response = self.provider_instance.aws_clients.ec2_client.describe_subnets(SubnetIds=[
                subnet_id])
            if not response or 'Subnets' not in response or not response['Subnets']:
                # Handle this case as required, for example:
                logger.debug(
                    f"No subnet information found for Subnet ID: {subnet_id}")
                return None
            vpc_id = response['Subnets'][0].get('VpcId', None)

            if vpc_id:
                vpc_name = self.get_vpc_name(vpc_id)

        return vpc_id, vpc_name

    def rds(self):
        self.hcl.prepare_folder()

        self.aws_db_instance()
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

    def aws_db_instance(self):
        resource_type = "aws_db_instance"
        logger.debug("Processing DB Instances...")

        paginator = self.provider_instance.aws_clients.rds_client.get_paginator(
            "describe_db_instances")
        total = 0
        for page in paginator.paginate():
            for instance in page.get("DBInstances", []):
                if instance.get("DBClusterIdentifier") is not None:
                    continue

                if instance.get("Engine", None) not in ["mysql", "postgres"]:
                    continue
                total += 1

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for page in paginator.paginate():
            for instance in page.get("DBInstances", []):
                instance_id = instance["DBInstanceIdentifier"]
                # Skip instances that belong to a cluster
                if instance.get("DBClusterIdentifier") is not None:
                    continue

                if instance.get("Engine", None) not in ["mysql", "postgres"]:
                    continue

                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{instance_id}[/]")

                logger.debug(f"Processing DB Instance: {instance_id}")

                # if instance_id != "xxx":
                #     continue

                id = instance_id

                ftstack = "rds"
                try:
                    tags_response = self.provider_instance.aws_clients.rds_client.list_tags_for_resource(
                        ResourceName=instance["DBInstanceArn"])
                    tags = tags_response.get('TagList', [])
                    for tag in tags:
                        if tag['Key'] == 'ftstack':
                            if tag['Value'] != 'rds':
                                ftstack = "stack_" + tag['Value']
                            break
                except Exception as e:
                    logger.error(f"Error occurred: {e}")

                attributes = {
                    "id": id,
                }
                self.hcl.process_resource(
                    resource_type, id, attributes)
                DbiResourceId = instance.get("DbiResourceId", None)
                self.hcl.add_stack(resource_type, DbiResourceId, ftstack)

                db_option_group_name = instance.get(
                    'OptionGroupMemberships', [{}])[0].get('OptionGroupName', None)
                if db_option_group_name is not None:
                    self.aws_db_option_group(db_option_group_name, ftstack)

                db_parameter_group_name = instance.get(
                    'DBParameterGroups', [{}])[0].get('DBParameterGroupName', None)
                if db_parameter_group_name is not None:
                    self.aws_db_parameter_group(
                        db_parameter_group_name, ftstack)

                db_subnet_group_name = instance.get(
                    'DBSubnetGroup', {}).get('DBSubnetGroupName', None)
                if db_subnet_group_name is not None:
                    self.aws_db_subnet_group(db_subnet_group_name, ftstack)

                arn = instance.get("DBInstanceArn")
                self.aws_db_instance_automated_backups_replication(
                    arn, ftstack)

                # call aws_cloudwatch_log_group function with instance_id and each log export name as parameters
                for log_export_name in instance.get("EnabledCloudwatchLogsExports", []):
                    self.logs_instance.aws_cloudwatch_log_group(
                        f"/aws/rds/instance/{instance_id}/{log_export_name}", ftstack)
                    # self.aws_cloudwatch_log_group(instance_id, log_export_name)

                monitoring_role_arn = instance.get("MonitoringRoleArn")
                if monitoring_role_arn:
                    role_name = monitoring_role_arn.split('/')[-1]
                    self.iam_role_instance.aws_iam_role(role_name, ftstack)
                    # self.aws_iam_role(monitoring_role_arn)

                vpc_security_groups = instance.get("VpcSecurityGroups", [])
                security_group_ids = []
                for sg in vpc_security_groups:
                    sg_name = self.security_group_instance.aws_security_group(
                        sg['VpcSecurityGroupId'], ftstack)
                    if sg_name == "default":
                        security_group_ids.append("default")
                    else:
                        security_group_ids.append(sg['VpcSecurityGroupId'])
                self.hcl.add_additional_data(
                    resource_type, id, "vpc_security_group_ids",  security_group_ids)

                kms_key_id = instance.get("KmsKeyId")
                if kms_key_id:
                    type = self.kms_instance.aws_kms_key(kms_key_id, ftstack)
                    if type == "MANAGED":
                        kms_key_alias = self.get_kms_alias(kms_key_id)
                        if kms_key_alias:
                            self.hcl.add_additional_data(
                                resource_type, id, "kms_key_alias",  kms_key_alias)

                performance_insights_kms_key_id = instance.get(
                    "PerformanceInsightsKMSKeyId")
                if performance_insights_kms_key_id:
                    type = self.kms_instance.aws_kms_key(
                        performance_insights_kms_key_id, ftstack)
                    if type == "MANAGED":
                        kms_key_alias = self.get_kms_alias(
                            performance_insights_kms_key_id)
                        if kms_key_alias:
                            self.hcl.add_additional_data(
                                resource_type, id, "performance_insights_kms_key_alias",  kms_key_alias)

    def aws_db_option_group(self, option_group_name, ftstack):
        resource_type = "aws_db_option_group"
        logger.debug(f"Processing DB Option Group {option_group_name}")
        if option_group_name.startswith("default"):
            return

        paginator = self.provider_instance.aws_clients.rds_client.get_paginator(
            "describe_option_groups")
        for page in paginator.paginate():
            for option_group in page.get("OptionGroupsList", []):
                # Skip the option group if it's not the given one
                if option_group["OptionGroupName"] != option_group_name:
                    continue

                logger.debug(
                    f"Processing DB Option Group: {option_group_name}")
                id = option_group_name
                attributes = {
                    "id": id,
                    "name": option_group_name,
                    "engine_name": option_group["EngineName"],
                    "major_engine_version": option_group["MajorEngineVersion"],
                    "option_group_description": option_group["OptionGroupDescription"],
                }
                self.hcl.process_resource(
                    resource_type, id, attributes)
                self.hcl.add_stack(resource_type, id, ftstack)

    def aws_db_parameter_group(self, parameter_group_name, ftstack):
        resource_type = "aws_db_parameter_group"
        logger.debug(f"Processing DB Parameter Group {parameter_group_name}")
        if parameter_group_name.startswith("default"):
            return

        paginator = self.provider_instance.aws_clients.rds_client.get_paginator(
            "describe_db_parameter_groups")
        for page in paginator.paginate():
            for parameter_group in page.get("DBParameterGroups", []):
                # Skip the parameter group if it's not the given one
                if parameter_group["DBParameterGroupName"] != parameter_group_name:
                    continue

                logger.debug(
                    f"Processing DB Parameter Group: {parameter_group_name}")
                id = parameter_group_name
                attributes = {
                    "id": id,
                    "name": parameter_group_name,
                    "family": parameter_group["DBParameterGroupFamily"],
                    "description": parameter_group["Description"],
                }
                self.hcl.process_resource(
                    resource_type, id, attributes)
                self.hcl.add_stack(resource_type, id, ftstack)

    def aws_db_subnet_group(self, db_subnet_group_name, ftstack):
        resource_type = "aws_db_subnet_group"
        logger.debug(f"Processing DB Subnet Groups {db_subnet_group_name}")

        paginator = self.provider_instance.aws_clients.rds_client.get_paginator(
            "describe_db_subnet_groups")
        for page in paginator.paginate():
            for db_subnet_group in page.get("DBSubnetGroups", []):
                # Skip the subnet group if it's not the given one
                if db_subnet_group["DBSubnetGroupName"] != db_subnet_group_name:
                    continue

                # Fetch the subnet names even for the default one
                id = db_subnet_group_name
                subnet_ids = [subnet["SubnetIdentifier"]
                              for subnet in db_subnet_group["Subnets"]]
                subnet_names = get_subnet_names(
                    self.provider_instance.aws_clients, subnet_ids)
                if subnet_names:
                    self.hcl.add_additional_data(
                        resource_type, id, "subnet_names",  subnet_names)

                vpc_id, vpc_name = self.get_vpc_name_by_subnet(subnet_ids)
                if vpc_id:
                    self.hcl.add_additional_data(
                        resource_type, id, "vpc_id",  vpc_id)
                    self.hcl.add_additional_data(
                        "aws_db_instance", id, "vpc_id",  vpc_id)
                if vpc_name:
                    self.hcl.add_additional_data(
                        resource_type, id, "vpc_name",  vpc_name)
                    self.hcl.add_additional_data(
                        "aws_db_instance", id, "vpc_name",  vpc_name)

                if db_subnet_group_name.startswith("default"):
                    return

                logger.debug(
                    f"Processing DB Subnet Group: {db_subnet_group_name}")
                attributes = {
                    "id": id,
                }
                self.hcl.process_resource(
                    resource_type, id, attributes)
                self.hcl.add_stack(resource_type, id, ftstack)

    def aws_db_instance_automated_backups_replication(self, source_instance_arn, ftstack):
        resource_type = "aws_db_instance_automated_backups_replication"
        logger.debug(
            f"Processing DB Instance Automated Backups Replication {source_instance_arn}")

        paginator = self.provider_instance.aws_clients.rds_client.get_paginator(
            "describe_db_instances")
        for page in paginator.paginate():
            for instance in page.get("DBInstances", []):
                if instance.get("ReadReplicaDBInstanceIdentifiers") and instance["DBInstanceArn"] == source_instance_arn:
                    if instance.get("Engine", None) not in ["mysql", "postgres"]:
                        continue

                    # Fetching automated backup details
                    backups_paginator = self.provider_instance.aws_clients.rds_client.get_paginator(
                        "describe_db_instance_automated_backups")
                    backups_page = backups_paginator.paginate(
                        DBInstanceIdentifier=instance["DBInstanceIdentifier"])

                    for backup_page in backups_page:
                        for backup in backup_page.get("DBInstanceAutomatedBackups", []):
                            automated_backup_arn = backup["DBInstanceAutomatedBackupsArn"]

                            source_instance_id = instance["DBInstanceIdentifier"]
                            for replica_id in instance["ReadReplicaDBInstanceIdentifiers"]:
                                logger.debug(
                                    f"Processing DB Instance Automated Backups Replication for {source_instance_id} to {replica_id}")
                                id = automated_backup_arn
                                attributes = {
                                    "id": automated_backup_arn,
                                }
                                self.hcl.process_resource(
                                    resource_type, id, attributes)
                                self.hcl.add_stack(resource_type, id, ftstack)

                                kms_key_id = backup.get("KmsKeyId")
                                if kms_key_id:
                                    type = self.kms_instance.aws_kms_key(
                                        kms_key_id, ftstack)
                                    if type == "MANAGED":
                                        kms_key_alias = self.get_kms_alias(
                                            kms_key_id)
                                        if kms_key_alias:
                                            self.hcl.add_additional_data(
                                                resource_type, id, "kms_key_alias",  kms_key_alias)
