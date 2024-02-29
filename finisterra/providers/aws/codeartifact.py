from ...utils.hcl import HCL
import botocore
from ...providers.aws.kms import KMS
import logging
import inspect

logger = logging.getLogger('finisterra')


class CodeArtifact:
    def __init__(self, progress, aws_clients, script_dir, provider_name, provider_name_short,
                 provider_source, provider_version, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id, output_dir, account_name, hcl=None):
        self.progress = progress

        self.aws_clients = aws_clients
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.aws_account_id = aws_account_id

        self.workspace_id = workspace_id
        self.modules = modules
        if not hcl:
            self.hcl = HCL(self.schema_data)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.output_dir = output_dir
        self.hcl.account_id = aws_account_id

        self.hcl.provider_name = provider_name
        self.hcl.provider_name_short = provider_name_short
        self.hcl.provider_source = provider_source
        self.hcl.provider_version = provider_version
        self.hcl.account_name = account_name

        self.kms_instance = KMS(self.progress,  self.aws_clients, script_dir, provider_name, provider_name_short, provider_source, provider_version, schema_data, region,
                                s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, output_dir, account_name, self.hcl)

    def code_artifact_get_kms_alias(self, kms_key_id):
        if kms_key_id:
            try:
                value = ""
                response = self.aws_clients.kms_client.list_aliases()
                aliases = response.get('Aliases', [])
                while 'NextMarker' in response:
                    response = self.aws_clients.kms_client.list_aliases(
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
        return ""

    def codeartifact(self):
        self.hcl.prepare_folder()
        self.aws_codeartifact_domain()
        self.hcl.module = inspect.currentframe().f_code.co_name
        if self.hcl.count_state():
            self.progress.update(
                self.task, description=f"[cyan]{self.__class__.__name__} [bold]Refreshing state[/]", total=self.progress.tasks[self.task].total+1)
            self.hcl.refresh_state()
            if self.hcl.request_tf_code():
                self.progress.update(
                    self.task, advance=1, description=f"[green]{self.__class__.__name__} [bold]Code Generated[/]")
            else:
                self.progress.update(
                    self.task, advance=1, description=f"[orange3]{self.__class__.__name__} [bold]No code generated[/]")
        else:
            self.task = self.progress.add_task(
                f"[orange3]{self.__class__.__name__} [bold]No resources found[/]", total=1)
            self.progress.update(self.task, advance=1)

    def aws_codeartifact_domain(self, domain_name=None, ftstack=None):
        # logger.debug(f"Processing CodeArtifact Domains")

        if domain_name:
            self.process_single_codeartifact_domain(domain_name, ftstack)
            return

        paginator = self.aws_clients.codeartifact_client.get_paginator(
            'list_domains')
        total = 0
        for response in paginator.paginate():
            total += len(response["domains"])
        if total > 0:
            self.task = self.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for response in paginator.paginate():
            for domain in response["domains"]:
                domain_name = domain["name"]
                domain_arn = domain["arn"]
                self.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{domain_name}[/]")
                self.process_single_codeartifact_domain(domain_name, ftstack)

                try:
                    policy = self.aws_clients.codeartifact_client.get_domain_permissions_policy(
                        domain=domain_name)
                    if policy["policy"]:
                        document = policy["policy"]["document"]
                        self.aws_codeartifact_domain_permissions_policy(
                            domain_arn)
                except botocore.exceptions.ClientError as error:
                    # Ignore ResourceNotFoundException and continue
                    pass

    def process_single_codeartifact_domain(self, domain_name, ftstack=None):
        resource_type = "aws_codeartifact_domain"
        domain_info = self.aws_clients.codeartifact_client.describe_domain(
            domain=domain_name)
        domain_arn = domain_info["domain"]["arn"]
        logger.debug(f"Processing CodeArtifact Domain: {domain_name}")

        id = domain_arn
        attributes = {
            "id": id,
        }

        if not ftstack:
            ftstack = "codeartifact"
            # Retrieve and process domain tags if they exist
            domain_tags = self.aws_clients.codeartifact_client.list_tags_for_resource(
                resourceArn=domain_arn)
            for tag in domain_tags.get('Tags', []):
                if tag["Key"] == "ftstack":
                    ftstack = tag["Value"]
                    break

        self.hcl.process_resource(resource_type, id, attributes)
        self.hcl.add_stack(resource_type, id, ftstack)

        kms_key_id = domain_info["domain"].get("encryptionKey")
        if kms_key_id:
            type = self.kms_instance.aws_kms_key(kms_key_id, ftstack)
            if type == "MANAGED":
                alias = self.code_artifact_get_kms_alias(kms_key_id)
                if alias:
                    if 'codeartifact' not in self.hcl.additional_data:
                        self.hcl.additional_data["codeartifact"] = {}
                    if id not in self.hcl.additional_data["codeartifact"]:
                        self.hcl.additional_data["codeartifact"] = {}
                    self.hcl.additional_data["codeartifact"][id] = {
                        "kms_key_alias": alias}

        # Process repositories in the specified domain
        repositories = self.aws_clients.codeartifact_client.list_repositories_in_domain(
            domain=domain_name)
        for repository in repositories["repositories"]:
            repository_name = repository["name"]
            repository_arn = repository["arn"]
            self.aws_codeartifact_repository(
                domain_name, repository_arn, repository_name)

    def aws_codeartifact_repository(self, domain_name, repository_arn, repository_name):
        resource_type = "aws_codeartifact_repository"
        logger.debug(f"Processing CodeArtifact Repository: {repository_arn}")

        id = repository_arn
        attributes = {
            "id": id,
        }

        self.hcl.process_resource(
            resource_type, id, attributes)

        try:
            policy = self.aws_clients.codeartifact_client.get_repository_permissions_policy(
                domain=domain_name, repository=repository_name)
            if policy["policy"]:
                self.aws_codeartifact_repository_permissions_policy(
                    repository_arn)
        except botocore.exceptions.ClientError as error:
            # Ignore ResourceNotFoundException and continue
            pass

    def aws_codeartifact_repository_permissions_policy(self, repository_arn):
        logger.debug(
            f"Processing CodeArtifact Repository Permissions Policy {repository_arn}")
        resource_type = "aws_codeartifact_repository_permissions_policy"
        id = repository_arn
        attributes = {
            "id": id,
        }
        self.hcl.process_resource(resource_type, id, attributes)

    def aws_codeartifact_domain_permissions_policy(self, domain_name_arn):
        logger.debug(
            f"Processing CodeArtifact Domain Permissions Policy {domain_name_arn}")
        resource_type = "aws_codeartifact_domain_permissions_policy"
        id = domain_name_arn
        attributes = {
            "id": id,
        }
        self.hcl.process_resource(resource_type, id, attributes)
