import os
from utils.hcl import HCL
from providers.aws.s3 import S3
from providers.aws.logs import Logs

class Wafv2:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
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
            self.hcl = HCL(self.schema_data, self.provider_name)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.account_id = aws_account_id

        self.s3_instance = S3(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.logs_instance = Logs(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)

        

    def wafv2(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_wafv2_web_acl()

        self.hcl.refresh_state()

        self.hcl.request_tf_code()


    def aws_wafv2_ip_set(self, waf_id, ip_set_name, scope):
        print(f"Processing WAFv2 IP Set:  {ip_set_name}")

        attributes = {
            "id": waf_id,
            "name": ip_set_name,
            "scope": scope,
        }
        self.hcl.process_resource(
            "aws_wafv2_ip_set", waf_id.replace("-", "_"), attributes)


    # def aws_wafv2_regex_pattern_set(self):
    #     print("Processing WAFv2 Regex Pattern Sets...")

    #     scope = 'REGIONAL'
    #     regex_pattern_sets = self.aws_clients.wafv2_client.list_regex_pattern_sets(Scope=scope)[
    #         "RegexPatternSets"]

    #     for regex_pattern_set in regex_pattern_sets:
    #         regex_pattern_set_id = regex_pattern_set["Id"]
    #         print(
    #             f"Processing WAFv2 Regex Pattern Set: {regex_pattern_set_id}")

    #         regex_pattern_set_info = self.aws_clients.wafv2_client.get_regex_pattern_set(
    #             Id=regex_pattern_set_id, Scope=scope)["RegexPatternSet"]
    #         attributes = {
    #             "id": regex_pattern_set_id,
    #             "name": regex_pattern_set_info["Name"],
    #             "description": regex_pattern_set_info.get("Description", ""),
    #             "scope": scope,
    #         }
    #         self.hcl.process_resource(
    #             "aws_wafv2_regex_pattern_set", regex_pattern_set_id.replace("-", "_"), attributes)

    # def aws_wafv2_rule_group(self):
    #     print("Processing WAFv2 Rule Groups...")

    #     scope = 'REGIONAL'
    #     rule_groups = self.aws_clients.wafv2_client.list_rule_groups(Scope=scope)[
    #         "RuleGroups"]

    #     for rule_group in rule_groups:
    #         rule_group_id = rule_group["Id"]
    #         print(f"Processing WAFv2 Rule Group: {rule_group_id}")

    #         rule_group_info = self.aws_clients.wafv2_client.get_rule_group(
    #             Id=rule_group_id, Scope=scope)["RuleGroup"]
    #         attributes = {
    #             "id": rule_group_id,
    #             "name": rule_group_info["Name"],
    #             "description": rule_group_info.get("Description", ""),
    #             "scope": scope,
    #         }
    #         self.hcl.process_resource(
    #             "aws_wafv2_rule_group", rule_group_id.replace("-", "_"), attributes)

    def aws_wafv2_web_acl(self, web_acl_id=None, ftstack=None):
        resource_type = "aws_wafv2_web_acl"
        print("Processing WAFv2 Web ACLs...")

        # iterate through both scopes
        for scope in ['REGIONAL', 'CLOUDFRONT']:
            web_acls = self.aws_clients.wafv2_client.list_web_acls(Scope=scope)["WebACLs"]

            for web_acl in web_acls:
                if web_acl_id and web_acl["Id"] != web_acl_id:
                    continue

                web_acl_id = web_acl["Id"]
                web_acl_name = web_acl["Name"]

                # if web_acl_name != "aws-managed-waf-sandbox":
                #     continue

                print(f"Processing WAFv2 Web ACL: {web_acl_id}")

                web_acl_info = self.aws_clients.wafv2_client.get_web_acl(
                    Id=web_acl_id, Name=web_acl_name, Scope=scope)["WebACL"]

                if not ftstack:
                    ftstack = "wafv2"
                    # Find tags for the ACL
                    tags_response = self.aws_clients.wafv2_client.list_tags_for_resource(
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

                # Find IP sets for the ACL
                ip_sets = self.aws_clients.wafv2_client.list_ip_sets(Scope=scope)["IPSets"]
                for ip_set in ip_sets:
                    ip_set_name = ip_set["Name"]
                    self.aws_wafv2_ip_set(web_acl_id, ip_set_name, scope)

                # call the other functions with appropriate arguments
                # self.aws_wafv2_web_acl_association(web_acl_id)
                self.aws_wafv2_web_acl_logging_configuration(
                    web_acl_id, web_acl_info["ARN"], ftstack)

    def aws_wafv2_web_acl_association(self, web_acl_id):
        print("Processing WAFv2 Web ACL Associations...")

        # Iterate over Application Load Balancers (ALBs)
        alb_paginator = self.aws_clients.elbv2_client.get_paginator(
            'describe_load_balancers')
        alb_iterator = alb_paginator.paginate()

        for alb_page in alb_iterator:
            for alb in alb_page['LoadBalancers']:
                resource_arn = alb['LoadBalancerArn']
                try:
                    association = self.aws_clients.wafv2_client.get_web_acl_for_resource(
                        ResourceArn=resource_arn
                    )
                    if 'WebACL' in association and association['WebACL']['Id'] == web_acl_id:
                        association_id = f"{web_acl_id},{resource_arn}"
                        print(
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
        print("Processing WAFv2 Web ACL Logging Configurations...")

        try:
            logging_config = self.aws_clients.wafv2_client.get_logging_configuration(ResourceArn=web_acl_arn)[
                "LoggingConfiguration"]
            log_destination_configs = logging_config.get("LogDestinationConfigs", [])

            for index, log_destination_config in enumerate(log_destination_configs):
                config_id = f"{web_acl_id}-{index}"
                print(
                    f"Processing WAFv2 Web ACL Logging Configuration: {config_id}")

                if "arn:aws:s3" in log_destination_config:
                    bucket_name = log_destination_config.split(":")[-1]
                    self.s3_instance.aws_s3_bucket(bucket_name, ftstack)

                if "arn:aws:logs" in log_destination_config:
                    log_group = log_destination_config.split(":")[-1]
                    if log_group:
                        self.logs_instance.aws_cloudwatch_log_group(log_group, ftstack)

                attributes = {
                    "id": web_acl_arn,
                }
                self.hcl.process_resource(
                    "aws_wafv2_web_acl_logging_configuration", config_id.replace("-", "_"), attributes)
        except self.aws_clients.wafv2_client.exceptions.WAFNonexistentItemException:
            print(
                f"  No logging configuration found for Web ACL: {web_acl_id}")
