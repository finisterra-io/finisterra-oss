from ...utils.hcl import HCL
import json
import logging
import inspect

logger = logging.getLogger('finisterra')


class IAM:
    def __init__(self, provider_instance, hcl=None):
        self.provider_instance = provider_instance

        if not hcl:
            self.hcl = HCL(self.provider_instance.schema_data)
            self.hcl.global_region = "global"
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

        self.aws_iam_role()
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

    def aws_iam_role(self, role_name=None, ftstack=None):
        resource_type = "aws_iam_role"
        logger.debug("Processing IAM Roles...")

        # If role_name is provided, process only that specific role
        if role_name:
            if ftstack and self.hcl.id_resource_processed(resource_type, role_name, ftstack):
                logger.debug(
                    f"  Skipping IAM Role: {role_name} - already processed")
                return

            # Fetch and process the specific role
            try:
                role = self.provider_instance.aws_clients.iam_client.get_role(
                    RoleName=role_name)["Role"]
                self.process_iam_role(role, ftstack)
            except Exception as e:
                logger.debug(f"Error fetching IAM Role {role_name}: {e}")
            return

        # Code to process all roles if no specific role_name is provided
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
            "list_roles")
        filtered_roles = []
        for page in paginator.paginate():
            for role in page["Roles"]:
                try:
                    tags = self.provider_instance.aws_clients.iam_client.list_role_tags(
                        RoleName=role['RoleName'])["Tags"]
                    # Convert tags list to a dictionary for easier matching
                    tag_dict = {tag['Key']: tag['Value'] for tag in tags}
                    if self.role_matches_filters(tag_dict):
                        filtered_roles.append(role)
                except Exception as e:
                    logger.debug(
                        f"Error listing tags for IAM Role {role['RoleName']}: {e}")
                    continue
        total = len(filtered_roles)
        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for role in filtered_roles:
            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{role['RoleName']}[/]")
            self.process_iam_role(role, ftstack)

    def process_iam_role(self, role, ftstack=None):
        resource_type = "aws_iam_role"
        current_role_name = role["RoleName"]
        role_path = role["Path"]

        # Ignore roles managed or created by AWS
        if role_path.startswith("/aws-service-role/") or "AWS-QuickSetup" in current_role_name:
            return

        logger.debug(f"Processing IAM Role: {current_role_name}")
        id = current_role_name
        attributes = {
            "id": id,
            "name": current_role_name,
            "assume_role_policy": json.dumps(role["AssumeRolePolicyDocument"]),
            "description": role.get("Description"),
            "path": role_path,
        }
        self.hcl.process_resource(resource_type, current_role_name, attributes)
        if not ftstack:
            ftstack = "iam"
        self.hcl.add_stack(resource_type, id, ftstack)

        # Call aws_iam_role_policy_attachment for the current role_name
        self.aws_iam_role_policy_attachment(current_role_name, ftstack)

        # Now call aws_iam_instance_profile for the current role_name
        self.aws_iam_instance_profile(current_role_name)

    def role_matches_filters(self, role_tags):
        """
        Check if the role's tags match all filter conditions.
        :param role_tags: Dictionary of role tags
        :return: True if role matches all filter conditions, False otherwise.
        """
        return all(
            any(role_tags.get(f['Name'].replace('tag:', ''),
                '') == value for value in f['Values'])
            for f in self.provider_instance.filters
        ) if self.provider_instance.filters else True

    def aws_iam_instance_profile(self, role_name):
        logger.debug("Processing IAM Instance Profiles...")
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
            "list_instance_profiles")

        for page in paginator.paginate():
            for instance_profile in page["InstanceProfiles"]:
                # Check if any of the associated roles match the role_name
                associated_roles = [role["RoleName"]
                                    for role in instance_profile["Roles"]]
                if role_name not in associated_roles:
                    # If the current instance profile's roles do not include the filtered role name, skip it.
                    continue

                instance_profile_name = instance_profile["InstanceProfileName"]
                logger.debug(
                    f"Processing IAM Instance Profile: {instance_profile_name} for role {role_name}")

                attributes = {
                    "id": instance_profile_name,
                    "name": instance_profile_name,
                    "path": instance_profile["Path"],
                    "role": role_name,
                }
                self.hcl.process_resource(
                    "aws_iam_instance_profile", instance_profile_name, attributes)

    def aws_iam_role_policy_attachment(self, role_name, ftstack):
        logger.debug(
            f"Processing IAM Role Policy Attachments for {role_name}...")

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

                # if not policy_arn.startswith('arn:aws:iam::aws:policy/') and '/service-role/' not in policy_arn:
                if not policy_arn.startswith('arn:aws:iam::aws:policy/'):
                    self.aws_iam_policy(policy_arn, ftstack)

    def aws_iam_policy(self, policy_arn, ftstack=None):
        # Check if the policy is AWS managed
        if ':aws:policy/' in policy_arn:
            logger.debug(f"Skipping AWS managed policy: {policy_arn}")
            return  # This is an AWS managed policy

        resource_type = "aws_iam_policy"
        policy_name = policy_arn.split('/')[-1]

        logger.debug(f"Processing IAM Policy: {policy_name}")
        id = policy_arn
        attributes = {
            "id": id,
            "arn": policy_arn,
            "name": policy_name,
        }
        self.hcl.process_resource(resource_type, policy_name, attributes)

        if not ftstack:
            ftstack = "iam"
        self.hcl.add_stack(resource_type, id, ftstack)

    def aws_iam_saml_provider(self, provider_arn=None, ftstack=None):
        resource_type = "aws_iam_saml_provider"
        logger.debug("Processing IAM SAML Providers...")

        # If provider_arn is provided, process only that specific SAML provider
        if provider_arn:
            if ftstack and self.hcl.id_resource_processed(resource_type, provider_arn, ftstack):
                logger.debug(
                    f"  Skipping IAM SAML Provider: {provider_arn} - already processed")
                return

            # Fetch and process the specific SAML provider
            try:
                self.process_iam_saml_provider(provider_arn, ftstack)
            except Exception as e:
                logger.debug(
                    f"Error fetching IAM SAML Provider {provider_arn}: {e}")
            return

        # Code to process all SAML providers if no specific provider_arn is provided
        paginator = self.provider_instance.aws_clients.iam_client.get_paginator(
            "list_saml_providers")
        for page in paginator.paginate():
            for provider in page["SAMLProviderList"]:
                try:
                    self.process_iam_saml_provider(provider["Arn"], ftstack)
                except Exception as e:
                    logger.debug(
                        f"Error fetching IAM SAML Provider {provider['Arn']}: {e}")

    def process_iam_saml_provider(self, provider_arn, ftstack=None):
        resource_type = "aws_iam_saml_provider"
        # saml_provider = self.provider_instance.aws_clients.iam_client.get_saml_provider(
        #     SAMLProviderArn=provider_arn)
        logger.debug(f"Processing IAM SAML Provider: {provider_arn}")
        # Assuming the ARN format allows us to extract an identifier this way
        id = provider_arn

        attributes = {
            "id": id,
        }
        self.hcl.process_resource(resource_type, id, attributes)
        if not ftstack:
            ftstack = "saml"
        self.hcl.add_stack(resource_type, id, ftstack)
