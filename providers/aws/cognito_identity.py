import os
from utils.hcl import HCL


class CognitoIdentity:
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


    def cognito_identity(self):
        self.hcl.prepare_folder(os.path.join("generated", "cognito_identity"))

        if "gov" not in self.region:
            self.aws_cognito_identity_pool()
            self.aws_cognito_identity_pool_provider_principal_tag()
            self.aws_cognito_identity_pool_roles_attachment()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_cognito_identity_pool(self):
        print("Processing Cognito Identity Pools...")

        paginator = self.aws_clients.cognito_identity_client.get_paginator(
            "list_identity_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["IdentityPools"]:
                pool_id = pool["IdentityPoolId"]
                identity_pool = self.aws_clients.cognito_identity_client.describe_identity_pool(
                    IdentityPoolId=pool_id)["IdentityPool"]

                print(f"Processing Cognito Identity Pool: {pool_id}")

                attributes = {
                    "id": pool_id,
                    "identity_pool_name": identity_pool["IdentityPoolName"],
                    "allow_unauthenticated_identities": identity_pool["AllowUnauthenticatedIdentities"],
                }
                self.hcl.process_resource(
                    "aws_cognito_identity_pool", pool_id.replace("-", "_"), attributes)

    def aws_cognito_identity_pool_provider_principal_tag(self):
        print("Processing Cognito Identity Pool Provider Principal Tags...")

        paginator = self.aws_clients.cognito_identity_client.get_paginator(
            "list_identity_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["IdentityPools"]:
                pool_id = pool["IdentityPoolId"]
                pool_details = self.aws_clients.cognito_identity_client.describe_identity_pool(
                    IdentityPoolId=pool_id)
                identity_pool_arn = pool_details["IdentityPoolArn"]
                tags = self.aws_clients.cognito_identity_client.list_tags_for_resource(
                    ResourceArn=identity_pool_arn)["Tags"]

                if tags:
                    for tag_key, tag_value in tags.items():
                        print(
                            f"Processing Cognito Identity Pool Provider Principal Tag: {tag_key}")

                        attributes = {
                            "id": f"{pool_id}:{tag_key}",
                            "identity_pool_id": pool_id,
                            "tag_key": tag_key,
                            "tag_value": tag_value,
                        }
                        self.hcl.process_resource(
                            "aws_cognito_identity_pool_provider_principal_tag", f"{pool_id}_{tag_key}".replace("-", "_"), attributes)

    def aws_cognito_identity_pool_roles_attachment(self):
        print("Processing Cognito Identity Pool Roles Attachments...")

        paginator = self.aws_clients.cognito_identity_client.get_paginator(
            "list_identity_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["IdentityPools"]:
                pool_id = pool["IdentityPoolId"]
                identity_pool = self.aws_clients.cognito_identity_client.describe_identity_pool(
                    IdentityPoolId=pool_id)["IdentityPool"]

                if "Roles" in identity_pool:
                    print(
                        f"Processing Cognito Identity Pool Roles Attachment: {pool_id}")

                    attributes = {
                        "id": pool_id,
                        "identity_pool_id": pool_id,
                        "roles": identity_pool["Roles"],
                    }

                    if "RoleMappings" in identity_pool:
                        attributes["role_mapping"] = identity_pool["RoleMappings"]

                    self.hcl.process_resource(
                        "aws_cognito_identity_pool_roles_attachment", pool_id.replace("-", "_"), attributes)
