import os
from utils.hcl import HCL
import botocore
import json
import http.client
from urllib.parse import urlparse
from providers.aws.iam_role import IAM_ROLE
from providers.aws.logs import Logs
from providers.aws.security_group import SECURITY_GROUP
import shutil

def convert_to_terraform_format(env_variables_dict):
    # Format the dictionary to Terraform format
    # terraform_format = "variables = {\n"
    terraform_format = "{\n"
    for key, value in env_variables_dict.items():
        # Escape the double quotes
        value = str(value).replace('"', '\\"')
        terraform_format += f"  {key} = \"{value}\"\n"
    terraform_format += "}"

    return terraform_format


class AwsLambda:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {        }
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.aws_account_id = aws_account_id
        
        self.workspace_id = workspace_id
        self.modules = modules
        if not hcl:
            self.hcl = HCL(self.schema_data, self.provider_name)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.account_id = aws_account_id

        self.iam_role_instance = IAM_ROLE(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.logs_instance = Logs(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.security_group_instance = SECURITY_GROUP(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)

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


    def aws_lambda(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_lambda_function()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()

        
    def aws_lambda_function(self, selected_function_name=None, ftstack=None):
        resource_type = "aws_lambda_function"
        print("Processing Lambda Functions...", selected_function_name)

        if selected_function_name and ftstack:
            if self.hcl.id_resource_processed(resource_type, selected_function_name, ftstack):
                print(f"  Skipping Lambda Function: {selected_function_name} already processed")
                return
            self.process_single_lambda_function(selected_function_name, ftstack)
            return

        paginator = self.aws_clients.lambda_client.get_paginator('list_functions')
        for page in paginator.paginate():
            for function in page['Functions']:
                function_name = function['FunctionName']
                self.process_single_lambda_function(function_name, ftstack)

    def process_single_lambda_function(self, function_name, ftstack=None):
        resource_type = "aws_lambda_function"

        # if function_name != 'ApiGatewayCustomAuth':
        #     return
        
        print(f"Processing Lambda Function: {function_name}")

        function_details = self.aws_clients.lambda_client.get_function(FunctionName=function_name)
        function_arn = function_details["Configuration"]["FunctionArn"]

        if not ftstack:
            ftstack = "aws_lambda"
            try:
                tags = self.aws_clients.lambda_client.list_tags(Resource=function_arn)['Tags']
                if tags.get('ftstack', 'aws_lambda') != 'aws_lambda':
                    ftstack = "stack_" + tags.get('ftstack', 'aws_lambda')
            except Exception as e:
                print("Error occurred: ", e)

        s3_bucket = ''
        s3_key = ''

        if 'Code' in function_details:
            if 'S3Bucket' in function_details['Code']:
                s3_bucket = function_details['Code']['S3Bucket']
            if 'S3Key' in function_details['Code']:
                s3_key = function_details['Code']['S3Key']

        if 'Location' not in function_details['Code']:
            print(f"  Warning: No function code found for Lambda Function: {function_name}")
            return
        code_url = function_details['Code']['Location']
        url_parts = urlparse(code_url)

        conn = http.client.HTTPSConnection(url_parts.netloc)
        conn.request("GET", url_parts.path)
        response = conn.getresponse()

        folder = os.path.join(ftstack)
        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(folder, f"{function_name}.zip")
        with open(filename, "wb") as f:
            f.write(response.read())

        print(f"  Lambda Function code saved as: {filename}")

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
        current_folder=os.getcwd()
        files= {"base_dir": current_folder,"filename":filename }
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
                    self.hcl.add_additional_data(resource_type, function_arn, "vpc_name", vpc_name)
                subnet_names = self.get_subnet_names(subnet_ids)
                if subnet_names:
                    self.hcl.add_additional_data(resource_type, function_arn, "subnet_names", subnet_names)

            final_security_group_ids=[]
            for security_group_id in security_group_ids:
                sg_name=self.security_group_instance.aws_security_group(security_group_id, ftstack)
                if sg_name == "default":
                    final_security_group_ids.append("default")
                else:
                    final_security_group_ids.append(security_group_id)
                self.hcl.add_additional_data(resource_type, function_arn, "security_group_ids",  final_security_group_ids)
                                

        # log_group_name = f"/aws/lambda/{function_name}"
        # self.logs_instance.aws_cloudwatch_log_group(log_group_name, ftstack)
        # self.aws_cloudwatch_log_group(log_group_name)


    # def aws_iam_role(self, role_arn, aws_iam_policy=False):
    #     print(f"Processing IAM Role: {role_arn}...")

    #     role_name = role_arn.split('/')[-1]  # Extract role name from ARN

    #     try:
    #         role = self.aws_clients.iam_client.get_role(RoleName=role_name)['Role']

    #         print(f"Processing IAM Role: {role['Arn']}")

    #         attributes = {
    #             "id": role['RoleName'],
    #         }
    #         self.hcl.process_resource(
    #             "aws_iam_role", role['RoleName'], attributes)
    #         # Process IAM role policy attachments for the role
    #         self.aws_iam_role_policy_attachment(
    #             role['RoleName'], aws_iam_policy)
    #     except Exception as e:
    #         print(f"Error processing IAM role: {role_name}: {str(e)}")

    # def aws_iam_role_policy_attachment(self, role_name, aws_iam_policy=False):
    #     print(
    #         f"Processing IAM Role Policy Attachments for role: {role_name}...")

    #     try:
    #         paginator = self.aws_clients.iam_client.get_paginator(
    #             'list_attached_role_policies')
    #         for page in paginator.paginate(RoleName=role_name):
    #             for policy in page['AttachedPolicies']:
    #                 print(
    #                     f"Processing IAM Role Policy Attachment: {policy['PolicyName']} for role: {role_name}")

    #                 resource_name = f"{role_name}-{policy['PolicyName']}"
    #                 attributes = {
    #                     "id": f"{role_name}/{policy['PolicyArn']}",
    #                     "role": role_name,
    #                     "policy_arn": policy['PolicyArn']
    #                 }
    #                 self.hcl.process_resource(
    #                     "aws_iam_role_policy_attachment", resource_name, attributes)

    #                 if aws_iam_policy:
    #                     self.aws_iam_policy(policy['PolicyArn'])

    #     except Exception as e:
    #         print(
    #             f"Error processing IAM role policy attachments for role: {role_name}: {str(e)}")

    # def aws_iam_policy(self, policy_arn):
    #     print(f"Processing IAM Policy: {policy_arn}...")

    #     try:
    #         response = self.aws_clients.iam_client.get_policy(PolicyArn=policy_arn)
    #         policy = response.get('Policy', {})

    #         if policy:
    #             print(f"Processing IAM Policy: {policy_arn}")

    #             attributes = {
    #                 "id": policy_arn,
    #                 "arn": policy_arn,
    #                 "name": policy['PolicyName'],
    #                 "path": policy['Path'],
    #                 "description": policy.get('Description', ''),
    #             }
    #             self.hcl.process_resource(
    #                 "aws_iam_policy", policy['PolicyName'], attributes)
    #         else:
    #             print(f"No IAM Policy found with ARN: {policy_arn}")

    #     except Exception as e:
    #         print(f"Error processing IAM Policy: {policy_arn}: {str(e)}")

    def aws_cloudwatch_log_group(self, log_group_name):
        print(f"Processing CloudWatch Log Group for Lambda function...")

        paginator = self.aws_clients.logs_client.get_paginator('describe_log_groups')

        for page in paginator.paginate():
            for log_group in page['logGroups']:
                if log_group['logGroupName'] == log_group_name:
                    print(
                        f"Processing CloudWatch Log Group: {log_group_name}")

                    # Prepare the attributes
                    attributes = {
                        "id": log_group_name,
                        "name": log_group_name,
                    }

                    # Process the resource
                    self.hcl.process_resource(
                        "aws_cloudwatch_log_group", log_group_name.replace("/", "_"), attributes)
                    return  # End the function once we've found the matching log group

        print(
            f"  Warning: No matching CloudWatch Log Group found for Lambda function: {log_group_name}")

    def aws_lambda_alias(self):
        print("Processing Lambda Aliases...")

        functions = self.aws_clients.lambda_client.list_functions()["Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            aliases = self.aws_clients.lambda_client.list_aliases(
                FunctionName=function_name)["Aliases"]
            for alias in aliases:
                alias_name = alias["Name"]
                print(
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
        print("Processing Lambda Code Signing Configs...")

        paginator = self.aws_clients.lambda_client.get_paginator(
            "list_code_signing_configs")

        for page in paginator.paginate():
            for config in page.get("CodeSigningConfigs", []):
                config_id = config["CodeSigningConfigId"]
                print(f"Processing Lambda Code Signing Config: {config_id}")

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
        print("Processing Lambda Event Source Mappings...")

        functions = self.aws_clients.lambda_client.list_functions()["Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            event_source_mappings = self.aws_clients.lambda_client.list_event_source_mappings(
                FunctionName=function_name)["EventSourceMappings"]

            for mapping in event_source_mappings:
                mapping_id = mapping["UUID"]
                print(
                    f"Processing Lambda Event Source Mapping: {mapping_id} for Function: {function_name}")

                attributes = {
                    "id": mapping_id,
                    "function_name": function_name,
                    "event_source_arn": mapping["EventSourceArn"],
                }
                self.hcl.process_resource(
                    "aws_lambda_event_source_mapping", mapping_id.replace("-", "_"), attributes)

    def aws_lambda_function_event_invoke_config(self):
        print("Processing Lambda Function Event Invoke Configs...")

        functions = self.aws_clients.lambda_client.list_functions()["Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            try:
                event_invoke_config = self.aws_clients.lambda_client.get_function_event_invoke_config(
                    FunctionName=function_name)
                print(
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
                    print(
                        f"  Lambda Function {function_name} doesn't have an EventInvokeConfig")
                else:
                    raise e

    def aws_lambda_function_url(self):
        print("Processing Lambda Function URLs...")

        functions = self.aws_clients.lambda_client.list_functions()["Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            qualifier = "$LATEST"
            region = self.region
            arn = function["FunctionArn"]
            url = f"https://{arn.split(':')[4]}.lambda.{region}.amazonaws.com/2015-03-31/functions/{arn}/invocations"
            print(f"Processing URL for Lambda Function: {function_name}")

            attributes = {
                "id": f"{function_name}:$LATEST",
                "function_name": function_name,
                "qualifier": qualifier,
                "url": url,
            }
            self.hcl.process_resource(
                "aws_lambda_function_url", function_name.replace("-", "_"), attributes)

    def aws_lambda_layer_version(self):
        print("Processing Lambda Layer Versions...")

        layers = self.aws_clients.lambda_client.list_layers()["Layers"]

        for layer in layers:
            layer_name = layer["LayerName"]
            layer_versions = self.aws_clients.lambda_client.list_layer_versions(LayerName=layer_name)[
                "LayerVersions"]

            for layer_version in layer_versions:
                version = layer_version["Version"]
                print(
                    f"Processing Layer Version {version} for Lambda Layer: {layer_name}")

                attributes = {
                    "id": f"{layer_name}:{version}",
                    "layer_name": layer_name,
                    "version": version,
                    "compatible_runtimes": layer_version.get("CompatibleRuntimes", []),
                }

                layer_version_permission_arns = []
                policy = self.aws_clients.lambda_client.get_layer_version_policy(
                    LayerName=layer_name, VersionNumber=version)["Policy"]

                for statement in policy["Statement"]:
                    if statement["Effect"] == "Allow":
                        layer_version_permission_arns.extend(
                            statement["Principal"]["AWS"])

                self.hcl.process_resource(
                    "aws_lambda_layer_version", f"{layer_name.replace('-', '_')}_version_{version}", attributes)

    def aws_lambda_layer_version_permission(self):
        print("Processing Lambda Layer Version Permissions...")
        paginator = self.aws_clients.lambda_client.get_paginator("list_layers")
        page_iterator = paginator.paginate()
        for page in page_iterator:
            for layer in page["Layers"]:
                layer_version_arn = layer["LatestMatchingVersion"]["LayerVersionArn"]
                layer_version_permission_arns = [p["Principal"] for p in self.aws_clients.lambda_client.get_layer_version_policy(
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
        print("Processing Lambda Permissions...")

        functions = self.aws_clients.lambda_client.list_functions()["Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            try:
                policy_response = self.aws_clients.lambda_client.get_policy(
                    FunctionName=function_name)
                policy = json.loads(policy_response["Policy"])

                for statement in policy["Statement"]:
                    statement_id = statement["Sid"]
                    print(
                        f"Processing Permission {statement_id} for Lambda Function: {function_name}")

                    attributes = {
                        "id": f"{function_name}-{statement_id}",
                        "function_name": function_name,
                        "statement_id": statement_id,
                    }
                    self.hcl.process_resource(
                        "aws_lambda_permission", f"{function_name.replace('-', '_')}_permission_{statement_id}", attributes)
            except self.aws_clients.lambda_client.exceptions.ResourceNotFoundException:
                print(
                    f"  Skipping Lambda Function: {function_name} because no resource policy found")

    def aws_lambda_provisioned_concurrency_config(self):
        print("Processing Lambda Provisioned Concurrency Configurations...")

        functions = self.aws_clients.lambda_client.list_functions()["Functions"]

        for function in functions:
            function_name = function["FunctionName"]
            try:
                concurrency_configs = self.aws_clients.lambda_client.list_provisioned_concurrency_configs(
                    FunctionName=function_name)["ProvisionedConcurrencyConfigs"]

                for config in concurrency_configs:
                    version = config["FunctionVersion"]
                    allocated_concurrent_executions = config["RequestedProvisionedConcurrentExecutions"]
                    print(
                        f"Processing Provisioned Concurrency Configuration for Lambda Function: {function_name}, Version: {version}")

                    attributes = {
                        "id": f"{function_name}-{version}",
                        "function_name": function_name,
                        "qualifier": version,
                        "provisioned_concurrent_executions": allocated_concurrent_executions,
                    }
                    self.hcl.process_resource("aws_lambda_provisioned_concurrency_config",
                                              f"{function_name.replace('-', '_')}_provisioned_concurrency_{version}", attributes)
            except self.aws_clients.lambda_client.exceptions.ResourceNotFoundException:
                print(
                    f"  No provisioned concurrency configuration found for Lambda Function: {function_name}")
