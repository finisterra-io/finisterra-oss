from ...utils.hcl import HCL
from ...providers.aws.kms import KMS
import logging
import inspect

logger = logging.getLogger('finisterra')


class Logs:
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

        self.kms_instance = KMS(self.provider_instance, self.hcl)

    def logs(self):
        self.hcl.prepare_folder()

        self.aws_cloudwatch_log_group()
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

    def aws_cloudwatch_log_data_protection_policy(self):
        logger.debug("Processing CloudWatch Log Data Protection Policies...")

        paginator = self.provider_instance.aws_clients.logs_client.get_paginator(
            "describe_resource_policies")
        for page in paginator.paginate():
            for policy in page["resourcePolicies"]:
                policy_name = policy["policyName"]
                logger.debug(
                    f"Processing CloudWatch Log Data Protection Policy: {policy_name}")

                attributes = {
                    "id": policy_name,
                    "policy_name": policy_name,
                    "policy_document": policy["policyDocument"],
                }

                self.hcl.process_resource(
                    "aws_cloudwatch_log_data_protection_policy", policy_name.replace("-", "_"), attributes)

    def aws_cloudwatch_log_destination(self):
        logger.debug("Processing CloudWatch Log Destinations...")

        paginator = self.provider_instance.aws_clients.logs_client.get_paginator(
            "describe_destinations")
        for page in paginator.paginate():
            for destination in page["destinations"]:
                destination_name = destination["destinationName"]
                logger.debug(
                    f"Processing CloudWatch Log Destination: {destination_name}")

                attributes = {
                    "id": destination_name,
                    "name": destination_name,
                    "arn": destination["destinationArn"],
                    "role_arn": destination["roleArn"],
                    "target_arn": destination["targetArn"],
                }

                self.hcl.process_resource(
                    "aws_cloudwatch_log_destination", destination_name.replace("-", "_"), attributes)

    def aws_cloudwatch_log_destination_policy(self):
        logger.debug("Processing CloudWatch Log Destination Policies...")

        paginator = self.provider_instance.aws_clients.logs_client.get_paginator(
            "describe_destinations")
        for page in paginator.paginate():
            for destination in page["destinations"]:
                destination_name = destination["destinationName"]

                try:
                    destination_policy = self.provider_instance.aws_clients.logs_client.get_destination_policy(
                        destinationName=destination_name)
                    logger.debug(
                        f"Processing CloudWatch Log Destination Policy: {destination_name}")

                    attributes = {
                        "id": destination_name,
                        "destination_name": destination_name,
                        "access_policy": destination_policy["accessPolicy"],
                    }

                    self.hcl.process_resource(
                        "aws_cloudwatch_log_destination_policy", destination_name.replace("-", "_"), attributes)
                except self.provider_instance.aws_clients.logs_client.exceptions.ResourceNotFoundException:
                    logger.debug(
                        f"  No Destination Policy found for Log Destination: {destination_name}")

    def aws_cloudwatch_log_group(self, specific_log_group_name=None, ftstack=None):
        logger.debug("Processing CloudWatch Log Groups...")

        if specific_log_group_name:
            self.process_single_log_group(specific_log_group_name, ftstack)
            return

        paginator = self.provider_instance.aws_clients.logs_client.get_paginator(
            "describe_log_groups")
        total = 0
        for page in paginator.paginate():
            total += len(page["logGroups"])

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for page in paginator.paginate():
            for log_group in page["logGroups"]:
                log_group_name = log_group["logGroupName"]
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{log_group_name}[/]")
                if log_group_name.startswith("/aws"):
                    continue
                self.process_single_log_group(log_group_name, ftstack)

    def process_single_log_group(self, log_group_name, ftstack=None):
        resource_type = "aws_cloudwatch_log_group"
        log_group = self.provider_instance.aws_clients.logs_client.describe_log_groups(
            logGroupNamePrefix=log_group_name)['logGroups']
        if not log_group:
            return
        log_group = log_group[0]
        logger.debug(f"Processing CloudWatch Log Group: {log_group_name}")
        id = log_group_name
        attributes = {
            "id": id,
            "name": log_group_name,
        }

        self.hcl.process_resource(resource_type, id, attributes)
        if not ftstack:
            ftstack = "logs"

        # Fetch details of the log group for additional information like KMS key
        log_group = self.provider_instance.aws_clients.logs_client.describe_log_groups(
            logGroupNamePrefix=log_group_name)["logGroups"][0]
        if "kmsKeyId" in log_group:
            self.kms_instance.aws_kms_key(log_group["kmsKeyId"], ftstack)

        self.hcl.add_stack(resource_type, id, ftstack)

    def aws_cloudwatch_log_metric_filter(self):
        logger.debug("Processing CloudWatch Log Metric Filters...")

        paginator = self.provider_instance.aws_clients.logs_client.get_paginator(
            "describe_log_groups")
        for page in paginator.paginate():
            for log_group in page["logGroups"]:
                log_group_name = log_group["logGroupName"]

                paginator_filters = self.provider_instance.aws_clients.logs_client.get_paginator(
                    "describe_metric_filters")
                for filter_page in paginator_filters.paginate(logGroupName=log_group_name):
                    for metric_filter in filter_page["metricFilters"]:
                        filter_name = metric_filter["filterName"]
                        logger.debug(
                            f"Processing CloudWatch Log Metric Filter: {filter_name}")

                        attributes = {
                            "id": filter_name,
                            "name": filter_name,
                            "log_group_name": log_group_name,
                            "pattern": metric_filter["filterPattern"],
                            "metric_transformation": metric_filter["metricTransformations"],
                        }

                        self.hcl.process_resource(
                            "aws_cloudwatch_log_metric_filter", filter_name.replace("-", "_"), attributes)

    def aws_cloudwatch_log_resource_policy(self):
        logger.debug("Processing CloudWatch Log Resource Policies...")

        paginator = self.provider_instance.aws_clients.logs_client.get_paginator(
            "describe_resource_policies")
        for page in paginator.paginate():
            for resource_policy in page["resourcePolicies"]:
                policy_name = resource_policy["policyName"]
                logger.debug(
                    f"Processing CloudWatch Log Resource Policy: {policy_name}")

                attributes = {
                    "id": policy_name,
                    "policy_name": policy_name,
                    "policy_document": resource_policy["policyDocument"],
                }

                self.hcl.process_resource(
                    "aws_cloudwatch_log_resource_policy", policy_name.replace("-", "_"), attributes)

    def aws_cloudwatch_log_stream(self):
        logger.debug("Processing CloudWatch Log Streams...")

        paginator = self.provider_instance.aws_clients.logs_client.get_paginator(
            "describe_log_groups")
        for page in paginator.paginate():
            for log_group in page["logGroups"]:
                log_group_name = log_group["logGroupName"]

                paginator_streams = self.provider_instance.aws_clients.logs_client.get_paginator(
                    "describe_log_streams")
                for stream_page in paginator_streams.paginate(logGroupName=log_group_name):
                    for log_stream in stream_page["logStreams"]:
                        stream_name = log_stream["logStreamName"]
                        logger.debug(
                            f"Processing CloudWatch Log Stream: {stream_name}")

                        attributes = {
                            "id": stream_name,
                            "name": stream_name,
                            "log_group_name": log_group_name,
                        }

                        self.hcl.process_resource(
                            "aws_cloudwatch_log_stream", stream_name.replace("-", "_"), attributes)

    def aws_cloudwatch_log_subscription_filter(self):
        logger.debug("Processing CloudWatch Log Subscription Filters...")

        paginator = self.provider_instance.aws_clients.logs_client.get_paginator(
            "describe_log_groups")
        for page in paginator.paginate():
            for log_group in page["logGroups"]:
                log_group_name = log_group["logGroupName"]

                paginator_filters = self.provider_instance.aws_clients.logs_client.get_paginator(
                    "describe_subscription_filters")
                for filter_page in paginator_filters.paginate(logGroupName=log_group_name):
                    for subscription_filter in filter_page["subscriptionFilters"]:
                        filter_name = subscription_filter["filterName"]
                        logger.debug(
                            f"Processing CloudWatch Log Subscription Filter: {filter_name}")

                        attributes = {
                            "id": filter_name,
                            "name": filter_name,
                            "log_group_name": log_group_name,
                            "filter_pattern": subscription_filter["filterPattern"],
                            "destination_arn": subscription_filter["destinationArn"],
                            "role_arn": subscription_filter.get("roleArn", ""),
                        }

                        self.hcl.process_resource(
                            "aws_cloudwatch_log_subscription_filter", filter_name.replace("-", "_"), attributes)

    def aws_cloudwatch_query_definition(self):
        logger.debug("Processing CloudWatch Query Definitions...")

        query_definitions_response = self.provider_instance.aws_clients.logs_client.describe_query_definitions()

        for query_definition in query_definitions_response["queryDefinitions"]:
            query_definition_id = query_definition["queryDefinitionId"]
            logger.debug(
                f"Processing CloudWatch Query Definition: {query_definition_id}")

            attributes = {
                "id": query_definition_id,
                "name": query_definition["name"],
                "query_string": query_definition["queryString"],
            }

            if "logGroupNames" in query_definition:
                attributes["log_group_names"] = query_definition["logGroupNames"]

            self.hcl.process_resource(
                "aws_cloudwatch_query_definition", query_definition_id.replace("-", "_"), attributes)
