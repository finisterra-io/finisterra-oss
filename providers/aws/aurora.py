import os
from utils.hcl import HCL
from providers.aws.iam_role import IAM_ROLE
from providers.aws.logs import Logs
from providers.aws.security_group import SECURITY_GROUP
from providers.aws.kms import KMS
import botocore

class Aurora:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
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
        self.s3Bucket = s3Bucket
        self.dynamoDBTable = dynamoDBTable
        self.state_key = state_key

        
        if not hcl:
            self.hcl = HCL(self.schema_data, self.provider_name)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


        self.iam_role_instance = IAM_ROLE(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.logs_instance = Logs(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.security_group_instance = SECURITY_GROUP(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.kms_instance = KMS(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)

        self.aws_rds_cluster_attrs = {}

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

    def get_vpc_name(self, vpc_id):
        response = self.aws_clients.ec2_client.describe_vpcs(VpcIds=[vpc_id])

        if not response or 'Vpcs' not in response or not response['Vpcs']:
            # Handle this case as required, for example:
            print(f"No VPC information found for VPC ID: {vpc_id}")
            return None

        vpc_tags = response['Vpcs'][0].get('Tags', [])
        vpc_name = next((tag['Value']
                        for tag in vpc_tags if tag['Key'] == 'Name'), None)

        if vpc_name is None:
            print(f"No 'Name' tag found for VPC ID: {vpc_id}")

        return vpc_name
        
    def get_vpc_name_by_subnet(self, subnet_ids):
        vpc_id = ""
        vpc_name = ""
        if subnet_ids:
            subnet_id = subnet_ids[0]
            #get the vpc id for the subnet_id
            response = self.aws_clients.ec2_client.describe_subnets(SubnetIds=[subnet_id])
            if not response or 'Subnets' not in response or not response['Subnets']:
                # Handle this case as required, for example:
                print(f"No subnet information found for Subnet ID: {subnet_id}")
                return None
            vpc_id = response['Subnets'][0].get('VpcId', None)

            if vpc_id:
                vpc_name = self.get_vpc_name(vpc_id)

        return vpc_id, vpc_name


    def aurora(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_rds_cluster()
        self.hcl.refresh_state()
        self.hcl.request_tf_code()

    def aws_db_cluster_snapshot(self):
        print("Processing DB Cluster Snapshots...")

        paginator = self.aws_clients.rds_client.get_paginator(
            "describe_db_cluster_snapshots")
        for page in paginator.paginate():
            for snapshot in page.get("DBClusterSnapshots", []):
                if snapshot["Engine"] in ["mysql", "postgres"]:
                    snapshot_id = snapshot["DBClusterSnapshotIdentifier"]
                    print(f"Processing DB Cluster Snapshot: {snapshot_id}")

                    attributes = {
                        "id": snapshot_id,
                    }
                    self.hcl.process_resource(
                        "aws_db_cluster_snapshot", snapshot_id.replace("-", "_"), attributes)

    def aws_appautoscaling_target(self, cluster_arn):
        print(
            f"Processing AppAutoScaling Targets for Aurora Cluster ARN {cluster_arn}...")

        paginator = self.aws_clients.appautoscaling_client.get_paginator(
            "describe_scalable_targets")
        page_iterator = paginator.paginate(
            ServiceNamespace='kafka',
            ResourceIds=[cluster_arn]
        )

        for page in page_iterator:
            for target in page["ScalableTargets"]:
                target_id = target["ResourceId"]
                print(f"Processing AppAutoScaling Target: {target_id}")

                attributes = {
                    "id": target_id,
                    "service_namespace": 'kafka',
                    "resource_id": cluster_arn
                    # Add other relevant details from 'target' as needed
                }

                self.hcl.process_resource(
                    "aws_appautoscaling_target", target_id, attributes)

    def aws_appautoscaling_policy(self, cluster_arn):
        print(
            f"Processing AppAutoScaling Policies for Aurora Cluster ARN {cluster_arn}...")

        paginator = self.aws_clients.appautoscaling_client.get_paginator(
            "describe_scaling_policies")
        page_iterator = paginator.paginate(
            ServiceNamespace='kafka',
            ResourceId=cluster_arn
        )

        for page in page_iterator:
            for policy in page["ScalingPolicies"]:
                policy_name = policy["PolicyName"]
                print(f"Processing AppAutoScaling Policy: {policy_name}")

                attributes = {
                    "id": policy_name,
                    "service_namespace": 'kafka',
                    "resource_id": cluster_arn
                    # Add other relevant details from 'policy' as needed
                }

                self.hcl.process_resource(
                    "aws_appautoscaling_policy", policy_name, attributes)

    def aws_db_event_subscription(self):
        print("Processing DB Event Subscriptions...")

        paginator = self.aws_clients.rds_client.get_paginator(
            "describe_event_subscriptions")
        for page in paginator.paginate():
            for subscription in page.get("EventSubscriptionsList", []):
                subscription_id = subscription["CustSubscriptionId"]
                print(f"Processing DB Event Subscription: {subscription_id}")

                attributes = {
                    "id": subscription_id,
                    "name": subscription_id,
                    "sns_topic_arn": subscription["SnsTopicArn"],
                    "source_type": subscription["SourceType"],
                    "event_categories": subscription["EventCategoriesList"],
                    "enabled": subscription["Enabled"],
                }
                self.hcl.process_resource(
                    "aws_db_event_subscription", subscription_id.replace("-", "_"), attributes)

    def aws_db_instance(self):
        print("Processing DB Instances...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for instance in page.get("DBInstances", []):
                if instance.get("Engine", None) not in ["mysql", "postgres"]:
                    continue
                instance_id = instance["DBInstanceIdentifier"]
                print(f"Processing DB Instance: {instance_id}")

                attributes = {
                    "id": instance_id,
                    "identifier": instance_id,
                    "allocated_storage": instance.get("AllocatedStorage", None),
                    "engine": instance.get("Engine", None),
                    "engine_version": instance.get("EngineVersion", None),
                    "instance_class": instance.get("DBInstanceClass", None),
                    "name": instance.get("DBName", None),
                    "username": instance.get("MasterUsername", None),
                    "vpc_security_group_ids": [sg["VpcSecurityGroupId"] for sg in instance.get("VpcSecurityGroups", [])],
                    "db_subnet_group_name": instance["DBSubnetGroup"]["DBSubnetGroupName"] if instance.get("DBSubnetGroup") else None,
                    "apply_immediately": instance.get("ApplyImmediately", False),
                    "delete_automated_backups": instance.get("DeleteAutomatedBackups", False),
                    "skip_final_snapshot": instance.get("SkipFinalSnapshot", False),
                }
                self.hcl.process_resource(
                    "aws_db_instance", instance_id.replace("-", "_"), attributes)

    def aws_db_instance_automated_backups_replication(self):
        print("Processing DB Instance Automated Backups Replications...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for instance in page.get("DBInstances", []):
                if instance.get("ReadReplicaDBInstanceIdentifiers"):
                    if instance.get("Engine", None) not in ["mysql", "postgres"]:
                        continue
                    source_instance_id = instance["DBInstanceIdentifier"]
                    for replica_id in instance["ReadReplicaDBInstanceIdentifiers"]:
                        print(
                            f"Processing DB Instance Automated Backups Replication for {source_instance_id} to {replica_id}")
                        attributes = {
                            "id": f"{source_instance_id}-{replica_id}",
                            "source_db_instance_identifier": source_instance_id,
                            "replica_db_instance_identifier": replica_id,
                        }
                        self.hcl.process_resource("aws_db_instance_automated_backups_replication",
                                                  f"{source_instance_id}-{replica_id}".replace("-", "_"), attributes)

    def aws_db_instance_role_association(self):
        print("Processing DB Instance Role Associations...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for instance in page.get("DBInstances", []):
                if instance.get("Engine", None) not in ["mysql", "postgres"]:
                    continue
                instance_id = instance["DBInstanceIdentifier"]
                associated_roles = instance.get("AssociatedRoles", [])
                for role in associated_roles:
                    role_arn = role["RoleArn"]
                    print(
                        f"Processing DB Instance Role Association for {instance_id} with Role ARN {role_arn}")
                    attributes = {
                        "id": f"{instance_id}-{role_arn}",
                        "db_instance_identifier": instance_id,
                        "feature_name": role["FeatureName"],
                        "role_arn": role_arn,
                    }
                    self.hcl.process_resource(
                        "aws_db_instance_role_association", f"{instance_id}-{role_arn}".replace("-", "_"), attributes)

    def aws_db_option_group(self):
        print("Processing DB Option Groups...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_option_groups")
        for page in paginator.paginate():
            for option_group in page.get("OptionGroupsList", []):
                option_group_name = option_group["OptionGroupName"]
                print(f"Processing DB Option Group: {option_group_name}")
                attributes = {
                    "id": option_group_name,
                    "name": option_group_name,
                    "engine_name": option_group["EngineName"],
                    "major_engine_version": option_group["MajorEngineVersion"],
                    "option_group_description": option_group["OptionGroupDescription"],
                }
                self.hcl.process_resource(
                    "aws_db_option_group", option_group_name.replace("-", "_"), attributes)

    def aws_db_parameter_group(self, parameter_group_name, ftstack):
        resource_type = "aws_db_parameter_group"
        print(f"Processing DB Parameter Group {parameter_group_name}")
        if parameter_group_name.startswith("default"):
            return

        paginator = self.aws_clients.rds_client.get_paginator(
            "describe_db_parameter_groups")
        for page in paginator.paginate():
            for parameter_group in page.get("DBParameterGroups", []):
                # Skip the parameter group if it's not the given one
                if parameter_group["DBParameterGroupName"] != parameter_group_name:
                    continue

                print(
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

    def aws_db_proxy(self):
        print("Processing DB Proxies...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_proxies")
        for page in paginator.paginate():
            for db_proxy in page.get("DBProxies", []):
                db_proxy_name = db_proxy["DBProxyName"]
                print(f"Processing DB Proxy: {db_proxy_name}")
                attributes = {
                    "id": db_proxy["DBProxyArn"],
                    "name": db_proxy_name,
                    "engine_family": db_proxy["EngineFamily"],
                    "auth": db_proxy["Auth"],
                    "role_arn": db_proxy["RoleArn"],
                }
                self.hcl.process_resource(
                    "aws_db_proxy", db_proxy_name.replace("-", "_"), attributes)

    def aws_db_proxy_default_target_group(self):
        print("Processing DB Proxy Default Target Groups...")

        # Get all DB Proxies
        db_proxies_response = self.aws_clients.rds_client.describe_db_proxies()
        db_proxies = db_proxies_response.get('DBProxies', [])

        for db_proxy in db_proxies:
            db_proxy_name = db_proxy.get('DBProxyName')

            # Describe target groups for each DB Proxy
            target_groups_response = self.aws_clients.rds_client.describe_db_proxy_target_groups(
                DBProxyName=db_proxy_name)
            target_groups = target_groups_response.get('TargetGroups', [])

            for target_group in target_groups:
                target_group_name = target_group.get("DBProxyName")
                print(
                    f"Processing DB Proxy Default Target Group: {target_group_name}")
                attributes = {
                    "id": target_group.get("TargetGroupArn"),
                    "name": target_group_name,
                    "db_proxy_name": target_group.get("DBProxyName"),
                }
                self.hcl.process_resource(
                    "aws_db_proxy_default_target_group", target_group_name.replace("-", "_"), attributes)

    def aws_db_proxy_endpoint(self):
        print("Processing DB Proxy Endpoints...")

        paginator = self.aws_clients.rds_client.get_paginator(
            "describe_db_proxy_endpoints")
        for page in paginator.paginate():
            for db_proxy_endpoint in page.get("DBProxyEndpoints", []):
                db_proxy_endpoint_name = db_proxy_endpoint["DBProxyEndpointName"]
                print(
                    f"Processing DB Proxy Endpoint: {db_proxy_endpoint_name}")
                attributes = {
                    "id": db_proxy_endpoint["DBProxyEndpointArn"],
                    "name": db_proxy_endpoint_name,
                    "db_proxy_name": db_proxy_endpoint["DBProxyName"],
                    "vpc_subnet_ids": db_proxy_endpoint["VpcSubnetIds"],
                }
                self.hcl.process_resource(
                    "aws_db_proxy_endpoint", db_proxy_endpoint_name.replace("-", "_"), attributes)

    def aws_db_proxy_target(self):
        print("Processing DB Proxy Targets...")

        # Get all DB Proxies
        db_proxies_response = self.aws_clients.rds_client.describe_db_proxies()
        db_proxies = db_proxies_response.get('DBProxies', [])

        for db_proxy in db_proxies:
            db_proxy_name = db_proxy.get('DBProxyName')

            # Get paginator for each DB Proxy
            paginator = self.aws_clients.rds_client.get_paginator(
                "describe_db_proxy_targets")

            for page in paginator.paginate(DBProxyName=db_proxy_name):
                for db_proxy_target in page.get("Targets", []):
                    target_arn = db_proxy_target["TargetArn"]
                    print(f"Processing DB Proxy Target: {target_arn}")
                    attributes = {
                        "id": target_arn,
                        "db_proxy_name": db_proxy_target["DBProxyName"],
                        "target_group_name": db_proxy_target["TargetGroupName"],
                        # Some targets might not be associated with a DB instance
                        "db_instance_identifier": db_proxy_target.get("DbInstanceIdentifier", None),
                    }
                    self.hcl.process_resource("aws_db_proxy_target", target_arn.replace(
                        ":", "_").replace("-", "_"), attributes)

    # def aws_db_security_group(self):
    #     print("Processing DB Security Groups...")

    #     paginator = self.aws_clients.rds_client.get_paginator(
    #         "describe_db_security_groups")
    #     for page in paginator.paginate():
    #         for db_security_group in page.get("DBSecurityGroups", []):
    #             db_security_group_name = db_security_group["DBSecurityGroupName"]
    #             print(
    #                 f"Processing DB Security Group: {db_security_group_name}")
    #             attributes = {
    #                 "id": db_security_group["DBSecurityGroupArn"],
    #                 "name": db_security_group_name,
    #                 "description": db_security_group["DBSecurityGroupDescription"],
    #             }
    #             self.hcl.process_resource(
    #                 "aws_db_security_group", db_security_group_name.replace("-", "_"), attributes)

    def aws_db_snapshot(self):
        print("Processing DB Snapshots...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_snapshots")
        for page in paginator.paginate():
            for db_snapshot in page.get("DBSnapshots", []):
                db_snapshot_id = db_snapshot["DBSnapshotIdentifier"]
                print(f"Processing DB Snapshot: {db_snapshot_id}")
                attributes = {
                    "id": db_snapshot_id,
                    # "snapshot_identifier": db_snapshot_id,
                    # "db_instance_identifier": db_snapshot["DBInstanceIdentifier"],
                    # "snapshot_type": db_snapshot["SnapshotType"],
                }
                self.hcl.process_resource(
                    "aws_db_snapshot", db_snapshot_id.replace("-", "_"), attributes)

    def aws_db_snapshot_copy(self):
        print("Processing DB Snapshot Copies...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_snapshots")
        for page in paginator.paginate():
            for db_snapshot in page.get("DBSnapshots", []):
                if "SourceRegion" in db_snapshot:
                    db_snapshot_id = db_snapshot["DBSnapshotIdentifier"]
                    print(f"Processing DB Snapshot Copy: {db_snapshot_id}")
                    attributes = {
                        "id": db_snapshot["DBSnapshotArn"],
                        "snapshot_identifier": db_snapshot_id,
                        "source_db_snapshot_identifier": db_snapshot["SourceDBSnapshotIdentifier"],
                        "source_region": db_snapshot["SourceRegion"],
                    }
                    self.hcl.process_resource(
                        "aws_db_snapshot_copy", db_snapshot_id.replace("-", "_"), attributes)

    def aws_db_subnet_group(self, db_subnet_group_name, ftstack):
        resource_type = "aws_db_subnet_group"
        print(f"Processing DB Subnet Groups {db_subnet_group_name}")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_subnet_groups")
        for page in paginator.paginate():
            for db_subnet_group in page.get("DBSubnetGroups", []):
                # Skip the subnet group if it's not the given one
                if db_subnet_group["DBSubnetGroupName"] != db_subnet_group_name:
                    continue

                # Fetch the subnet names even for the default one
                id = db_subnet_group_name
                subnet_ids = [subnet["SubnetIdentifier"] for subnet in db_subnet_group["Subnets"]]
                subnet_names = self.get_subnet_names(subnet_ids)
                if subnet_names:
                    self.hcl.add_additional_data(resource_type, id, "subnet_names",  subnet_names)

                vpc_id, vpc_name = self.get_vpc_name_by_subnet(subnet_ids)
                if vpc_id:
                    self.hcl.add_additional_data(resource_type, id, "vpc_id",  vpc_id)
                    self.hcl.add_additional_data("aws_db_instance", id, "vpc_id",  vpc_id)
                if vpc_name:
                    self.hcl.add_additional_data(resource_type, id, "vpc_name",  vpc_name)
                    self.hcl.add_additional_data("aws_db_instance", id, "vpc_name",  vpc_name)

                if db_subnet_group_name.startswith("default"):
                    return
                
                print(f"Processing DB Subnet Group: {db_subnet_group_name}")
                attributes = {
                    "id": id,
                }
                self.hcl.process_resource(
                    resource_type, id, attributes)
                self.hcl.add_stack(resource_type, id, ftstack)

    def aws_rds_cluster(self):
        resource_type = "aws_rds_cluster"
        print("Processing RDS Clusters...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_clusters")
        for page in paginator.paginate():
            for rds_cluster in page.get("DBClusters", []):
                engine = rds_cluster.get("Engine", "")
                if not engine.startswith("aurora"):
                    continue
                rds_cluster_id = rds_cluster["DBClusterIdentifier"]
                print(f"Processing RDS Cluster: {rds_cluster_id}")
                cluster_arn = rds_cluster["DBClusterArn"]

                ftstack = "aurora"
                try:
                    tags_response = self.aws_clients.rds_client.list_tags_for_resource(ResourceName=cluster_arn)
                    tags = tags_response.get('TagList', [])
                    for tag in tags:
                        if tag['Key'] == 'ftstack':
                            if tag['Value'] != 'aurora':
                                ftstack = "stack_"+tag['Value']
                            break
                except Exception as e:
                    print("Error occurred: ", e)

                attributes = {
                    "id": cluster_arn,
                    "cluster_identifier": rds_cluster_id,
                    "engine": engine,
                    "engine_version": rds_cluster["EngineVersion"],
                    "master_username": rds_cluster["MasterUsername"],
                    "database_name": rds_cluster.get("DatabaseName"),
                    "port": rds_cluster["Port"],
                }
                self.hcl.process_resource(
                    resource_type, cluster_arn, attributes)
                
                self.hcl.add_stack(resource_type, cluster_arn, ftstack)

                vpc_security_groups = rds_cluster.get("VpcSecurityGroups", [])
                security_group_ids = []
                for sg in vpc_security_groups:
                    sg_name=self.security_group_instance.aws_security_group(sg['VpcSecurityGroupId'], ftstack)
                    if sg_name == "default":
                        security_group_ids.append("default")
                    else:
                        security_group_ids.append(sg['VpcSecurityGroupId'])
                self.hcl.add_additional_data(resource_type, cluster_arn, "vpc_security_group_ids",  security_group_ids)

                kms_key_id = rds_cluster.get("KmsKeyId")
                if kms_key_id:
                    type=self.kms_instance.aws_kms_key(kms_key_id, ftstack)
                    if type == "MANAGED":
                        kms_key_alias = self.get_kms_alias(kms_key_id)
                        if kms_key_alias:
                            self.hcl.add_additional_data(resource_type, cluster_arn, "kms_key_alias",  kms_key_alias)                        


                parameter_group_name = rds_cluster.get(
                    "DBClusterParameterGroup", "")
                self.aws_rds_cluster_instance(rds_cluster_id, ftstack, rds_cluster)
                self.aws_rds_cluster_parameter_group(parameter_group_name, ftstack)
                self.aws_rds_cluster_endpoint(rds_cluster_id)
                self.aws_rds_cluster_role_association(rds_cluster_id)
                # Call AppAutoScaling related functions
                self.aws_appautoscaling_target(rds_cluster_id)
                self.aws_appautoscaling_policy(rds_cluster_id)

    def aws_rds_cluster_activity_stream(self):
        print("Processing RDS Cluster Activity Streams...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_clusters")
        for page in paginator.paginate():
            for rds_cluster in page.get("DBClusters", []):
                engine = rds_cluster.get("Engine", "")
                if engine not in ["mysql", "postgres"]:
                    continue

                rds_cluster_id = rds_cluster["DBClusterIdentifier"]
                activity_stream_mode = rds_cluster.get(
                    "ActivityStreamMode", "disabled")
                if activity_stream_mode != "disabled":
                    print(
                        f"Processing RDS Cluster Activity Stream: {rds_cluster_id}")
                    attributes = {
                        "id": rds_cluster["DBClusterArn"],
                        "cluster_identifier": rds_cluster_id,
                        "activity_stream_mode": activity_stream_mode,
                        "activity_stream_kms_key_id": rds_cluster["ActivityStreamKmsKeyId"],
                    }
                    self.hcl.process_resource(
                        "aws_rds_cluster_activity_stream", rds_cluster_id.replace("-", "_"), attributes)

    def aws_rds_cluster_endpoint(self, cluster_id):
        print("Processing RDS Cluster Endpoints...")

        paginator = self.aws_clients.rds_client.get_paginator(
            "describe_db_cluster_endpoints")
        for page in paginator.paginate():
            for rds_cluster_endpoint in page.get("DBClusterEndpoints", []):
                if rds_cluster_endpoint["DBClusterIdentifier"] != cluster_id:
                    continue
                if "DBClusterEndpointIdentifier" in rds_cluster_endpoint:
                    endpoint_id = rds_cluster_endpoint["DBClusterEndpointIdentifier"]
                    print(f"Processing RDS Cluster Endpoint: {endpoint_id}")
                    attributes = {
                        "id": endpoint_id,
                        # "endpoint_identifier": endpoint_id,
                        # "cluster_identifier": rds_cluster_endpoint["DBClusterIdentifier"],
                        # "endpoint_type": rds_cluster_endpoint["EndpointType"],
                        # "custom_endpoint_type": rds_cluster_endpoint.get("CustomEndpointType"),
                    }
                    self.hcl.process_resource(
                        "aws_rds_cluster_endpoint", endpoint_id.replace("-", "_"), attributes)

    def aws_rds_cluster_instance(self, cluster_id, ftstack, rds_cluster_data):
        print("Processing RDS Cluster Instances...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for rds_instance in page.get("DBInstances", []):
                if rds_instance.get("DBClusterIdentifier") != cluster_id:
                    continue
                if "DBClusterIdentifier" in rds_instance and rds_instance["Engine"].startswith("aurora"):
                    instance_id = rds_instance["DBInstanceIdentifier"]
                    print(f"Processing RDS Cluster Instance: {instance_id}")
                    attributes = {
                        "id": rds_instance["DBInstanceArn"],
                    }
                    self.hcl.process_resource(
                        "aws_rds_cluster_instance", instance_id.replace("-", "_"), attributes)

                    # Extract the DBSubnetGroupName and call the aws_db_subnet_group function
                    db_subnet_group = rds_instance.get(
                        "DBSubnetGroup", "")
                    if db_subnet_group:
                        db_subnet_group_name = db_subnet_group.get(
                            "DBSubnetGroupName", "")
                        self.aws_db_subnet_group(db_subnet_group_name, ftstack)

                    # Extract the DBParameterGroupName and call the aws_db_parameter_group function
                    
                    db_parameter_groups = rds_instance.get(
                        "DBParameterGroups", [])
                    for db_parameter_group in db_parameter_groups:
                        db_parameter_group_name = db_parameter_group.get(
                            "DBParameterGroupName", "")
                        self.aws_db_parameter_group(db_parameter_group_name, ftstack)

                    monitoring_role_arn = rds_instance.get("MonitoringRoleArn")
                    if monitoring_role_arn:
                        role_name = monitoring_role_arn.split('/')[-1]
                        self.iam_role_instance.aws_iam_role(role_name, ftstack)
                        # self.aws_iam_role(monitoring_role_arn)

                    performance_insights_kms_key_id = rds_instance.get("PerformanceInsightsKMSKeyId")
                    if performance_insights_kms_key_id:
                        type=self.kms_instance.aws_kms_key(performance_insights_kms_key_id, ftstack)
                        if type == "MANAGED":
                            kms_key_alias = self.get_kms_alias(performance_insights_kms_key_id)
                            if kms_key_alias:
                                self.hcl.add_additional_data("aws_rds_cluster_instance", instance_id, "performance_insights_kms_key_alias",  kms_key_alias)

                    # call aws_cloudwatch_log_group function with instance_id and each log export name as parameters
                    for log_export_name in rds_instance.get("EnabledCloudwatchLogsExports", []):
                        self.logs_instance.aws_cloudwatch_log_group(f"/aws/rds/instance/{instance_id}/{log_export_name}", ftstack)

                    copy_tags_to_snapshot = rds_cluster_data.get("CopyTagsToSnapshot", False)
                    if copy_tags_to_snapshot:
                        self.hcl.add_additional_data("aws_rds_cluster_instance", instance_id, "copy_tags_to_snapshot", copy_tags_to_snapshot)
                    preferred_maintenance_window = rds_cluster_data.get("PreferredMaintenanceWindow", "")
                    if preferred_maintenance_window:
                        self.hcl.add_additional_data("aws_rds_cluster_instance", instance_id, "preferred_maintenance_window", preferred_maintenance_window)
                    tags = rds_cluster_data.get("Tags", [])
                    if tags:
                        self.hcl.add_additional_data("aws_rds_cluster_instance", instance_id, "tags", tags)

    def aws_rds_cluster_parameter_group(self, parameter_group_name, ftstack):
        
        resource_type = "aws_rds_cluster_parameter_group"
        print("Processing RDS Cluster Parameter Groups...")

        paginator = self.aws_clients.rds_client.get_paginator(
            "describe_db_cluster_parameter_groups")
        for page in paginator.paginate():
            for rds_cluster_parameter_group in page.get("DBClusterParameterGroups", []):
                if rds_cluster_parameter_group["DBClusterParameterGroupName"] != parameter_group_name:
                    continue
                parameter_group_id = rds_cluster_parameter_group["DBClusterParameterGroupName"]
                print(
                    f"Processing RDS Cluster Parameter Group: {parameter_group_id}")
                id = parameter_group_id
                attributes = {
                    "id": id,
                    # "name": parameter_group_id,
                    # "family": rds_cluster_parameter_group["DBParameterGroupFamily"],
                    # "description": rds_cluster_parameter_group["Description"],
                }
                self.hcl.process_resource(
                    resource_type, parameter_group_id.replace("-", "_"), attributes)
                self.hcl.add_stack(resource_type, id, ftstack)

    def aws_rds_cluster_role_association(self, cluster_id):
        print("Processing RDS Cluster Role Associations...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_db_clusters")
        for page in paginator.paginate():
            for rds_cluster in page.get("DBClusters", []):
                if rds_cluster["DBClusterIdentifier"] != cluster_id:
                    continue
                engine = rds_cluster.get("Engine", "")
                if engine not in ["mysql", "postgres"]:
                    continue

                cluster_id = rds_cluster["DBClusterIdentifier"]
                for associated_role in rds_cluster.get("AssociatedRoles", []):
                    role_arn = associated_role["RoleArn"]
                    role_name = role_arn.split("/")[-1]
                    association_id = f"{cluster_id}-{role_name}"
                    print(
                        f"Processing RDS Cluster Role Association: {association_id}")
                    attributes = {
                        "id": association_id,
                        "cluster_identifier": cluster_id,
                        "role_arn": role_arn,
                    }
                    self.hcl.process_resource(
                        "aws_rds_cluster_role_association", association_id.replace("-", "_"), attributes)

    def aws_rds_export_task(self):
        print("Processing RDS Export Tasks...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_export_tasks")
        for page in paginator.paginate():
            for export_task in page.get("ExportTasks", []):
                export_task_id = export_task["ExportTaskIdentifier"]
                print(f"Processing RDS Export Task: {export_task_id}")
                attributes = {
                    "id": export_task_id,
                    "source_arn": export_task["SourceArn"],
                    "export_task_identifier": export_task_id,
                    "s3_bucket": export_task["S3Bucket"],
                    "s3_prefix": export_task["S3Prefix"],
                    "iam_role_arn": export_task["IamRoleArn"],
                    "kms_key_id": export_task["KmsKeyId"],
                    "export_only": export_task["ExportOnly"],
                }
                self.hcl.process_resource(
                    "aws_rds_export_task", export_task_id.replace("-", "_"), attributes)

    def aws_rds_global_cluster(self):
        print("Processing RDS Global Clusters...")

        paginator = self.aws_clients.rds_client.get_paginator("describe_global_clusters")
        for page in paginator.paginate():
            for global_cluster in page.get("GlobalClusters", []):
                global_cluster_id = global_cluster["GlobalClusterIdentifier"]
                print(f"Processing RDS Global Cluster: {global_cluster_id}")
                attributes = {
                    "id": global_cluster["GlobalClusterArn"],
                    "global_cluster_identifier": global_cluster_id,
                    "engine": global_cluster["Engine"],
                    "engine_version": global_cluster["EngineVersion"],
                    "deletion_protection": global_cluster["DeletionProtection"],
                }
                self.hcl.process_resource(
                    "aws_rds_global_cluster", global_cluster_id.replace("-", "_"), attributes)

    def aws_rds_reserved_instance(self):
        print("Processing RDS Reserved Instances...")

        paginator = self.aws_clients.rds_client.get_paginator(
            "describe_reserved_db_instances")
        for page in paginator.paginate():
            for reserved_instance in page.get("ReservedDBInstances", []):
                reserved_instance_id = reserved_instance["ReservedDBInstanceId"]
                print(
                    f"Processing RDS Reserved Instance: {reserved_instance_id}")
                attributes = {
                    "id": reserved_instance_id,
                    "db_instance_class": reserved_instance["DBInstanceClass"],
                    "duration": reserved_instance["Duration"],
                    "fixed_price": reserved_instance["FixedPrice"],
                    "instance_count": reserved_instance["DBInstanceCount"],
                    "start_time": reserved_instance["StartTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "usage_price": reserved_instance["UsagePrice"],
                    "currency_code": reserved_instance["CurrencyCode"],
                    "offering_type": reserved_instance["OfferingType"],
                    "product_description": reserved_instance["ProductDescription"],
                }
                self.hcl.process_resource(
                    "aws_rds_reserved_instance", reserved_instance_id.replace("-", "_"), attributes)

    def aws_security_group(self, security_group_ids):
        print("Processing Security Groups...")

        # Create a response dictionary to collect responses for all security groups
        response = self.aws_clients.ec2_client.describe_security_groups(
            GroupIds=security_group_ids
        )

        for security_group in response["SecurityGroups"]:
            print(
                f"Processing Security Group: {security_group['GroupName']}")

            attributes = {
                "id": security_group["GroupId"],
                "name": security_group["GroupName"],
                "description": security_group.get("Description", ""),
                "vpc_id": security_group.get("VpcId", ""),
                "owner_id": security_group.get("OwnerId", ""),
            }

            self.hcl.process_resource(
                "aws_security_group", security_group["GroupName"].replace("-", "_"), attributes)

            # Process egress rules
            for rule in security_group.get('IpPermissionsEgress', []):
                self.aws_security_group_rule(
                    'egress', security_group, rule)

            # Process ingress rules
            for rule in security_group.get('IpPermissions', []):
                self.aws_security_group_rule(
                    'ingress', security_group, rule)

    def aws_security_group_rule(self, rule_type, security_group, rule):
        # Rule identifiers are often constructed by combining security group id, rule type, protocol, ports and security group references
        rule_id = f"{security_group['GroupId']}_{rule_type}_{rule.get('IpProtocol', 'all')}"
        print(f"Processing Security Groups Rule {rule_id}...")
        if rule.get('FromPort'):
            rule_id += f"_{rule['FromPort']}"
        if rule.get('ToPort'):
            rule_id += f"_{rule['ToPort']}"

        attributes = {
            "id": rule_id,
            "type": rule_type,
            "security_group_id": security_group['GroupId'],
            "protocol": rule.get('IpProtocol', '-1'),  # '-1' stands for 'all'
            "from_port": rule.get('FromPort', 0),
            "to_port": rule.get('ToPort', 0),
            "cidr_blocks": [ip_range['CidrIp'] for ip_range in rule.get('IpRanges', [])],
            "source_security_group_ids": [sg['GroupId'] for sg in rule.get('UserIdGroupPairs', [])]
        }

        self.hcl.process_resource(
            "aws_security_group_rule", rule_id.replace("-", "_"), attributes)

    # def aws_iam_role(self, role_arn):
    #     # the role name is the last part of the ARN
    #     role_name = role_arn.split('/')[-1]

    #     role = self.aws_clients.iam_client.get_role(RoleName=role_name)
    #     print(f"Processing IAM Role: {role_name}")

    #     attributes = {
    #         "id": role_name,
    #         # "name": role['Role']['RoleName'],
    #         # "arn": role['Role']['Arn'],
    #         # "description": role['Role']['Description'],
    #         # "assume_role_policy": role['Role']['AssumeRolePolicyDocument'],
    #     }
    #     self.hcl.process_resource(
    #         "aws_iam_role", role_name.replace("-", "_"), attributes)

    #     # After processing the role, process the policies attached to it
    #     self.aws_iam_role_policy_attachment(role_name)

    # def aws_iam_role_policy_attachment(self, role_name):
    #     attached_policies = self.aws_clients.iam_client.list_attached_role_policies(
    #         RoleName=role_name)

    #     for policy in attached_policies['AttachedPolicies']:
    #         policy_name = policy['PolicyName']
    #         print(
    #             f"Processing IAM Role Policy Attachment: {policy_name} for Role: {role_name}")

    #         resource_name = f"{role_name}/{policy_name}"

    #         attributes = {
    #             "id": f"{role_name}/{policy['PolicyArn']}",
    #             "role": role_name,
    #             "policy_arn": policy['PolicyArn']
    #         }
    #         self.hcl.process_resource(
    #             "aws_iam_role_policy_attachment", resource_name.replace("-", "_"), attributes)

    # def aws_cloudwatch_log_group(self, instance_id, log_export_name):
    #     print(
    #         f"Processing CloudWatch Log Group: {log_export_name} for DB Instance: {instance_id}")

    #     # assuming the log group name has prefix /aws/rds/instance/{instance_id}/{log_export_name}
    #     log_group_name_prefix = f"/aws/rds/instance/{instance_id}/{log_export_name}"

    #     response = self.aws_clients.logs_client.describe_log_groups(
    #         logGroupNamePrefix=log_group_name_prefix)

    #     while True:
    #         for log_group in response.get('logGroups', []):
    #             log_group_name = log_group.get('logGroupName')
    #             if log_group_name.startswith(log_group_name_prefix):
    #                 print(f"Processing Log Group: {log_group_name}")
    #                 attributes = {
    #                     "id": log_group_name,
    #                     "name": log_group_name,
    #                     "retention_in_days": log_group.get('retentionInDays'),
    #                     "arn": log_group.get('arn'),
    #                 }
    #                 self.hcl.process_resource(
    #                     "aws_cloudwatch_log_group", log_group_name.replace("-", "_"), attributes)

    #         if 'nextToken' in response:
    #             response = self.aws_clients.logs_client.describe_log_groups(
    #                 logGroupNamePrefix=log_group_name_prefix, nextToken=response['nextToken'])
    #         else:
    #             break

    def aws_appautoscaling_target(self, cluster_identifier):
        cluster_identifier = f"cluster:{cluster_identifier}"
        print(
            f"Processing AppAutoScaling Targets for Aurora Cluster ARN {cluster_identifier}...")

        paginator = self.aws_clients.appautoscaling_client.get_paginator(
            "describe_scalable_targets")
        page_iterator = paginator.paginate(
            ServiceNamespace='kafka',
            ResourceIds=[cluster_identifier]
        )

        for page in page_iterator:
            for target in page["ScalableTargets"]:
                target_id = target["ResourceId"]
                print(f"Processing AppAutoScaling Target: {target_id}")

                attributes = {
                    "id": target_id,
                    "service_namespace": 'kafka',
                    "resource_id": cluster_identifier
                    # Add other relevant details from 'target' as needed
                }

                self.hcl.process_resource(
                    "aws_appautoscaling_target", target_id, attributes)

    def aws_appautoscaling_policy(self, cluster_identifier):
        cluster_identifier = f"cluster:{cluster_identifier}"
        print(
            f"Processing AppAutoScaling Policies for Aurora Cluster ARN {cluster_identifier}...")

        paginator = self.aws_clients.appautoscaling_client.get_paginator(
            "describe_scaling_policies")
        page_iterator = paginator.paginate(
            ServiceNamespace='kafka',
            ResourceId=cluster_identifier
        )

        for page in page_iterator:
            for policy in page["ScalingPolicies"]:
                policy_name = policy["PolicyName"]
                print(f"Processing AppAutoScaling Policy: {policy_name}")

                attributes = {
                    "id": policy_name,
                    "service_namespace": 'kafka',
                    "resource_id": cluster_identifier
                    # Add other relevant details from 'policy' as needed
                }

                self.hcl.process_resource(
                    "aws_appautoscaling_policy", policy_name, attributes)
