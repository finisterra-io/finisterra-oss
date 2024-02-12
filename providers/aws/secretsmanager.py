import os
from utils.hcl import HCL


class Secretsmanager:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.workspace_id = workspace_id
        self.modules = modules
        self.hcl = HCL(self.schema_data, self.provider_name)

        self.hcl.region = region
        self.hcl.account_id = aws_account_id

    def secretsmanager(self):
        self.hcl.prepare_folder(os.path.join("generated", "secretsmanager"))

        self.aws_secretsmanager_secret()
        self.aws_secretsmanager_secret_policy()
        self.aws_secretsmanager_secret_rotation()
        self.aws_secretsmanager_secret_version()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_secretsmanager_secret(self):
        print("Processing Secrets Manager Secrets...")

        paginator = self.aws_clients.secretsmanager_client.get_paginator("list_secrets")
        for page in paginator.paginate():
            for secret in page["SecretList"]:
                secret_id = secret["ARN"]
                secret_name = secret["Name"]
                print(f"Processing Secrets Manager Secret: {secret_name}")

                attributes = {
                    "id": secret_id,
                    "name": secret_name,
                }
                self.hcl.process_resource(
                    "aws_secretsmanager_secret", secret_name.replace("-", "_"), attributes)

    def aws_secretsmanager_secret_policy(self):
        print("Processing Secrets Manager Secret Policies...")

        paginator = self.aws_clients.secretsmanager_client.get_paginator("list_secrets")
        for page in paginator.paginate():
            for secret in page["SecretList"]:
                secret_id = secret["ARN"]
                secret_name = secret["Name"]

                try:
                    policy_response = self.aws_clients.secretsmanager_client.get_resource_policy(
                        SecretId=secret_id)
                    if 'ResourcePolicy' in policy_response:    # Check if 'ResourcePolicy' exists
                        policy = policy_response["ResourcePolicy"]
                        print(
                            f"Processing Secrets Manager Secret Policy for Secret: {secret_name}")

                        attributes = {
                            "id": secret_id,
                            "secret_arn": secret_id,
                            "policy": policy,
                        }
                        self.hcl.process_resource(
                            "aws_secretsmanager_secret_policy", secret_name.replace("-", "_"), attributes)
                    else:
                        print(f"  No policy found for Secret: {secret_name}")
                except self.aws_clients.secretsmanager_client.exceptions.ResourceNotFoundException:
                    print(f"  No policy found for Secret: {secret_name}")

    def aws_secretsmanager_secret_rotation(self):
        print("Processing Secrets Manager Secret Rotations...")

        paginator = self.aws_clients.secretsmanager_client.get_paginator("list_secrets")
        for page in paginator.paginate():
            for secret in page["SecretList"]:
                secret_id = secret["ARN"]
                secret_name = secret["Name"]

                try:
                    rotation_response = self.aws_clients.secretsmanager_client.describe_secret(
                        SecretId=secret_id)
                    rotation_enabled = rotation_response["RotationEnabled"]
                    if rotation_enabled:
                        rotation_lambda_arn = rotation_response["RotationLambdaARN"]
                        rotation_rules = rotation_response["RotationRules"]

                        print(
                            f"Processing Secrets Manager Secret Rotation for Secret: {secret_name}")

                        attributes = {
                            "id": secret_id,
                            "secret_arn": secret_id,
                            "rotation_lambda_arn": rotation_lambda_arn,
                            "rotation_rules": {
                                "automatically_after_days": rotation_rules["AutomaticallyAfterDays"],
                            },
                        }
                        self.hcl.process_resource(
                            "aws_secretsmanager_secret_rotation", secret_name.replace("-", "_"), attributes)
                except KeyError:
                    print(f"  No rotation found for Secret: {secret_name}")

    def aws_secretsmanager_secret_version(self):
        print("Processing Secrets Manager Secret Versions...")

        paginator = self.aws_clients.secretsmanager_client.get_paginator("list_secrets")
        for page in paginator.paginate():
            for secret in page["SecretList"]:
                secret_id = secret["ARN"]
                secret_name = secret["Name"]

                # Call list_secret_version_ids directly instead of paginating
                versions = self.aws_clients.secretsmanager_client.list_secret_version_ids(
                    SecretId=secret_id)

                for version in versions["Versions"]:
                    version_id = version["VersionId"]

                    if "AWSCURRENT" in version["VersionStages"]:
                        print(
                            f"Processing Secrets Manager Secret Version: {version_id} for Secret: {secret_name}")

                        attributes = {
                            "id": f"{secret_id}|{version_id}",
                            "secret_id": secret_id,
                            "version_id": version_id,
                        }
                        self.hcl.process_resource(
                            "aws_secretsmanager_secret_version", f"{secret_name.replace('-', '_')}_version_{version_id.replace('-', '_')}", attributes)
