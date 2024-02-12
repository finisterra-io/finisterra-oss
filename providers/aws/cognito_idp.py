import os
from utils.hcl import HCL


class CognitoIDP:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {        }
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.workspace_id = workspace_id
        self.modules = modules
        self.hcl = HCL(self.schema_data, self.provider_name)

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


    def cognito_idp(self):
        self.hcl.prepare_folder(os.path.join("generated", "cognito_idp"))

        self.aws_cognito_identity_provider()
        # self.aws_cognito_managed_user_pool_client() # use aws_cognito_user_pool_client instead
        self.aws_cognito_resource_server()

        if "gov" not in self.region:
            self.aws_cognito_risk_configuration()
            self.aws_cognito_user_pool_ui_customization()

        self.aws_cognito_user()
        self.aws_cognito_user_group()
        self.aws_cognito_user_in_group()
        self.aws_cognito_user_pool()
        self.aws_cognito_user_pool_client()
        self.aws_cognito_user_pool_domain()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_cognito_identity_provider(self):
        print("Processing Cognito Identity Providers...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                providers = self.aws_clients.cognito_idp_client.list_identity_providers(UserPoolId=pool_id)[
                    "Providers"]
                for provider in providers:
                    attributes = {
                        "id": pool_id+":"+provider["ProviderName"],
                        "user_pool_id": pool_id,
                        "provider_name": provider["ProviderName"],
                        "provider_type": provider["ProviderType"],
                    }
                    self.hcl.process_resource(
                        "aws_cognito_identity_provider", provider["ProviderName"].replace("-", "_"), attributes)

    def aws_cognito_managed_user_pool_client(self):
        print("Processing Cognito Managed User Pool Clients...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                clients = self.aws_clients.cognito_idp_client.list_user_pool_clients(UserPoolId=pool_id)[
                    "UserPoolClients"]
                for client in clients:
                    attributes = {
                        "id": client["ClientId"],
                        "user_pool_id": pool_id,
                        "client_name": client["ClientName"],
                        "client_id": client["ClientId"],
                    }
                    self.hcl.process_resource(
                        "aws_cognito_managed_user_pool_client", client["ClientId"].replace("-", "_"), attributes)

    def aws_cognito_resource_server(self):
        print("Processing Cognito Resource Servers...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                resource_servers = self.aws_clients.cognito_idp_client.list_resource_servers(
                    UserPoolId=pool_id, MaxResults=50)["ResourceServers"]
                for server in resource_servers:
                    attributes = {
                        "id": server["Identifier"],
                        "user_pool_id": pool_id,
                        "identifier": server["Identifier"],
                        "name": server["Name"],
                        "scopes": server["Scopes"],
                    }
                    self.hcl.process_resource(
                        "aws_cognito_resource_server", server["Identifier"].replace("-", "_"), attributes)

    def aws_cognito_risk_configuration(self):
        print("Processing Cognito Risk Configurations...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                try:
                    risk_config_response = self.aws_clients.cognito_idp_client.describe_risk_configuration(
                        UserPoolId=pool_id)
                    if "RiskConfiguration" in risk_config_response:
                        risk_config = risk_config_response["RiskConfiguration"]
                        attributes = {
                            "id": risk_config["ClientId"],
                            "user_pool_id": pool_id,
                            "client_id": risk_config["ClientId"],
                            "compromised_credentials_risk_configuration": risk_config["CompromisedCredentialsRiskConfiguration"],
                            "account_takeover_risk_configuration": risk_config["AccountTakeoverRiskConfiguration"],
                        }
                        self.hcl.process_resource(
                            "aws_cognito_risk_configuration", risk_config["ClientId"].replace("-", "_"), attributes)
                    else:
                        print(
                            f"  No Risk Configuration key found for user pool: {pool_id}")
                except self.aws_clients.cognito_idp_client.exceptions.ResourceNotFoundException:
                    print(
                        f"  No Risk Configuration found for user pool: {pool_id}")

    def aws_cognito_user(self):
        print("Processing Cognito Users...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                user_paginator = self.aws_clients.cognito_idp_client.get_paginator(
                    "list_users")
                for user_page in user_paginator.paginate(UserPoolId=pool_id):
                    for user in user_page["Users"]:
                        attributes = {
                            "id": user["Username"],
                            "user_pool_id": pool_id,
                            "username": user["Username"],
                            # "attributes": user["Attributes"],
                        }
                        self.hcl.process_resource(
                            "aws_cognito_user", user["Username"].replace("-", "_"), attributes)

    def aws_cognito_user_group(self):
        print("Processing Cognito User Groups...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                group_paginator = self.aws_clients.cognito_idp_client.get_paginator(
                    "list_groups")
                for group_page in group_paginator.paginate(UserPoolId=pool_id):
                    for group in group_page["Groups"]:
                        attributes = {
                            "id": group["GroupName"],
                            "user_pool_id": pool_id,
                            "name": group["GroupName"],
                            # "description": group.get("Description", ""),
                            # "role_arn": group.get("RoleArn", ""),
                            # "precedence": group.get("Precedence", ""),
                        }
                        self.hcl.process_resource(
                            "aws_cognito_user_group", group["GroupName"].replace("-", "_"), attributes)

    def aws_cognito_user_in_group(self):
        print("Processing Cognito Users in Groups...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                group_paginator = self.aws_clients.cognito_idp_client.get_paginator(
                    "list_groups")
                for group_page in group_paginator.paginate(UserPoolId=pool_id):
                    for group in group_page["Groups"]:
                        user_paginator = self.aws_clients.cognito_idp_client.get_paginator(
                            "list_users_in_group")
                        for user_page in user_paginator.paginate(UserPoolId=pool_id, GroupName=group["GroupName"]):
                            for user in user_page["Users"]:
                                attributes = {
                                    "id": f"{pool_id}-{group['GroupName']}-{user['Username']}",
                                    "user_pool_id": pool_id,
                                    "username": user["Username"],
                                    "group_name": group["GroupName"],
                                }
                                self.hcl.process_resource(
                                    "aws_cognito_user_in_group", user["Username"].replace("-", "_"), attributes)

    def aws_cognito_user_pool(self):
        print("Processing Cognito User Pools...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                user_pool = self.aws_clients.cognito_idp_client.describe_user_pool(UserPoolId=pool_id)[
                    "UserPool"]
                attributes = {
                    "id": pool_id,
                    "name": user_pool["Name"],
                    # "admin_create_user_config": user_pool["AdminCreateUserConfig"],
                    # "auto_verified_attributes": user_pool["AutoVerifiedAttributes"],
                    # "email_verification_message": user_pool["EmailVerificationMessage"],
                    # "email_verification_subject": user_pool["EmailVerificationSubject"],
                    # "sms_authentication_message": user_pool["SmsAuthenticationMessage"],
                    # "sms_verification_message": user_pool["SmsVerificationMessage"],
                    # "verification_message_template": user_pool["VerificationMessageTemplate"],
                    # "mfa_configuration": user_pool["MfaConfiguration"],
                    # "password_policy": user_pool["Policies"]["PasswordPolicy"],
                }
                self.hcl.process_resource(
                    "aws_cognito_user_pool", user_pool["Name"].replace("-", "_"), attributes)

    def aws_cognito_user_pool_client(self):
        print("Processing Cognito User Pool Clients...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                client_paginator = self.aws_clients.cognito_idp_client.get_paginator(
                    "list_user_pool_clients")
                for client_page in client_paginator.paginate(UserPoolId=pool_id, MaxResults=60):
                    for client in client_page["UserPoolClients"]:
                        client_details = self.aws_clients.cognito_idp_client.describe_user_pool_client(
                            UserPoolId=pool_id, ClientId=client["ClientId"])["UserPoolClient"]
                        attributes = {
                            "id": client["ClientId"],
                            "name": client["ClientName"],
                            "user_pool_id": pool_id,
                            "explicit_auth_flows": client_details["ExplicitAuthFlows"],
                            "supported_identity_providers": client_details["SupportedIdentityProviders"],
                        }
                        self.hcl.process_resource(
                            "aws_cognito_user_pool_client", client["ClientName"].replace("-", "_"), attributes)

    def aws_cognito_user_pool_domain(self):
        print("Processing Cognito User Pool Domains...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                user_pool = self.aws_clients.cognito_idp_client.describe_user_pool(
                    UserPoolId=pool_id)["UserPool"]

                if "Domain" in user_pool:
                    domain = user_pool["Domain"]
                    domain_description = self.aws_clients.cognito_idp_client.describe_user_pool_domain(
                        Domain=domain)["DomainDescription"]
                    attributes = {
                        "id": domain_description["Domain"],
                        "domain": domain_description["Domain"],
                        "user_pool_id": pool_id,
                    }
                    self.hcl.process_resource(
                        "aws_cognito_user_pool_domain", domain_description["Domain"].replace("-", "_"), attributes)

    def aws_cognito_user_pool_ui_customization(self):
        print("Processing Cognito User Pool UI Customizations...")

        paginator = self.aws_clients.cognito_idp_client.get_paginator("list_user_pools")
        for page in paginator.paginate(MaxResults=60):
            for pool in page["UserPools"]:
                pool_id = pool["Id"]
                try:
                    ui_customization_response = self.aws_clients.cognito_idp_client.get_ui_customization(
                        UserPoolId=pool_id)
                    if "UICustomization" in ui_customization_response:
                        ui_customization = ui_customization_response["UICustomization"]
                        print(
                            f"Processing Cognito User Pool UI Customization: {pool_id}")

                        if "ClientId" in ui_customization:
                            attributes = {
                                "id": pool_id,
                                "user_pool_id": pool_id,
                                "client_id": ui_customization["ClientId"],
                                "css": ui_customization["CSS"],
                                "image_url": ui_customization["ImageUrl"],
                            }
                            self.hcl.process_resource(
                                "aws_cognito_user_pool_ui_customization", pool_id.replace("-", "_"), attributes)
                        else:
                            print(
                                f"  No ClientId found for UI customization of user pool: {pool_id}")
                    else:
                        print(
                            f"  No UI customization found for user pool: {pool_id}")
                except self.aws_clients.cognito_idp_client.exceptions.ResourceNotFoundException:
                    print(
                        f"  ResourceNotFoundException: No UI customization found for user pool: {pool_id}")
