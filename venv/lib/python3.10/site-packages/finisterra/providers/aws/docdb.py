from ...utils.hcl import HCL
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.kms import KMS
from ...providers.aws.utils import get_subnet_names
import logging
import inspect

logger = logging.getLogger('finisterra')


class DocDb:
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

        self.security_group_instance = SECURITY_GROUP(
            self.provider_instance, self.hcl)
        self.kms_instance = KMS(self.provider_instance, self.hcl)

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

    def docdb(self):
        self.hcl.prepare_folder()

        self.aws_docdb_cluster()
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

    def aws_docdb_cluster(self):
        resource_type = "aws_docdb_cluster"
        # logger.debug(f"Processing DocumentDB Clusters...")

        paginator = self.provider_instance.aws_clients.docdb_client.get_paginator(
            "describe_db_clusters")
        total = 0
        for page in paginator.paginate():
            for db_cluster in page["DBClusters"]:
                if db_cluster["Engine"] == "docdb":
                    total += 1

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)

        for page in paginator.paginate():
            for db_cluster in page["DBClusters"]:
                if db_cluster["Engine"] == "docdb":
                    logger.debug(
                        f"Processing DocumentDB Cluster: {db_cluster['DBClusterIdentifier']}")

                    id = db_cluster["DBClusterIdentifier"]
                    self.provider_instance.progress.update(
                        self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{id}[/]")

                    ftstack = "docdb"
                    try:
                        response = self.provider_instance.aws_clients.docdb_client.list_tags_for_resource(
                            ResourceName=db_cluster["DBClusterArn"])
                        tags = response.get('TagList', [])
                        for tag in tags:
                            if tag['Key'] == 'ftstack':
                                if tag['Value'] != 'docdb':
                                    ftstack = "docdb_"+tag['Value']
                                break
                    except Exception as e:
                        logger.error(f"Error occurred: {e}")

                    attributes = {
                        "id": db_cluster["DBClusterIdentifier"],
                    }
                    self.hcl.process_resource(
                        resource_type, id.replace("-", "_"), attributes)

                    self.hcl.add_stack(resource_type, id, ftstack)

                    # Call aws_docdb_cluster_instance with db_cluster as an argument
                    self.aws_docdb_cluster_instance(db_cluster)

                    # Call aws_security_group with the list of VpcSecurityGroups

                    for sg in db_cluster.get("VpcSecurityGroups", []):
                        self.security_group_instance.aws_security_group(
                            sg["VpcSecurityGroupId"], ftstack)
                    # vpc_security_group_ids = [sg["VpcSecurityGroupId"]
                    #                         for sg in db_cluster.get("VpcSecurityGroups", [])]
                    # self.aws_security_group(vpc_security_group_ids)
                    KmsKeyId = db_cluster.get("KmsKeyId", None)
                    if KmsKeyId:
                        self.kms_instance.aws_kms_key(KmsKeyId, ftstack)

    def aws_docdb_cluster_instance(self, db_cluster):
        logger.debug(f"Processing DocumentDB Cluster Instances...")

        paginator = self.provider_instance.aws_clients.docdb_client.get_paginator(
            "describe_db_instances")
        for page in paginator.paginate():
            for db_instance in page["DBInstances"]:
                if db_instance["Engine"] == "docdb" and db_instance["DBClusterIdentifier"] == db_cluster["DBClusterIdentifier"]:
                    logger.debug(
                        f"Processing DocumentDB Cluster Instance: {db_instance['DBInstanceIdentifier']}")

                    attributes = {
                        "id": db_instance["DBInstanceIdentifier"],
                        "instance_identifier": db_instance.get("DBInstanceIdentifier", None),
                        "cluster_identifier": db_instance.get("DBClusterIdentifier", None),
                        "instance_class": db_instance.get("DBInstanceClass", None),
                        "availability_zone": db_instance.get("AvailabilityZone", None),
                        "engine": db_instance.get("Engine", None),
                        "engine_version": db_instance.get("EngineVersion", None),
                        "status": db_instance.get("DBInstanceStatus", None),
                        "port": db_instance.get("DbInstancePort", None),
                    }
                    self.hcl.process_resource(
                        "aws_docdb_cluster_instance", db_instance["DBInstanceIdentifier"].replace("-", "_"), attributes)

                    # Call aws_docdb_cluster_parameter_group if db_instance's DBParameterGroupName matches parameter_group in DBClusterParameterGroups
                    if db_instance.get('DBParameterGroups'):
                        for param_group in db_instance['DBParameterGroups']:
                            if param_group.get('DBParameterGroupName'):
                                self.aws_docdb_cluster_parameter_group(
                                    param_group['DBParameterGroupName'])

                    # Call aws_docdb_subnet_group if DBSubnetGroup of db_instance matches subnet_group in DBSubnetGroups
                    if db_instance.get('DBSubnetGroup', {}).get('DBSubnetGroupName'):
                        self.aws_docdb_subnet_group(
                            db_instance['DBSubnetGroup']['DBSubnetGroupName'])

    def aws_docdb_cluster_parameter_group(self, parameter_group_name):
        logger.debug(f"Processing DocumentDB Cluster Parameter Groups...")

        paginator = self.provider_instance.aws_clients.docdb_client.get_paginator(
            "describe_db_cluster_parameter_groups")
        for page in paginator.paginate():
            for parameter_group in page["DBClusterParameterGroups"]:
                if parameter_group['DBClusterParameterGroupName'] == parameter_group_name:
                    # Check if it's a DocumentDB parameter group
                    if "docdb" in parameter_group["DBParameterGroupFamily"]:
                        logger.debug(
                            f"Processing DocumentDB Cluster Parameter Group: {parameter_group['DBClusterParameterGroupName']}")

                        attributes = {
                            "id": parameter_group["DBClusterParameterGroupName"],
                            "name": parameter_group["DBClusterParameterGroupName"],
                            "family": parameter_group["DBParameterGroupFamily"],
                            "description": parameter_group["Description"],
                        }
                        self.hcl.process_resource("aws_docdb_cluster_parameter_group",
                                                  parameter_group["DBClusterParameterGroupName"].replace("-", "_"), attributes)

    def aws_docdb_subnet_group(self, subnet_group_name):
        resource_type = "aws_docdb_subnet_group"
        logger.debug(f"Processing DocumentDB Subnet Groups...")

        paginator = self.provider_instance.aws_clients.docdb_client.get_paginator(
            "describe_db_subnet_groups")
        for page in paginator.paginate():
            for subnet_group in page["DBSubnetGroups"]:
                if subnet_group['DBSubnetGroupName'] == subnet_group_name:
                    # Check if it's a DocumentDB subnet group
                    if "DocumentDB" in subnet_group.get("DBSubnetGroupDescription", ""):
                        logger.debug(
                            f"Processing DocumentDB Subnet Group: {subnet_group['DBSubnetGroupName']}")

                        subnet_ids = [subnet['SubnetIdentifier']
                                      for subnet in subnet_group.get("Subnets", [])]
                        id = subnet_group["DBSubnetGroupName"]

                        attributes = {
                            "id": subnet_group["DBSubnetGroupName"],
                            "name": subnet_group.get("DBSubnetGroupName", None),
                            "description": subnet_group.get("DBSubnetGroupDescription", None),
                            "subnet_ids": subnet_ids,
                            "arn": subnet_group.get("DBSubnetGroupArn", None),
                        }
                        self.hcl.process_resource(
                            resource_type, subnet_group["DBSubnetGroupName"].replace("-", "_"), attributes)

                        subnet_names = get_subnet_names(
                            self.provider_instance.aws_clients, subnet_ids)
                        if subnet_names:
                            if resource_type not in self.hcl.additional_data:
                                self.hcl.additional_data[resource_type] = {}
                            if id not in self.hcl.additional_data[resource_type]:
                                self.hcl.additional_data[resource_type][id] = {
                                }
                            self.hcl.additional_data[resource_type][id]["subnet_names"] = subnet_names

                        VpcId = subnet_group.get("VpcId", None)
                        if VpcId:
                            if resource_type not in self.hcl.additional_data:
                                self.hcl.additional_data[resource_type] = {}
                            if id not in self.hcl.additional_data[resource_type]:
                                self.hcl.additional_data[resource_type][id] = {
                                }
                            self.hcl.additional_data[resource_type][id]["vpc_id"] = VpcId
                            vpc_name = self.get_vpc_name(VpcId)
                            if vpc_name:
                                if resource_type not in self.hcl.additional_data:
                                    self.hcl.additional_data[resource_type] = {
                                    }
                                if id not in self.hcl.additional_data[resource_type]:
                                    self.hcl.additional_data[resource_type][id] = {
                                    }
                                self.hcl.additional_data[resource_type][id]["vpc_name"] = vpc_name

    def aws_docdb_cluster_snapshot(self):
        logger.debug(f"Processing DocumentDB Cluster Snapshots...")

        paginator = self.provider_instance.aws_clients.docdb_client.get_paginator(
            "describe_db_cluster_snapshots")
        for page in paginator.paginate():
            for snapshot in page["DBClusterSnapshots"]:
                if snapshot["Engine"] == "docdb":
                    logger.debug(
                        f"Processing DocumentDB Cluster Snapshot: {snapshot['DBClusterSnapshotIdentifier']}")

                    attributes = {
                        "id": snapshot["DBClusterSnapshotIdentifier"],
                        "snapshot_identifier": snapshot.get("DBClusterSnapshotIdentifier", None),
                        "cluster_identifier": snapshot.get("DBClusterIdentifier", None),
                        "snapshot_type": snapshot.get("SnapshotType", None),
                        "engine": snapshot.get("Engine", None),
                        "engine_version": snapshot.get("EngineVersion", None),
                        "port": snapshot.get("Port", None),
                        "status": snapshot.get("Status", None),
                        "availability_zone": snapshot.get("AvailabilityZone", None),
                    }
                    self.hcl.process_resource(
                        "aws_docdb_cluster_snapshot", snapshot["DBClusterSnapshotIdentifier"].replace("-", "_"), attributes)

    def aws_docdb_event_subscription(self):
        logger.debug(f"Processing DocumentDB Event Subscriptions...")

        paginator = self.provider_instance.aws_clients.docdb_client.get_paginator(
            "describe_event_subscriptions")
        for page in paginator.paginate():
            for subscription in page["EventSubscriptionsList"]:
                logger.debug(
                    f"Processing DocumentDB Event Subscription: {subscription['CustSubscriptionId']}")

                attributes = {
                    "id": subscription["CustSubscriptionId"],
                    "name": subscription.get("CustSubscriptionId", None),
                    "sns_topic_arn": subscription.get("CustomerAwsId", None),
                    "source_type": subscription.get("SourceType", None),
                    "event_categories": subscription.get("EventCategoriesList", None),
                    "enabled": subscription.get("Enabled", None),
                }
                self.hcl.process_resource(
                    "aws_docdb_event_subscription", subscription["CustSubscriptionId"].replace("-", "_"), attributes)

    def aws_docdb_global_cluster(self):
        logger.debug(f"Processing DocumentDB Global Clusters...")

        paginator = self.provider_instance.aws_clients.docdb_client.get_paginator(
            "describe_db_clusters")
        for page in paginator.paginate():
            for cluster in page["DBClusters"]:
                if "GlobalClusterIdentifier" in cluster and cluster["Engine"] == "docdb":
                    logger.debug(
                        f"Processing DocumentDB Global Cluster: {cluster['GlobalClusterIdentifier']}")

                    attributes = {
                        "id": cluster["GlobalClusterIdentifier"],
                        "global_cluster_identifier": cluster.get("GlobalClusterIdentifier", None),
                        "source_db_cluster_identifier": cluster.get("DBClusterIdentifier", None),
                        "engine": cluster.get("Engine", None),
                        "engine_version": cluster.get("EngineVersion", None),
                        "deletion_protection": cluster.get("DeletionProtection", None),
                    }
                    self.hcl.process_resource(
                        "aws_docdb_global_cluster", cluster["GlobalClusterIdentifier"].replace("-", "_"), attributes)
