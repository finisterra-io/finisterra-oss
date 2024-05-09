import botocore
from ...utils.hcl import HCL
import json
from ...providers.aws.kms import KMS
import logging
import inspect

logger = logging.getLogger('finisterra')


class ECR:
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

        self.kms_instance = KMS(self.provider_instance, self.hcl)

    def get_kms_alias(self, kms_key_id):
        try:
            value = ""
            response = self.provider_instance.aws_clients.kms_client.list_aliases()
            aliases = response.get('Aliases', [])
            while 'NextMarker' in response:
                response = self.provider_instance.aws_clients.kms_client.list_aliases(
                    Marker=response['NextMarker'])
                aliases.extend(response.get('Aliases', []))
            for alias in aliases:
                if 'TargetKeyId' in alias and alias['TargetKeyId'] == kms_key_id.split('/')[-1]:
                    value = alias['AliasName']
                    break
            return value
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'AccessDeniedException':
                return ""
            else:
                raise e

    def ecr(self):
        self.hcl.prepare_folder()

        self.aws_ecr_repository()

        if "gov" not in self.provider_instance.region:
            self.aws_ecr_registry_policy()
            self.aws_ecr_pull_through_cache_rule()
            self.aws_ecr_replication_configuration()
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

    def aws_ecr_repository(self):
        resource_type = "aws_ecr_repository"
        # logger.debug(f"Processing ECR Repositories...")

        # Create a paginator for the describe_repositories operation
        paginator = self.provider_instance.aws_clients.ecr_client.get_paginator(
            'describe_repositories')
        repositories = []

        # Paginate through the repositories, appending each batch to the repositories list
        for page in paginator.paginate():
            repositories.extend(page["repositories"])

        if len(repositories) > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=len(repositories))
        for repo in repositories:
            repository_name = repo["repositoryName"]
            repository_arn = repo["repositoryArn"]
            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{repository_name}[/]")

            logger.debug(f"Processing ECR Repository: {repository_name}")
            id = repository_name

            ftstack = "ecr"
            try:
                tags_response = self.provider_instance.aws_clients.ecr_client.list_tags_for_resource(
                    resourceArn=repository_arn)
                tags = tags_response.get('tags', [])
                for tag in tags:
                    if tag['Key'] == 'ftstack':
                        if tag['Value'] != 'ecr':
                            ftstack = "stack_" + tag['Value']
                        break
            except Exception as e:
                logger.error(f"Error occurred: {e}")

            attributes = {
                "id": id,
                "arn": repository_arn,
            }
            self.hcl.process_resource(
                resource_type, repository_name.replace("-", "_"), attributes)

            encryption_configuration = repo.get("encryptionConfiguration", {})
            if encryption_configuration:
                kmsKey = encryption_configuration.get("kmsKey", None)
                if kmsKey:
                    type = self.kms_instance.aws_kms_key(kmsKey, ftstack)
                    if type == "MANAGED":
                        kms_key_alias = self.get_kms_alias(kmsKey)
                        if kms_key_alias:
                            if resource_type not in self.hcl.additional_data:
                                self.hcl.additional_data[resource_type] = {}
                            if id not in self.hcl.additional_data[resource_type]:
                                self.hcl.additional_data[resource_type][id] = {
                                }
                            self.hcl.additional_data[resource_type][id]["kms_key_alias"] = kms_key_alias

            self.hcl.add_stack(resource_type, id, ftstack)

            self.aws_ecr_repository_policy(repository_name)
            self.aws_ecr_lifecycle_policy(repository_name)

            if "gov" not in self.provider_instance.region:
                # Call to the aws_ecr_registry_scanning_configuration function
                self.aws_ecr_registry_scanning_configuration(repo)

    def aws_ecr_repository_policy(self, repository_name):
        logger.debug(
            f"Processing ECR Repository Policy for: {repository_name}")

        try:
            policy = self.provider_instance.aws_clients.ecr_client.get_repository_policy(
                repositoryName=repository_name)
        except self.provider_instance.aws_clients.ecr_client.exceptions.RepositoryPolicyNotFoundException:
            return

        policy_text = json.loads(policy["policyText"])

        attributes = {
            "id": repository_name,
            "policy": json.dumps(policy_text, indent=2),
        }
        self.hcl.process_resource(
            "aws_ecr_repository_policy", f"{repository_name}_policy".replace("-", "_"), attributes)

    def aws_ecr_lifecycle_policy(self, repository_name):
        logger.debug(f"Processing ECR Lifecycle Policy for: {repository_name}")

        try:
            lifecycle_policy = self.provider_instance.aws_clients.ecr_client.get_lifecycle_policy(repositoryName=repository_name)[
                "lifecyclePolicyText"]
        except self.provider_instance.aws_clients.ecr_client.exceptions.LifecyclePolicyNotFoundException:
            return

        logger.debug(
            f"Processing ECR Lifecycle Policy for repository: {repository_name}")

        attributes = {
            "id": repository_name,
            "policy": json.dumps(json.loads(lifecycle_policy), indent=2),
        }
        self.hcl.process_resource(
            "aws_ecr_lifecycle_policy", repository_name.replace("-", "_"), attributes)

    def aws_ecr_registry_policy(self):
        logger.debug(f"Processing ECR Registry Policies...")
        resource_type = "aws_ecr_registry_policy"

        try:
            registry_policy = self.provider_instance.aws_clients.ecr_client.get_registry_policy()
            if "registryPolicyText" not in registry_policy:
                return
            registry_policy = registry_policy["registryPolicyText"]
        except self.provider_instance.aws_clients.ecr_client.exceptions.RegistryPolicyNotFoundException:
            return

        logger.debug(f"Processing ECR Registry Policy")
        id = self.provider_instance.aws_clients.ecr_client.describe_registries()[
            "registries"][0]["registryId"],

        attributes = {
            "policy": json.dumps(json.loads(registry_policy), indent=2),
        }
        self.hcl.process_resource(
            resource_type, "ecr_registry_policy", attributes)

        ftstack = "ecr"
        self.hcl.add_stack(resource_type, id, ftstack)

    def aws_ecr_pull_through_cache_rule(self):
        logger.debug(f"Processing ECR Pull Through Cache Rules...")
        resource_type = "aws_ecr_pull_through_cache_rule"

        repositories = self.provider_instance.aws_clients.ecr_client.describe_repositories()[
            "repositories"]
        for repo in repositories:
            repository_name = repo["repositoryName"]
            try:
                cache_settings = self.provider_instance.aws_clients.ecr_client.get_registry_policy()
                if "registryPolicyText" not in cache_settings:
                    continue
                cache_settings = cache_settings["registryPolicyText"]
                cache_settings_data = json.loads(cache_settings)
            except self.provider_instance.aws_clients.ecr_client.exceptions.RegistryPolicyNotFoundException:
                continue

            for rule in cache_settings_data.get("rules", []):
                if rule["repositoryName"] == repository_name:
                    logger.debug(
                        f"Processing ECR Pull Through Cache Rule for repository: {repository_name}")
                    id = repository_name
                    attributes = {
                        "id": id,
                        "action": rule["action"],
                        "rule_priority": rule["rulePriority"],
                    }
                    self.hcl.process_resource(
                        resource_type, id, attributes)
                    ftstack = "ecr"
                    self.hcl.add_stack(resource_type, id, ftstack)

    def aws_ecr_registry_scanning_configuration(self, repo):
        repository_name = repo["repositoryName"]
        image_scanning_config = repo["imageScanningConfiguration"]

        logger.debug(
            f"Processing ECR Registry Scanning Configuration for repository: {repository_name}")

        attributes = {
            "id": repository_name,
            "scan_on_push": image_scanning_config["scanOnPush"],
        }
        self.hcl.process_resource(
            "aws_ecr_registry_scanning_configuration", repository_name.replace("-", "_"), attributes)

    def aws_ecr_replication_configuration(self):
        logger.debug(f"Processing ECR Replication Configurations...")
        resource_type = "aws_ecr_replication_configuration"

        try:
            registry = self.provider_instance.aws_clients.ecr_client.describe_registry()
            registryId = registry["registryId"]
            replication_configuration = registry["replicationConfiguration"]
        except KeyError:
            return

        rules = replication_configuration["rules"]

        # Skip the resource if the rules are empty
        if len(rules) == 0:
            logger.debug(
                f"  No rules for ECR Replication Configuration. Skipping...")
            return

        logger.debug(f"Processing ECR Replication Configuration")

        # formatted_rules = []
        # for rule in rules:
        #     formatted_rules.append({
        #         "destination": {
        #             "region": rule["destination"]["region"],
        #             "registry_id": rule["destination"]["registryId"]
        #         }
        #     })

        attributes = {
            "id": registryId,
            # "rule": formatted_rules,
        }
        self.hcl.process_resource(
            resource_type, registryId, attributes)

        ftstack = "ecr"
        self.hcl.add_stack(resource_type, registryId, ftstack)
