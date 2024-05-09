from ...utils.hcl import HCL
import json
import logging
import inspect

logger = logging.getLogger('finisterra')


class IAM_POLICY:
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

    def iam(self):
        self.hcl.prepare_folder()

        self.aws_iam_policy()

        self.hcl.refresh_state()

        self.hcl.request_tf_code()

    def aws_iam_access_key(self):
        logger.debug("Processing IAM Access Keys...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator("list_users")

        for page in paginator.paginate():
            for user in page["Users"]:
                user_name = user["UserName"]
                access_keys_paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
                    "list_access_keys")

                for access_keys_page in access_keys_paginator.paginate(UserName=user_name):
                    for access_key in access_keys_page["AccessKeyMetadata"]:
                        access_key_id = access_key["AccessKeyId"]
                        logger.debug(
                            f"Processing IAM Access Key: {access_key_id} for User: {user_name}")

                        attributes = {
                            "id": access_key_id,
                            "user": user_name,
                            "status": access_key["Status"],
                            "create_date": access_key["CreateDate"].isoformat(),
                        }
                        self.hcl.process_resource(
                            "aws_iam_access_key", access_key_id.replace("-", "_"), attributes)

    def aws_iam_account_alias(self):
        logger.debug("Processing IAM Account Aliases...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
            "list_account_aliases")

        for page in paginator.paginate():
            for alias in page["AccountAliases"]:
                logger.debug(f"Processing IAM Account Alias: {alias}")

                attributes = {
                    "id": alias,
                    "name": alias,
                }
                self.hcl.process_resource(
                    "aws_iam_account_alias", alias.replace("-", "_"), attributes)

    def aws_iam_account_password_policy(self):
        logger.debug("Processing IAM Account Password Policy...")

        try:
            response = self.provider_instance.aws_clients.iam_client.get_account_password_policy()
            policy = response["PasswordPolicy"]
            attributes = {
                "id": "iam-account-password-policy",
                "minimum_password_length": policy.get("MinimumPasswordLength"),
                "require_symbols": policy.get("RequireSymbols"),
                "require_numbers": policy.get("RequireNumbers"),
                "require_uppercase_characters": policy.get("RequireUppercaseCharacters"),
                "require_lowercase_characters": policy.get("RequireLowercaseCharacters"),
                "allow_users_to_change_password": policy.get("AllowUsersToChangePassword"),
                "expire_passwords": policy.get("ExpirePasswords"),
                "max_password_age": policy.get("MaxPasswordAge"),
                "password_reuse_prevention": policy.get("PasswordReusePrevention"),
                "hard_expiry": policy.get("HardExpiry"),
            }
            self.hcl.process_resource(
                "aws_iam_account_password_policy", "iam_account_password_policy", attributes)
            logger.debug("  IAM Account Password Policy processed.")
        except self.provider_instance.aws_clients.iam_client.exceptions.NoSuchEntityException:
            logger.debug("  No IAM Account Password Policy found.")

    def aws_iam_group(self):
        logger.debug("Processing IAM Groups...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator("list_groups")

        for page in paginator.paginate():
            for group in page["Groups"]:
                group_name = group["GroupName"]
                logger.debug(f"Processing IAM Group: {group_name}")

                attributes = {
                    "id": group["GroupId"],
                    "name": group_name,
                    "arn": group["Arn"],
                    "path": group["Path"],
                    "create_date": group["CreateDate"].isoformat(),
                }
                self.hcl.process_resource(
                    "aws_iam_group", group_name.replace("-", "_"), attributes)

    def aws_iam_group_policy(self):
        logger.debug("Processing IAM Group Policies...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator("list_groups")

        for page in paginator.paginate():
            for group in page["Groups"]:
                group_name = group["GroupName"]
                policies_paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
                    "list_group_policies")

                for policies_page in policies_paginator.paginate(GroupName=group_name):
                    for policy_name in policies_page["PolicyNames"]:
                        logger.debug(
                            f"Processing IAM Group Policy: {group_name} - {policy_name}")

                        policy_document = self.provider_instance.aws_clients.iam_client.get_group_policy(
                            GroupName=group_name, PolicyName=policy_name)
                        attributes = {
                            "id": f"{group_name}:{policy_name}",
                            "group_name": group_name,
                            "policy_name": policy_name,
                            "policy_document": json.dumps(policy_document["PolicyDocument"]),
                        }
                        self.hcl.process_resource(
                            "aws_iam_group_policy", f"{group_name}_{policy_name}", attributes)

    def aws_iam_instance_profile(self):
        logger.debug("Processing IAM Instance Profiles...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
            "list_instance_profiles")

        for page in paginator.paginate():
            for instance_profile in page["InstanceProfiles"]:
                instance_profile_name = instance_profile["InstanceProfileName"]
                logger.debug(
                    f"Processing IAM Instance Profile: {instance_profile_name}")

                attributes = {
                    "id": instance_profile_name,
                    "name": instance_profile_name,
                    "path": instance_profile["Path"],
                    "role": instance_profile["Roles"][0]["RoleName"] if instance_profile["Roles"] else None,
                }
                self.hcl.process_resource(
                    "aws_iam_instance_profile", instance_profile_name, attributes)

    def aws_iam_openid_connect_provider(self):
        logger.debug("Processing IAM OpenID Connect Providers...")
        openid_providers = self.provider_instance.aws_clients.iam_client.list_open_id_connect_providers()[
            "OpenIDConnectProviderList"]

        for provider in openid_providers:
            provider_arn = provider["Arn"]
            logger.debug(
                f"Processing IAM OpenID Connect Provider: {provider_arn}")

            provider_details = self.provider_instance.aws_clients.iam_client.get_open_id_connect_provider(
                OpenIDConnectProviderArn=provider_arn)
            attributes = {
                "id": provider_arn,
                "client_id_list": provider_details["ClientIDList"],
                "thumbprint_list": provider_details["ThumbprintList"],
                "url": provider_details["Url"],
            }
            self.hcl.process_resource(
                "aws_iam_openid_connect_provider", provider_arn.split(':')[-1], attributes)

    def aws_iam_policy(self):
        logger.debug("Processing IAM Policies...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator("list_policies")

        for page in paginator.paginate(Scope='Local'):
            for policy in page["Policies"]:
                policy_name = policy["PolicyName"]
                policy_arn = policy["Arn"]

                # Ignore AWS managed policies and policies with '/service-role/' in the ARN
                if policy_arn.startswith('arn:aws:iam::aws:policy/') or '/service-role/' in policy_arn:
                    continue

                # if policy_name != "xxxxxx":
                #     continue

                logger.debug(f"Processing IAM Policy: {policy_name}")

                attributes = {
                    "id": policy_arn,
                    "arn": policy_arn,
                    "name": policy_name,
                }
                self.hcl.process_resource(
                    "aws_iam_policy", policy_name, attributes)

    def aws_iam_role_policy(self):
        logger.debug("Processing IAM Role Policies...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator("list_roles")

        for page in paginator.paginate():
            for role in page["Roles"]:
                role_name = role["RoleName"]

                policy_paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
                    "list_role_policies")
                for policy_page in policy_paginator.paginate(RoleName=role_name):
                    for policy_name in policy_page["PolicyNames"]:
                        policy_document = self.provider_instance.aws_clients.iam_client.get_role_policy(
                            RoleName=role_name, PolicyName=policy_name)
                        logger.debug(
                            f"Processing IAM Role Policy: {policy_name} for Role: {role_name}")

                        attributes = {
                            "id": f"{role_name}:{policy_name}",
                            "name": policy_name,
                            "role": role_name,
                            "policy": json.dumps(policy_document["PolicyDocument"]),
                        }
                        self.hcl.process_resource(
                            "aws_iam_role_policy", f"{role_name}_{policy_name}", attributes)

    def aws_iam_saml_provider(self):
        logger.debug("Processing IAM SAML Providers...")
        saml_providers = self.provider_instance.aws_clients.iam_client.list_saml_providers()[
            "SAMLProviderList"]

        for provider in saml_providers:
            provider_arn = provider["Arn"]
            provider_name = provider_arn.split("/")[-1]
            logger.debug(f"Processing IAM SAML Provider: {provider_name}")

            metadata_document = self.provider_instance.aws_clients.iam_client.get_saml_provider(
                SAMLProviderArn=provider_arn)["SAMLMetadataDocument"]

            attributes = {
                "id": provider_arn,
                "name": provider_name,
                "saml_metadata_document": metadata_document,
            }
            self.hcl.process_resource(
                "aws_iam_saml_provider", provider_name, attributes)

    def aws_iam_server_certificate(self):
        logger.debug("Processing IAM Server Certificates...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
            "list_server_certificates")

        for page in paginator.paginate():
            for cert in page["ServerCertificateMetadataList"]:
                cert_id = cert["ServerCertificateId"]
                cert_name = cert["ServerCertificateName"]
                logger.debug(f"Processing IAM Server Certificate: {cert_name}")

                server_cert = self.provider_instance.aws_clients.iam_client.get_server_certificate(
                    ServerCertificateName=cert_name)
                cert_body = server_cert["ServerCertificate"]["CertificateBody"]
                cert_chain = server_cert["ServerCertificate"].get(
                    "CertificateChain", None)

                attributes = {
                    "id": cert_id,
                    "name": cert_name,
                    "certificate_body": cert_body,
                }
                if cert_chain:
                    attributes["certificate_chain"] = cert_chain

                self.hcl.process_resource(
                    "aws_iam_server_certificate", cert_name, attributes)

    def aws_iam_service_linked_role(self):
        logger.debug("Processing IAM Service Linked Roles...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator("list_roles")

        for page in paginator.paginate():
            for role in page["Roles"]:
                if "ServiceLinkedRole" in role["Path"]:
                    role_name = role["RoleName"]
                    logger.debug(
                        f"Processing IAM Service Linked Role: {role_name}")

                    attributes = {
                        "id": role["RoleId"],
                        "name": role_name,
                        "aws_service_name": role["AssumeRolePolicyDocument"]["Statement"][0]["Principal"]["Service"],
                    }
                    self.hcl.process_resource(
                        "aws_iam_service_linked_role", role_name, attributes)

    def aws_iam_service_specific_credential(self):
        logger.debug("Processing IAM Service Specific Credentials...")

        users = self.provider_instance.aws_clients.iam_client.list_users()["Users"]
        for user in users:
            user_name = user["UserName"]
            service_credentials = self.provider_instance.aws_clients.iam_client.list_service_specific_credentials(UserName=user_name)[
                "ServiceSpecificCredentials"]

            for credential in service_credentials:
                service_name = credential["ServiceName"]
                credential_id = service_name+":"+user_name + \
                    ":"+credential["ServiceSpecificCredentialId"]
                logger.debug(
                    f"Processing IAM Service Specific Credential: {credential_id} for user: {user_name}")

                attributes = {
                    "id": credential_id,
                    "user_name": user_name,
                    "service_name": service_name,
                }
                self.hcl.process_resource(
                    "aws_iam_service_specific_credential", credential_id, attributes)

    def aws_iam_signing_certificate(self):
        logger.debug("Processing IAM Signing Certificates...")

        users = self.provider_instance.aws_clients.iam_client.list_users()["Users"]
        for user in users:
            user_name = user["UserName"]
            signing_certificates = self.provider_instance.aws_clients.iam_client.list_signing_certificates(
                UserName=user_name)["Certificates"]

            for certificate in signing_certificates:
                certificate_id = certificate["CertificateId"]
                logger.debug(
                    f"Processing IAM Signing Certificate: {certificate_id} for user: {user_name}")

                attributes = {
                    "id": certificate_id,
                    "user_name": user_name,
                    "certificate_body": certificate["CertificateBody"],
                    "status": certificate["Status"],
                }
                self.hcl.process_resource(
                    "aws_iam_signing_certificate", certificate_id, attributes)

    def aws_iam_user(self):
        logger.debug("Processing IAM Users...")

        users = self.provider_instance.aws_clients.iam_client.list_users()["Users"]
        for user in users:
            user_name = user["UserName"]
            logger.debug(f"Processing IAM User: {user_name}")

            attributes = {
                "id": user_name,
                # "name": user_name,
                # "path": user["Path"],
                # "arn": user["Arn"],
            }
            self.hcl.process_resource("aws_iam_user", user_name, attributes)

    def aws_iam_user_group_membership(self):
        logger.debug("Processing IAM User Group Memberships...")

        users = self.provider_instance.aws_clients.iam_client.list_users()["Users"]
        for user in users:
            user_name = user["UserName"]
            groups_for_user = self.provider_instance.aws_clients.iam_client.list_groups_for_user(UserName=user_name)[
                "Groups"]

            for group in groups_for_user:
                group_name = group["GroupName"]
                membership_id = f"{user_name}/{group_name}"
                logger.debug(
                    f"Processing IAM User Group Membership: {membership_id}")

                attributes = {
                    "id": membership_id,
                    "user": user_name,
                    "groups": [group_name],
                }
                self.hcl.process_resource(
                    "aws_iam_user_group_membership", membership_id, attributes)

    def aws_iam_user_login_profile(self):
        logger.debug("Processing IAM User Login Profiles...")

        users = self.provider_instance.aws_clients.iam_client.list_users()["Users"]
        for user in users:
            user_name = user["UserName"]

            try:
                login_profile = self.provider_instance.aws_clients.iam_client.get_login_profile(UserName=user_name)[
                    "LoginProfile"]
                logger.debug(f"Processing IAM User Login Profile: {user_name}")

                attributes = {
                    "id": user_name,
                    "user_name": user_name,
                    "password_reset_required": login_profile["PasswordResetRequired"],
                }
                self.hcl.process_resource(
                    "aws_iam_user_login_profile", user_name, attributes)
            except self.provider_instance.aws_clients.iam_client.exceptions.NoSuchEntityException:
                logger.debug(
                    f"  No login profile found for IAM User: {user_name}")

    def aws_iam_user_policy(self):
        logger.debug("Processing IAM User Policies...")

        users = self.provider_instance.aws_clients.iam_client.list_users()["Users"]
        for user in users:
            user_name = user["UserName"]
            user_policies = self.provider_instance.aws_clients.iam_client.list_user_policies(UserName=user_name)[
                "PolicyNames"]

            for policy_name in user_policies:
                policy_id = f"{user_name}:{policy_name}"
                logger.debug(f"Processing IAM User Policy: {policy_id}")

                policy_document = self.provider_instance.aws_clients.iam_client.get_user_policy(
                    UserName=user_name, PolicyName=policy_name
                )["PolicyDocument"]

                attributes = {
                    "id": policy_id,
                    "name": policy_name,
                    "user_name": user_name,
                    "policy": json.dumps(policy_document),
                }
                self.hcl.process_resource(
                    "aws_iam_user_policy", policy_id, attributes)

    def aws_iam_user_policy_attachment(self):
        logger.debug("Processing IAM User Policy Attachments...")

        users = self.provider_instance.aws_clients.iam_client.list_users()["Users"]
        for user in users:
            user_name = user["UserName"]
            attached_policies = self.provider_instance.aws_clients.iam_client.list_attached_user_policies(
                UserName=user_name)["AttachedPolicies"]

            for policy in attached_policies:
                policy_arn = policy["PolicyArn"]
                policy_name = policy["PolicyName"]
                attachment_id = f"{user_name}_{policy_name}"
                logger.debug(
                    f"Processing IAM User Policy Attachment: {attachment_id}")

                attributes = {
                    "id": attachment_id,
                    "user": user_name,
                    "policy_arn": policy_arn,
                }
                self.hcl.process_resource(
                    "aws_iam_user_policy_attachment", attachment_id, attributes)

    def aws_iam_user_ssh_key(self):
        logger.debug("Processing IAM User SSH Keys...")

        users = self.provider_instance.aws_clients.iam_client.list_users()["Users"]
        for user in users:
            user_name = user["UserName"]
            ssh_keys = self.provider_instance.aws_clients.iam_client.list_ssh_public_keys(UserName=user_name)[
                "SSHPublicKeys"]

            for ssh_key in ssh_keys:
                ssh_key_id = ssh_key["SSHPublicKeyId"]
                logger.debug(f"Processing IAM User SSH Key: {ssh_key_id}")

                attributes = {
                    "id": ssh_key_id,
                    "user_name": user_name,
                    "status": ssh_key["Status"],
                    "encoding": ssh_key["Encoding"],
                    "fingerprint": ssh_key["Fingerprint"],
                }
                self.hcl.process_resource(
                    "aws_iam_user_ssh_key", ssh_key_id, attributes)

    def aws_iam_virtual_mfa_device(self):
        logger.debug("Processing IAM Virtual MFA Devices...")

        mfa_devices = self.provider_instance.aws_clients.iam_client.list_virtual_mfa_devices()[
            "VirtualMFADevices"]
        for mfa_device in mfa_devices:
            mfa_device_arn = mfa_device["SerialNumber"]
            mfa_device_id = mfa_device_arn.split("/")[-1]
            if "User" in mfa_device and "Path" in mfa_device["User"]:
                path = mfa_device["User"]["Path"]
            else:
                path = "/"
            logger.debug(f"Processing IAM Virtual MFA Device: {mfa_device_id}")

            attributes = {
                "id": mfa_device_arn,
                "virtual_mfa_device_name": mfa_device_id,
                "path": path,
                # "arn": mfa_device_arn,
            }

            if "User" in mfa_device:
                user_name = mfa_device["User"]["UserName"]
                attributes["user_name"] = user_name

            self.hcl.process_resource(
                "aws_iam_virtual_mfa_device", mfa_device_id, attributes)

    def aws_iam_group_policy_attachment(self):
        logger.debug("Processing IAM Group Policy Attachments...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator("list_groups")

        for page in paginator.paginate():
            for group in page["Groups"]:
                group_name = group["GroupName"]
                policy_paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
                    "list_attached_group_policies")

                for policy_page in policy_paginator.paginate(GroupName=group_name):
                    for policy in policy_page["AttachedPolicies"]:
                        policy_arn = policy["PolicyArn"]
                        logger.debug(
                            f"Processing IAM Group Policy Attachment: {group_name} - {policy_arn}")

                        attributes = {
                            "id": f"{group_name}/{policy_arn}",
                            "group": group_name,
                            "policy_arn": policy_arn,
                        }
                        self.hcl.process_resource(
                            "aws_iam_group_policy_attachment", f"{group_name}_{policy_arn.split(':')[-1]}", attributes)

    def aws_iam_role_policy_attachment(self):
        logger.debug("Processing IAM Role Policy Attachments...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator("list_roles")

        for page in paginator.paginate():
            for role in page["Roles"]:
                role_name = role["RoleName"]
                policy_paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
                    "list_attached_role_policies")

                for policy_page in policy_paginator.paginate(RoleName=role_name):
                    for policy in policy_page["AttachedPolicies"]:
                        policy_arn = policy["PolicyArn"]
                        logger.debug(
                            f"Processing IAM Role Policy Attachment: {role_name} - {policy_arn}")

                        attributes = {
                            "id": f"{role_name}/{policy_arn}",
                            "role": role_name,
                            "policy_arn": policy_arn,
                        }
                        self.hcl.process_resource(
                            "aws_iam_role_policy_attachment", f"{role_name}_{policy_arn.split(':')[-1]}", attributes)
