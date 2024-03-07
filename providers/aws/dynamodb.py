import os
from utils.hcl import HCL


class Dynamodb:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {        }
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data

        self.workspace_id = workspace_id
        self.modules = modules
        self.hcl = HCL(self.schema_data, self.provider_name)
        self.hcl.region = region
        self.hcl.account_id = aws_account_id

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


    def dynamodb_aws_dynamodb_target_name(self, table_name):
        service_namespace = 'dynamodb'
        resource_id = f'table/{table_name}'
        print(
            f"Processing AppAutoScaling targets for DynamoDB Table: {table_name}")

        try:
            response = self.aws_clients.appautoscaling_client.describe_scalable_targets(
                ServiceNamespace=service_namespace,
                ResourceIds=[resource_id]
            )
            scalable_targets = response.get('ScalableTargets', [])
            if len(scalable_targets) > 0:
                return "autoscaled_gsi_ignore"
            else:
                return "this"
        except Exception as e:
            print(f"Error: {e}")
            return "this"
        
    def dynamodb(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_dynamodb_table()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()



    def aws_dynamodb_table(self):
        resource_type = "aws_dynamodb_table"
        print("Processing DynamoDB Tables...")

        paginator = self.aws_clients.dynamodb_client.get_paginator("list_tables")
        for page in paginator.paginate():
            for table_name in page["TableNames"]:
                table_description = self.aws_clients.dynamodb_client.describe_table(TableName=table_name)["Table"]

                # if table_name != "staging_WallFeedItem":
                #     continue

                print(f"Processing DynamoDB Table: {table_name}")
                id = table_name

                ftstack = "dynamodb"
                try:
                    response = self.aws_clients.dynamodb_client.list_tags_of_resource(ResourceArn=table_description["TableArn"])
                    tags = response.get('Tags', [])
                    for tag in tags:
                        if tag['Key'] == 'ftstack':
                            if tag['Value'] != 'dynamodb':
                                ftstack = "stack_"+tag['Value']
                            break
                except Exception as e:
                    print("Error occurred: ", e)

                attributes = {
                    "id": id,
                    "name": table_name,
                    "read_capacity": table_description["ProvisionedThroughput"]["ReadCapacityUnits"],
                    "write_capacity": table_description["ProvisionedThroughput"]["WriteCapacityUnits"],
                }

                if "GlobalSecondaryIndexes" in table_description:
                    for gsi in table_description["GlobalSecondaryIndexes"]:
                        index_name = gsi["IndexName"]
                        index_resource_id = f'table/{table_name}/index/{index_name}'
                        self.aws_appautoscaling_target(index_resource_id)

                self.hcl.process_resource(
                    resource_type, table_name.replace("-", "_"), attributes)
                self.hcl.add_stack(resource_type, id, ftstack)

                target_name = self.dynamodb_aws_dynamodb_target_name(table_name)
                if resource_type not in self.hcl.additional_data:
                    self.hcl.additional_data[resource_type] = {}
                if id not in self.hcl.additional_data[resource_type]:
                    self.hcl.additional_data[resource_type][id] = {}
                self.hcl.additional_data[resource_type][id]["target_name"] = target_name

                self.aws_appautoscaling_target(table_name)

    def aws_appautoscaling_target(self, table_name):
        service_namespace = 'dynamodb'
        resource_id = f'table/{table_name}'
        print(
            f"Processing AppAutoScaling targets for DynamoDB Table: {table_name}")

        try:
            response = self.aws_clients.appautoscaling_client.describe_scalable_targets(
                ServiceNamespace=service_namespace,
                ResourceIds=[resource_id]
            )
            scalable_targets = response.get('ScalableTargets', [])

            for target in scalable_targets:
                print(
                    f"Processing DynamoDB AppAutoScaling Target: {resource_id} with dimension: {target['ScalableDimension']}")

                resource_name = f"{service_namespace}-{resource_id.replace('/', '-')}-{target['ScalableDimension']}"
                attributes = {
                    "id": resource_id,
                    "resource_id": resource_id,
                    "service_namespace": service_namespace,
                    "scalable_dimension": target['ScalableDimension'],
                }
                self.hcl.process_resource(
                    "aws_appautoscaling_target", resource_name, attributes)

                # Processing scaling policies for the target
                self.aws_appautoscaling_policy(
                    service_namespace, resource_id, target['ScalableDimension'])

            if not scalable_targets:
                print(
                    f"No AppAutoScaling targets found for DynamoDB Table: {table_name}")

        except Exception as e:
            print(
                f"Error processing AppAutoScaling targets for DynamoDB Table: {table_name}: {str(e)}")

    def aws_appautoscaling_policy(self, service_namespace, resource_id, scalable_dimension):
        print(
            f"Processing AppAutoScaling policies for resource: {resource_id} with dimension: {scalable_dimension}...")

        try:
            response = self.aws_clients.appautoscaling_client.describe_scaling_policies(
                ServiceNamespace=service_namespace,
                ResourceId=resource_id,
                ScalableDimension=scalable_dimension
            )
            scaling_policies = response.get('ScalingPolicies', [])

            for policy in scaling_policies:
                print(
                    f"Processing AppAutoScaling Policy: {policy['PolicyName']} for resource: {resource_id}")

                resource_name = f"{service_namespace}-{resource_id.replace('/', '-')}-{policy['PolicyName']}"
                attributes = {
                    "id": f"{policy['PolicyName']}",
                    "resource_id": resource_id,
                    "service_namespace": service_namespace,
                    "scalable_dimension": scalable_dimension,
                    "name": policy['PolicyName'],
                }
                self.hcl.process_resource(
                    "aws_appautoscaling_policy", resource_name, attributes)
        except Exception as e:
            print(
                f"Error processing AppAutoScaling policies for resource: {resource_id} with dimension: {scalable_dimension}: {str(e)}")

    # def aws_dynamodb_contributor_insights(self):
    #     print("Processing DynamoDB Contributor Insights...")

    #     paginator = self.aws_clients.dynamodb_client.get_paginator("list_tables")
    #     for page in paginator.paginate():
    #         for table_name in page["TableNames"]:
    #             try:
    #                 contributor_insights = self.aws_clients.dynamodb_client.describe_contributor_insights(
    #                     TableName=table_name)
    #                 status = contributor_insights["ContributorInsightsStatus"]

    #                 print(
    #                     f"Processing DynamoDB Contributor Insights: {table_name}")

    #                 attributes = {
    #                     "table_name": table_name,
    #                     "contributor_insights_status": status,
    #                 }

    #                 self.hcl.process_resource(
    #                     "aws_dynamodb_contributor_insights", table_name.replace("-", "_"), attributes)
    #             except self.aws_clients.dynamodb_client.exceptions.ResourceNotFoundException:
    #                 print(
    #                     f"  No Contributor Insights found for DynamoDB Table: {table_name}")

    # def aws_dynamodb_global_table(self):
    #     print("Processing DynamoDB Global Tables...")

    #     global_tables = self.aws_clients.dynamodb_client.list_global_tables()[
    #         "GlobalTables"]
    #     for global_table in global_tables:
    #         global_table_name = global_table["GlobalTableName"]

    #         global_table_description = self.aws_clients.dynamodb_client.describe_global_table(
    #             GlobalTableName=global_table_name)["GlobalTableDescription"]

    #         print(
    #             f"Processing DynamoDB Global Table: {global_table_name}")

    #         attributes = {
    #             "id": global_table_name,
    #             "name": global_table_name,
    #             "replica": [{"region_name": replica["RegionName"]} for replica in global_table_description["ReplicaDescriptions"]],
    #         }

    #         self.hcl.process_resource(
    #             "aws_dynamodb_global_table", global_table_name.replace("-", "_"), attributes)

    # def aws_dynamodb_kinesis_streaming_destination(self):
    #     print("Processing DynamoDB Kinesis Streaming Destinations...")

    #     table_names = self.aws_clients.dynamodb_client.list_tables()["TableNames"]
    #     for table_name in table_names:
    #         try:
    #             streaming_destination = self.aws_clients.dynamodb_client.describe_kinesis_streaming_destination(
    #                 TableName=table_name)
    #             destinations = streaming_destination["KinesisDataStreamDestinations"]

    #             for destination in destinations:
    #                 print(
    #                     f"Processing DynamoDB Kinesis Streaming Destination: {table_name}")

    #                 attributes = {
    #                     "id": destination["StreamArn"],
    #                     "table_name": table_name,
    #                     "stream_arn": destination["StreamArn"],
    #                     "destination_status": destination["DestinationStatus"],
    #                 }

    #                 self.hcl.process_resource(
    #                     "aws_dynamodb_kinesis_streaming_destination", table_name.replace("-", "_"), attributes)
    #         except self.aws_clients.dynamodb_client.exceptions.ResourceNotFoundException:
    #             print(
    #                 f"  No Kinesis Streaming Destination found for DynamoDB Table: {table_name}")

    # def aws_dynamodb_table_replica(self):
    #     print("Processing DynamoDB Table Replicas...")

    #     paginator = self.aws_clients.dynamodb_client.get_paginator("list_tables")
    #     for page in paginator.paginate():
    #         for table_name in page["TableNames"]:
    #             table_description = self.aws_clients.dynamodb_client.describe_table(
    #                 TableName=table_name)["Table"]

    #             if "Replicas" in table_description:
    #                 for replica in table_description["Replicas"]:
    #                     print(
    #                         f"Processing DynamoDB Table Replica: {table_name}")

    #                     attributes = {
    #                         "id": f"{table_name}-{replica['RegionName']}",
    #                         "table_name": table_name,
    #                         "region_name": replica["RegionName"],
    #                     }

    #                     self.hcl.process_resource(
    #                         "aws_dynamodb_table_replica", f"{table_name}-{replica['RegionName']}".replace("-", "_"), attributes)

    # def aws_dynamodb_tag(self):
    #     print("Processing DynamoDB Tags...")

    #     paginator = self.aws_clients.dynamodb_client.get_paginator("list_tables")
    #     for page in paginator.paginate():
    #         for table_name in page["TableNames"]:
    #             tags = self.aws_clients.dynamodb_client.list_tags_of_resource(
    #                 ResourceArn=self.aws_clients.dynamodb_client.describe_table(TableName=table_name)["Table"]["TableArn"])["Tags"]

    #             for tag in tags:
    #                 print(
    #                     f"Processing DynamoDB Tag: {tag['Key']} for Table: {table_name}")

    #                 attributes = {
    #                     "id": f"{table_name},{tag['Key']}",
    #                     "table_name": table_name,
    #                     "key": tag["Key"],
    #                     "value": tag["Value"],
    #                 }

    #                 self.hcl.process_resource(
    #                     "aws_dynamodb_tag", f"{table_name}-{tag['Key']}".replace("-", "_"), attributes)
