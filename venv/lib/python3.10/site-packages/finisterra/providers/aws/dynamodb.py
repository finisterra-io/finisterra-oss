from ...utils.hcl import HCL
import logging
import inspect
from botocore.exceptions import ClientError

logger = logging.getLogger('finisterra')


class Dynamodb:
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

    def dynamodb_aws_dynamodb_target_name(self, table_name):
        service_namespace = 'dynamodb'
        resource_id = f'table/{table_name}'
        logger.debug(
            f"Processing AppAutoScaling targets for DynamoDB Table: {table_name}")

        try:
            response = self.provider_instance.aws_clients.appautoscaling_client.describe_scalable_targets(
                ServiceNamespace=service_namespace,
                ResourceIds=[resource_id]
            )
            scalable_targets = response.get('ScalableTargets', [])
            if len(scalable_targets) > 0:
                return "autoscaled_gsi_ignore"
            else:
                return "this"
        except Exception as e:
            logger.error(f"Error: {e}")
            return "this"

    def dynamodb(self):
        self.hcl.prepare_folder()

        self.aws_dynamodb_table()
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

    def aws_dynamodb_table(self):
        resource_type = "aws_dynamodb_table"
        # logger.debug(f"Processing DynamoDB Tables...")

        filtered_tables = []  # List to hold filtered tables

        # Fetch and filter tables
        paginator = self.provider_instance.aws_clients.dynamodb_client.get_paginator(
            "list_tables")
        for page in paginator.paginate():
            for table_name in page["TableNames"]:
                table_description = self.provider_instance.aws_clients.dynamodb_client.describe_table(
                    TableName=table_name)["Table"]

                try:
                    tags_response = self.provider_instance.aws_clients.dynamodb_client.list_tags_of_resource(
                        ResourceArn=table_description["TableArn"])
                    table_tags = {tag['Key']: tag['Value']
                                  for tag in tags_response['Tags']}
                except ClientError as e:
                    if e.response['Error']['Code'] in ['AccessDenied', 'ResourceNotFoundException']:
                        continue  # Skip tables that cannot be accessed or don't exist
                    else:
                        raise e

                match_all_conditions = all(
                    any(table_tags.get(f['Name'].replace(
                        'tag:', ''), '') == value for value in f['Values'])
                    for f in self.provider_instance.filters
                ) if self.provider_instance.filters else True

                if match_all_conditions:
                    # Add the table name and description to the list
                    filtered_tables.append((table_name, table_description))

        # Now process the filtered tables
        total_filtered = len(filtered_tables)
        if total_filtered > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total_filtered)

        for table_name, table_description in filtered_tables:
            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{table_name}[/]")
            logger.debug(f"Processing DynamoDB Table: {table_name}")
            id = table_name

            ftstack = "dynamodb"
            try:
                response = self.provider_instance.aws_clients.dynamodb_client.list_tags_of_resource(
                    ResourceArn=table_description["TableArn"])
                tags = response.get('Tags', [])
                for tag in tags:
                    if tag['Key'] == 'ftstack':
                        if tag['Value'] != 'dynamodb':
                            ftstack = "stack_" + tag['Value']
                        break
            except Exception as e:
                logger.error(f"Error occurred: {e}")

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
        logger.debug(
            f"Processing AppAutoScaling targets for DynamoDB Table: {table_name}")

        try:
            response = self.provider_instance.aws_clients.appautoscaling_client.describe_scalable_targets(
                ServiceNamespace=service_namespace,
                ResourceIds=[resource_id]
            )
            scalable_targets = response.get('ScalableTargets', [])

            for target in scalable_targets:
                logger.debug(
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
                logger.debug(
                    f"No AppAutoScaling targets found for DynamoDB Table: {table_name}")

        except Exception as e:
            logger.error(
                f"Error processing AppAutoScaling targets for DynamoDB Table: {table_name}: {str(e)}")

    def aws_appautoscaling_policy(self, service_namespace, resource_id, scalable_dimension):
        logger.debug(
            f"Processing AppAutoScaling policies for resource: {resource_id} with dimension: {scalable_dimension}...")

        try:
            response = self.provider_instance.aws_clients.appautoscaling_client.describe_scaling_policies(
                ServiceNamespace=service_namespace,
                ResourceId=resource_id,
                ScalableDimension=scalable_dimension
            )
            scaling_policies = response.get('ScalingPolicies', [])

            for policy in scaling_policies:
                logger.debug(
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
            logger.error(
                f"Error processing AppAutoScaling policies for resource: {resource_id} with dimension: {scalable_dimension}: {str(e)}")
