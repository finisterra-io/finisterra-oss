from ...utils.hcl import HCL
from ...providers.aws.s3 import S3
from ...providers.aws.logs import Logs
from botocore.exceptions import ClientError
import logging
import inspect

logger = logging.getLogger('finisterra')


class Wafv2:
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

        self.s3_instance = S3(self.provider_instance, self.hcl)
        self.logs_instance = Logs(self.provider_instance, self.hcl)

    def wafv2(self):
        self.hcl.prepare_folder()

        self.aws_wafv2_web_acl()
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

    def aws_wafv7_ip_set(self):
        # Find IP sets for the ACL
        for scope in ['REGIONAL', 'CLOUDFRONT']:
            try:
                # Moving the client call inside the try block to ensure we handle any client errors, including valid issues
                ip_sets = self.provider_instance.aws_clients.wafv2_client.list_ip_sets(Scope=scope)[
                    "IPSets"]
            except ClientError as e:
                logger.error(f"Error fetching IP Sets for scope {scope}: {e}")
                continue  # This will make sure we skip to the next loop in case of an issue with the scope or another error

            for ip_set in ip_sets:
                ip_set_name = ip_set["Name"]
                # Assuming the immediate goal is to process configurations, and we don't need an extra logic to reconcile IDs
                ip_set_id = ip_set['Id']
                logger.debug(f"Processing WAFv2 IP Set: {ip_set_name}")

                id = f"{ip_set_id}/{ip_set_name}/{scope}"

                attributes = {
                    "id": id,
                    "name": ip_set_name,
                    "scope": scope,
                }
                self.hcl.process_resource(
                    "aws_wafv2_ip_set", ip_set_name, attributes)

    # def aws_wafv2_regex_pattern_set(self):
    #     logger.debug("Processing WAFv2 Regex Pattern Sets...")

    #     scope = 'REGIONAL'
    #     regex_pattern_sets = self.provider_instance.aws_clients.wafv2_client.list_regex_pattern_sets(Scope=scope)[
    #         "RegexPatternSets"]

    #     for regex_pattern_set in regex_pattern_sets:
    #         regex_pattern_set_id = regex_pattern_set["Id"]
    #         logger.debug(
    #             f"Processing WAFv2 Regex Pattern Set: {regex_pattern_set_id}")

    #         regex_pattern_set_info = self.provider_instance.aws_clients.wafv2_client.get_regex_pattern_set(
    #             Id=regex_pattern_set_id, Scope=scope)["RegexPatternSet"]
    #         attributes = {
    #             "id": regex_pattern_set_id,
    #             "name": regex_pattern_set_info["Name"],
    #             "description": regex_pattern_set_info.get("Description", ""),
    #             "scope": scope,
    #         }
    #         self.hcl.process_resource(
    #             "aws_wafv2_regex_pattern_set", regex_pattern_set_id.replace("-", "_"), attributes)

    def aws_wafv2_rule_group(self, rule_group_arn):
        scope = rule_group_arn.split(":")[5]
        rule_group_id = rule_group_arn.split("/")[-1]
        logger.debug(f"Processing WAFv2 Rule Group: {rule_group_id}")

        rule_group_info = self.provider_instance.aws_clients.wafv2_client.get_rule_group(
            Id=rule_group_id, Scope=scope)["RuleGroup"]
        rule_group_name = rule_group_info["Name"]
        id = rule_group_id + "/" + rule_group_name + "/" + scope
        attributes = {
            "id": id,
            "name": rule_group_name,
            "scope": scope,
        }
        self.hcl.process_resource(
            "aws_wafv2_rule_group", rule_group_name, attributes)

    def aws_wafv2_web_acl(self, web_acl_id=None, ftstack=None):
        logger.debug("Processing WAFv2 Web ACLs...")

        total = 0
        for scope in ['REGIONAL', 'CLOUDFRONT']:
            try:
                web_acls = self.provider_instance.aws_clients.wafv2_client.list_web_acls(Scope=scope)[
                    "WebACLs"]
                total += len(web_acls)
            except ClientError as e:
                logger.error(
                    f"An error occurred while listing WebACLs for scope {scope}: {e}")
                continue  # Skip this scope and continue with the next one

        if total > 0 and not web_acl_id:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)

        # iterate through both scopes
        for scope in ['REGIONAL', 'CLOUDFRONT']:
            try:
                web_acls = self.provider_instance.aws_clients.wafv2_client.list_web_acls(Scope=scope)[
                    "WebACLs"]
            except ClientError as e:
                logger.error(
                    f"An error occurred while listing WebACLs for scope {scope}: {e}")
                continue  # Skip this scope and continue with the next one

            for web_acl in web_acls:
                if web_acl_id and web_acl["Id"] != web_acl_id:
                    continue
                self.process_single_wafv2_web_acl(web_acl, scope, ftstack)
                if not web_acl_id:
                    self.provider_instance.progress.update(
                        self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{web_acl['Name']}[/]")

    def process_single_wafv2_web_acl(self, web_acl, scope, ftstack=None):
        resource_type = "aws_wafv2_web_acl"
        web_acl_name = web_acl["Name"]

        web_acl_id = web_acl["Id"]

        # if web_acl_name != "xxxxx":
        #     return

        logger.debug(f"Processing WAFv2 Web ACL: {web_acl_id}")

        web_acl_info = self.provider_instance.aws_clients.wafv2_client.get_web_acl(
            Id=web_acl_id, Name=web_acl_name, Scope=scope)["WebACL"]

        if not ftstack:
            ftstack = "wafv2"
            # Find tags for the ACL
            tags_response = self.provider_instance.aws_clients.wafv2_client.list_tags_for_resource(
                ResourceARN=web_acl_info["ARN"])
            if "TagInfoForResource" in tags_response:
                for tag in tags_response["TagInfoForResource"].get("TagList", []):
                    if tag["Key"] == "ftstack":
                        ftstack = tag["Value"]
                        break

        id = web_acl_id
        attributes = {
            "id": web_acl_id,
            "name": web_acl_info["Name"],
            "description": web_acl_info.get("Description", ""),
            "scope": scope,
        }
        self.hcl.process_resource(
            resource_type, id, attributes)
        self.hcl.add_stack(resource_type, id, ftstack)

        # call the other functions with appropriate arguments
        # self.aws_wafv2_web_acl_association(web_acl_id)
        self.aws_wafv2_web_acl_logging_configuration(
            web_acl_id, web_acl_info["ARN"], ftstack)

    def aws_wafv2_web_acl_association(self, web_acl_id):
        logger.debug("Processing WAFv2 Web ACL Associations...")

        # Iterate over Application Load Balancers (ALBs)
        alb_paginator = self.provider_instance.aws_clients.elbv2_client.get_paginator(
            'describe_load_balancers')
        alb_iterator = alb_paginator.paginate()

        for alb_page in alb_iterator:
            for alb in alb_page['LoadBalancers']:
                resource_arn = alb['LoadBalancerArn']
                try:
                    association = self.provider_instance.aws_clients.wafv2_client.get_web_acl_for_resource(
                        ResourceArn=resource_arn
                    )
                    if 'WebACL' in association and association['WebACL']['Id'] == web_acl_id:
                        association_id = f"{web_acl_id},{resource_arn}"
                        logger.debug(
                            f"Processing WAFv2 Web ACL Association: {association_id}")

                        attributes = {
                            "id": association_id,
                            "web_acl_id": web_acl_id,
                            "resource_arn": resource_arn,
                        }
                        self.hcl.process_resource(
                            "aws_wafv2_web_acl_association", association_id.replace("-", "_"), attributes)
                except Exception as e:
                    if e.response['Error']['Code'] == 'WAFNonexistentItemException':
                        pass
                    else:
                        raise e

    def aws_wafv2_web_acl_logging_configuration(self, web_acl_id, web_acl_arn, ftstack):
        logger.debug("Processing WAFv2 Web ACL Logging Configurations...")

        try:
            logging_config = self.provider_instance.aws_clients.wafv2_client.get_logging_configuration(ResourceArn=web_acl_arn)[
                "LoggingConfiguration"]
            log_destination_configs = logging_config.get(
                "LogDestinationConfigs", [])

            for index, log_destination_config in enumerate(log_destination_configs):
                config_id = f"{web_acl_id}-{index}"
                logger.debug(
                    f"Processing WAFv2 Web ACL Logging Configuration: {config_id}")

                if "arn:aws:s3" in log_destination_config:
                    bucket_name = log_destination_config.split(":")[-1]
                    self.s3_instance.aws_s3_bucket(bucket_name, ftstack)

                if "arn:aws:logs" in log_destination_config:
                    log_group = log_destination_config.split(":")[-1]
                    if log_group:
                        self.logs_instance.aws_cloudwatch_log_group(
                            log_group, ftstack)

                attributes = {
                    "id": web_acl_arn,
                }
                self.hcl.process_resource(
                    "aws_wafv2_web_acl_logging_configuration", config_id.replace("-", "_"), attributes)
        except self.provider_instance.aws_clients.wafv2_client.exceptions.WAFNonexistentItemException:
            logger.debug(
                f"  No logging configuration found for Web ACL: {web_acl_id}")
