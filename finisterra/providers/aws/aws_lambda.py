import os
import botocore
import json
import http.client
import tempfile
from urllib.parse import urlparse
from ...utils.hcl import HCL

from ...providers.aws.iam_role import IAM
from ...providers.aws.logs import Logs
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.utils import get_subnet_names
import logging
import inspect

logger = logging.getLogger('finisterra')


class AwsLambda:
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

    def aws_lambda(self):
        self.hcl.prepare_folder()

        self.aws_lambda_function()
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

    def aws_lambda_function(self, selected_function_name=None, ftstack=None):
        resource_type = "aws_lambda_function"
        # logger.debug(f"Processing Lambda Functions... {selected_function_name}")

        if selected_function_name and ftstack:
            if self.hcl.id_resource_processed(resource_type, selected_function_name, ftstack):
                logger.debug(
                    f"  Skipping Lambda Function: {selected_function_name} already processed")
                return
            self.process_single_lambda_function(
                selected_function_name, ftstack)
            return

        total = 0
        paginator = self.provider_instance.aws_clients.lambda_client.get_paginator(
            'list_functions')
        for page in paginator.paginate():
            for function in page['Functions']:
                total += 1

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for page in paginator.paginate():
            for function in page['Functions']:
                function_name = function['FunctionName']
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{function_name}[/]")
                self.process_single_lambda_function(function_name, ftstack)

    def process_single_lambda_function(self, function_name, ftstack=None):
        resource_type = "aws_lambda_function"

        logger.debug(f"Processing Lambda Function: {function_name}")

        try:
            function_details = self.provider_instance.aws_clients.lambda_client.get_function(
                FunctionName=function_name)
        except Exception as e:
            logger.error(
                f"Unexpected error occurred while getting lambda function: {e}")
            return

        function_arn = function_details["Configuration"]["FunctionArn"]

        if not ftstack:
            ftstack = "aws_lambda"
            try:
                tags = self.provider_instance.aws_clients.lambda_client.list_tags(
                    Resource=function_arn)['Tags']
                if tags.get('ftstack', 'aws_lambda') != 'aws_lambda':
                    ftstack = "stack_" + tags.get('ftstack', 'aws_lambda')
            except Exception as e:
                logger.error(f"Error occurred: {e}")

        s3_bucket = ''
        s3_key = ''

        if 'Code' in function_details:
            if 'S3Bucket' in function_details['Code']:
                s3_bucket = function_details['Code']['S3Bucket']
            if 'S3Key' in function_details['Code']:
                s3_key = function_details['Code']['S3Key']

        if 'Location' not in function_details['Code']:
            logger.info(
                f"  Warning: No function code found for Lambda Function: {function_name}")
            return
        code_url = function_details['Code']['Location']
        url_parts = urlparse(code_url)

        conn = http.client.HTTPSConnection(url_parts.netloc)
        conn.request("GET", url_parts.path)
        response = conn.getresponse()

        temp_folder = tempfile.mkdtemp()
        folder = os.path.join(temp_folder, "tf_code", ftstack)
        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(folder, f"{function_name}.zip")
        with open(filename, "wb") as f:
            f.write(response.read())

        logger.debug(f"  Lambda Function code saved as: {filename}")
        attributes = {
            "id": function_arn,
            "function_name": function_name,
            "runtime": function_details["Configuration"]["Runtime"],
            "role": function_details["Configuration"]["Role"],
            "handler": function_details["Configuration"]["Handler"],
            "timeout": function_details["Configuration"]["Timeout"],
            "memory_size": function_details["Configuration"]["MemorySize"],
            "description": function_details["Configuration"].get("Description", ""),
            "publish": False,
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "filename": filename,
        }

        self.hcl.process_resource(resource_type, function_arn, attributes)
        files = {"filename": filename}
        self.hcl.add_stack(resource_type, function_arn, ftstack, files)

        role_name = function_details["Configuration"]["Role"].split('/')[-1]
        self.iam_role_instance.aws_iam_role(role_name, ftstack)

        vpc_config = function_details["Configuration"].get('VpcConfig', {})
        if vpc_config:
            vpc_id = vpc_config.get('VpcId', '')
            subnet_ids = vpc_config.get('SubnetIds', [])
            security_group_ids = vpc_config.get('SecurityGroupIds', [])
            if vpc_id:
                vpc_name = self.get_vpc_name(vpc_id)
                if vpc_name:
                    self.hcl.add_additional_data(
                        resource_type, function_arn, "vpc_name", vpc_name)
                subnet_names = get_subnet_names(
                    self.provider_instance.aws_clients, subnet_ids)
                if subnet_names:
                    self.hcl.add_additional_data(
                        resource_type, function_arn, "subnet_names", subnet_names)

            final_security_group_ids = []
            for security_group_id in security_group_ids:
                sg_name = self.security_group_instance.aws_security_group(
                    security_group_id, ftstack)
                if sg_name == "default":
                    final_security_group_ids.append("default")
                else:
                    final_security_group_ids.append(security_group_id)
                self.hcl.add_additional_data(
                    resource_type, function_arn, "security_group_ids",  final_security_group_ids)

    def aws_lambda_alias(self):
        logger.debug(f"Processing Lambda Aliases...")

        functions = self.provider_instance.aws_clients.lambda_client.list_functions()[
            "Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            aliases = self.provider_instance.aws_clients.lambda_client.list_aliases(
                FunctionName=function_name)["Aliases"]
            for alias in aliases:
                alias_name = alias["Name"]
                logger.debug(
                    f"Processing Lambda Alias: {alias_name} for Function: {function_name}")

                attributes = {
                    "id": alias["AliasArn"],
                    "function_name": function_name,
                    "name": alias_name,
                    "function_version": alias["FunctionVersion"],
                }
                self.hcl.process_resource(
                    "aws_lambda_alias", f"{function_name}_{alias_name}".replace("-", "_"), attributes)

    def aws_lambda_code_signing_config(self):
        logger.debug(f"Processing Lambda Code Signing Configs...")

        paginator = self.provider_instance.aws_clients.lambda_client.get_paginator(
            "list_code_signing_configs")

        for page in paginator.paginate():
            for config in page.get("CodeSigningConfigs", []):
                config_id = config["CodeSigningConfigId"]
                logger.debug(
                    f"Processing Lambda Code Signing Config: {config_id}")

                attributes = {
                    "id": config_id,
                    "allowed_publishers": config["AllowedPublishers"]["SigningProfileVersionArns"],
                    "policies": config["CodeSigningPolicies"]["UntrustedArtifactOnDeployment"],
                }
                if "Description" in config:
                    attributes["description"] = config["Description"]

                self.hcl.process_resource(
                    "aws_lambda_code_signing_config", config_id.replace("-", "_"), attributes)

    def aws_lambda_event_source_mapping(self):
        logger.debug(f"Processing Lambda Event Source Mappings...")

        functions = self.provider_instance.aws_clients.lambda_client.list_functions()[
            "Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            event_source_mappings = self.provider_instance.aws_clients.lambda_client.list_event_source_mappings(
                FunctionName=function_name)["EventSourceMappings"]

            for mapping in event_source_mappings:
                mapping_id = mapping["UUID"]
                logger.debug(
                    f"Processing Lambda Event Source Mapping: {mapping_id} for Function: {function_name}")

                attributes = {
                    "id": mapping_id,
                    "function_name": function_name,
                    "event_source_arn": mapping["EventSourceArn"],
                }
                self.hcl.process_resource(
                    "aws_lambda_event_source_mapping", mapping_id.replace("-", "_"), attributes)

    def aws_lambda_function_event_invoke_config(self):
        logger.debug(f"Processing Lambda Function Event Invoke Configs...")

        functions = self.provider_instance.aws_clients.lambda_client.list_functions()[
            "Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            try:
                event_invoke_config = self.provider_instance.aws_clients.lambda_client.get_function_event_invoke_config(
                    FunctionName=function_name)
                logger.debug(
                    f"Processing Event Invoke Config for Lambda Function: {function_name}")

                attributes = {
                    "id": f"{function_name}:$LATEST",
                    "function_name": function_name,
                    "maximum_event_age_in_seconds": event_invoke_config.get("MaximumEventAgeInSeconds", ""),
                    "maximum_retry_attempts": event_invoke_config.get("MaximumRetryAttempts", ""),
                }
                self.hcl.process_resource(
                    "aws_lambda_function_event_invoke_config", function_name.replace("-", "_"), attributes)
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.debug(
                        f"  Lambda Function {function_name} doesn't have an EventInvokeConfig")
                else:
                    raise e

    def aws_lambda_function_url(self):
        logger.debug(f"Processing Lambda Function URLs...")

        functions = self.provider_instance.aws_clients.lambda_client.list_functions()[
            "Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            qualifier = "$LATEST"
            region = self.provider_instance.region
            arn = function["FunctionArn"]
            url = f"https://{arn.split(':')[4]}.lambda.{region}.amazonaws.com/2015-03-31/functions/{arn}/invocations"
            logger.debug(
                f"Processing URL for Lambda Function: {function_name}")

            attributes = {
                "id": f"{function_name}:$LATEST",
                "function_name": function_name,
                "qualifier": qualifier,
                "url": url,
            }
            self.hcl.process_resource(
                "aws_lambda_function_url", function_name.replace("-", "_"), attributes)

    def aws_lambda_layer_version(self):
        logger.debug(f"Processing Lambda Layer Versions...")

        layers = self.provider_instance.aws_clients.lambda_client.list_layers()[
            "Layers"]

        for layer in layers:
            layer_name = layer["LayerName"]
            layer_versions = self.provider_instance.aws_clients.lambda_client.list_layer_versions(LayerName=layer_name)[
                "LayerVersions"]

            for layer_version in layer_versions:
                version = layer_version["Version"]
                logger.debug(
                    f"Processing Layer Version {version} for Lambda Layer: {layer_name}")

                attributes = {
                    "id": f"{layer_name}:{version}",
                    "layer_name": layer_name,
                    "version": version,
                    "compatible_runtimes": layer_version.get("CompatibleRuntimes", []),
                }

                layer_version_permission_arns = []
                policy = self.provider_instance.aws_clients.lambda_client.get_layer_version_policy(
                    LayerName=layer_name, VersionNumber=version)["Policy"]

                for statement in policy["Statement"]:
                    if statement["Effect"] == "Allow":
                        layer_version_permission_arns.extend(
                            statement["Principal"]["AWS"])

                self.hcl.process_resource(
                    "aws_lambda_layer_version", f"{layer_name.replace('-', '_')}_version_{version}", attributes)

    def aws_lambda_layer_version_permission(self):
        logger.debug(f"Processing Lambda Layer Version Permissions...")
        paginator = self.provider_instance.aws_clients.lambda_client.get_paginator(
            "list_layers")
        page_iterator = paginator.paginate()
        for page in page_iterator:
            for layer in page["Layers"]:
                layer_version_arn = layer["LatestMatchingVersion"]["LayerVersionArn"]
                layer_version_permission_arns = [p["Principal"] for p in self.provider_instance.aws_clients.lambda_client.get_layer_version_policy(
                    LayerName=layer["LayerName"],
                    VersionNumber=layer["LatestMatchingVersion"]["Version"],
                )["Policy"]["Statement"]]
                for permission_arn in layer_version_permission_arns:
                    id = f"{layer_version_arn}-{permission_arn}"
                    attributes = {
                        "id": id,
                        "layer_version_arn": layer_version_arn,
                        "statement_id": permission_arn,
                        "action": "lambda:GetLayerVersion",
                        "principal": permission_arn,
                    }
                    self.hcl.process_resource(
                        "aws_lambda_layer_version_permission", id.replace("-", "_"), attributes)

    def aws_lambda_permission(self):
        logger.debug(f"Processing Lambda Permissions...")

        functions = self.provider_instance.aws_clients.lambda_client.list_functions()[
            "Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            try:
                policy_response = self.provider_instance.aws_clients.lambda_client.get_policy(
                    FunctionName=function_name)
                policy = json.loads(policy_response["Policy"])

                for statement in policy["Statement"]:
                    statement_id = statement["Sid"]
                    logger.debug(
                        f"Processing Permission {statement_id} for Lambda Function: {function_name}")

                    attributes = {
                        "id": f"{function_name}-{statement_id}",
                        "function_name": function_name,
                        "statement_id": statement_id,
                    }
                    self.hcl.process_resource(
                        "aws_lambda_permission", f"{function_name.replace('-', '_')}_permission_{statement_id}", attributes)
            except self.provider_instance.aws_clients.lambda_client.exceptions.ResourceNotFoundException:
                logger.debug(
                    f"  Skipping Lambda Function: {function_name} because no resource policy found")

    def aws_lambda_provisioned_concurrency_config(self):
        logger.debug(
            f"Processing Lambda Provisioned Concurrency Configurations...")

        functions = self.provider_instance.aws_clients.lambda_client.list_functions()[
            "Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            try:
                concurrency_configs = self.provider_instance.aws_clients.lambda_client.list_provisioned_concurrency_configs(
                    FunctionName=function_name)["ProvisionedConcurrencyConfigs"]

                for config in concurrency_configs:
                    version = config["FunctionVersion"]
                    allocated_concurrent_executions = config["RequestedProvisionedConcurrentExecutions"]
                    logger.debug(
                        f"Processing Provisioned Concurrency Configuration for Lambda Function: {function_name}, Version: {version}")

                    attributes = {
                        "id": f"{function_name}-{version}",
                        "function_name": function_name,
                        "qualifier": version,
                        "provisioned_concurrent_executions": allocated_concurrent_executions,
                    }
                    self.hcl.process_resource("aws_lambda_provisioned_concurrency_config",
                                              f"{function_name.replace('-', '_')}_provisioned_concurrency_{version}", attributes)
            except self.provider_instance.aws_clients.lambda_client.exceptions.ResourceNotFoundException:
                logger.debug(
                    f"  No provisioned concurrency configuration found for Lambda Function: {function_name}")
