import botocore
import os
from utils.hcl import HCL
import copy
from providers.aws.acm import ACM
from providers.aws.s3 import S3
from providers.aws.aws_lambda import AwsLambda
from providers.aws.wafv2 import Wafv2


def cors_config_transform(value):
    return "{items="+str(value)+"}\n"

class CloudFront:
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

        
        
        self.aws_account_id = aws_account_id
        self.origin = {}


        self.acm_instance = ACM(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.s3_instance = S3(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.aws_lambda_instance = AwsLambda(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.wafv2_instance = Wafv2(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)

    def get_managed_cache_policies(self):
        managed_cache_policies = self.aws_clients.cloudfront_client.list_cache_policies(
            Type="managed",
            MaxItems="100"
        ).get("CachePolicyList", [])
        result = {}
        for policy in managed_cache_policies['Items']:
            if policy['Type'] != 'managed':
                continue
            result[policy["CachePolicy"]["Id"]]= policy["CachePolicy"]["CachePolicyConfig"]["Name"]
        return result

    def cloudfront(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        if "gov" not in self.region:
            self.aws_cloudfront_distribution()

        self.hcl.refresh_state()

        managed_policies = self.get_managed_cache_policies()
        if managed_policies:
            if "aws_cloudfront_distribution" not in self.hcl.additional_data:
                self.hcl.additional_data["aws_cloudfront_distribution"] = {}
            self.hcl.additional_data["aws_cloudfront_distribution"]["managed_policies"] = managed_policies

        self.hcl.id_key_list.append("cloudfront_access_identity_path")
        self.hcl.id_key_list.append("bucket_domain_name")
        self.hcl.id_key_list.append("qualified_arn")
        self.hcl.request_tf_code()


    def aws_cloudfront_distribution(self):
        resource_type = "aws_cloudfront_distribution"
        print("Processing CloudFront Distributions...")

        paginator = self.aws_clients.cloudfront_client.get_paginator("list_distributions")
        for page in paginator.paginate():
            distribution_list = page.get("DistributionList")
            if not distribution_list:
                print("No DistributionList in page")
                continue

            items = distribution_list.get("Items")
            if not items:
                print("No Items in DistributionList")
                continue

            for distribution_summary in items:
                distribution_id = distribution_summary["Id"]

                # if distribution_id != "E31WQ2W96RYYTV":
                #     continue

                print(f"Processing CloudFront Distribution: {distribution_id}")

                ftstack = "cloudfront"
                try:
                    response = self.aws_clients.cloudfront_client.list_tags_for_resource(Resource=distribution_summary["ARN"])
                    tags = response.get('Tags', {}).get('Items', [])
                    for tag in tags:
                        if tag['Key'] == 'ftstack':
                            if tag['Value'] != 'cloudfront':
                                ftstack = "stack_"+tag['Value']
                            break
                except Exception as e:
                    print("Error occurred: ", e)
                            
                id = distribution_id

                attributes = {
                    "id": id,
                    "arn": distribution_summary["ARN"],
                    "domain_name": distribution_summary["DomainName"],
                }

                self.hcl.process_resource(
                    resource_type, distribution_id.replace("-", "_"), attributes)
                
                self.hcl.add_stack(resource_type, id, ftstack)

                # Fetch distribution configuration
                try:
                    dist_config_response = self.aws_clients.cloudfront_client.get_distribution_config(Id=distribution_id)
                     
                    dist_config = dist_config_response.get('DistributionConfig', {})

                    viewer_certificate = dist_config.get('ViewerCertificate', {})

                    if viewer_certificate:
                        ACMCertificateArn = viewer_certificate.get('ACMCertificateArn')
                        if ACMCertificateArn:
                            self.acm_instance.aws_acm_certificate(ACMCertificateArn, ftstack)

                    logger_config = dist_config.get('Logging', {})
                    if logger_config:
                        bucket = logger_config.get('Bucket')
                        if bucket:
                            # get the bucket name from the bucket domain
                            bucket = bucket.split('.')[0]
                            self.s3_instance.aws_s3_bucket(bucket, ftstack)

                    # Process cache behaviors and associated policies
                    all_behaviors = dist_config.get('CacheBehaviors', {}).get('Items', [])
                    all_behaviors.append(dist_config.get('DefaultCacheBehavior'))  # Include default cache behavior

                    for behavior in all_behaviors:
                        if behavior:
                            cache_policy_id = behavior.get('CachePolicyId')
                            if cache_policy_id:
                                self.aws_cloudfront_cache_policy(cache_policy_id)
                                self.hcl.add_stack("aws_cloudfront_cache_policy", cache_policy_id, ftstack)

                            response_headers_policy_id = behavior.get('ResponseHeadersPolicyId')
                            if response_headers_policy_id:
                                self.aws_cloudfront_response_headers_policy(response_headers_policy_id)
                                self.hcl.add_stack("aws_cloudfront_response_headers_policy", response_headers_policy_id, ftstack)

                            origin_request_policy_id = behavior.get('OriginRequestPolicyId')
                            if origin_request_policy_id:
                                self.aws_cloudfront_origin_request_policy(origin_request_policy_id)
                                self.hcl.add_stack("aws_cloudfront_origin_request_policy", origin_request_policy_id, ftstack)

                            lambda_function_associations = behavior.get('LambdaFunctionAssociations', {})
                            if lambda_function_associations:
                                for lambda_function_association in lambda_function_associations.get('Items', []):
                                    lambda_arn = lambda_function_association.get('LambdaFunctionARN')
                                    if lambda_arn:
                                        lambda_name = lambda_arn.split(":function:")[1].split(":")[0]
                                        self.aws_lambda_instance.aws_lambda_function(lambda_name, ftstack)

                            function_association = behavior.get('FunctionAssociations', {})
                            if function_association:
                                for function_association in function_association.get('Items', []):
                                    function_arn = function_association.get('FunctionARN')
                                    if function_arn:
                                        self.aws_cloudfront_function(function_arn, ftstack)

                  # Check if ACL ID is associated with the CloudFront distribution
                    acl_arn = dist_config.get('WebACLId')
                    if acl_arn:
                        acl_id = acl_arn.split("/")[-1]
                        print(acl_id)
                        self.wafv2_instance.aws_wafv2_web_acl(acl_id, ftstack)
                                        
                except Exception as e:
                    print(f"Error occurred while processing distribution {distribution_id}: {e}")
                    continue

                # Retrieve identity_id
                origins = distribution_summary.get("Origins", {}).get("Items", [])
                for origin in origins:
                    s3_origin_config = origin.get("S3OriginConfig")
                    if s3_origin_config:
                        identity_id = s3_origin_config.get("OriginAccessIdentity")
                        if identity_id:
                            # Call aws_cloudfront_origin_access_identity function filtered by the identity_id
                            identity_id = identity_id.split("/")[-1]
                            self.aws_cloudfront_origin_access_identity(identity_id)
                            self.hcl.add_stack("aws_cloudfront_origin_access_identity", identity_id, ftstack)

                self.aws_cloudfront_monitoring_subscription(distribution_id)

    def aws_cloudfront_cache_policy(self, specific_cache_policy_id):
        print("Processing CloudFront Cache Policies...")

        response = self.aws_clients.cloudfront_client.list_cache_policies(Type="custom")
        if "CachePolicyList" in response and "Items" in response["CachePolicyList"]:
            for cache_policy_summary in response["CachePolicyList"]["Items"]:
                cache_policy = cache_policy_summary["CachePolicy"]
                cache_policy_id = cache_policy["Id"]

                # Process only the specified cache policy
                if cache_policy_id != specific_cache_policy_id:
                    continue

                print(f"Processing CloudFront Cache Policy: {cache_policy_id}")

                attributes = {
                    "id": cache_policy_id,
                    "name": cache_policy["CachePolicyConfig"]["Name"],
                }

                self.hcl.process_resource(
                    "aws_cloudfront_cache_policy", cache_policy_id.replace("-", "_"), attributes)


    def aws_cloudfront_field_level_encryption_config(self):
        print("Processing CloudFront Field-Level Encryption Configs...")

        response = self.aws_clients.cloudfront_client.list_field_level_encryption_configs()
        if "FieldLevelEncryptionList" in response and "Items" in response["FieldLevelEncryptionList"]:
            for config_summary in response["FieldLevelEncryptionList"]["Items"]:
                config_id = config_summary["Id"]
                print(
                    f"Processing CloudFront Field-Level Encryption Config: {config_id}")

                attributes = {
                    "id": config_id,
                }

                self.hcl.process_resource(
                    "aws_cloudfront_field_level_encryption_config", config_id.replace("-", "_"), attributes)

    def aws_cloudfront_field_level_encryption_profile(self):
        print("Processing CloudFront Field-Level Encryption Profiles...")

        response = self.aws_clients.cloudfront_client.list_field_level_encryption_profiles()
        if "FieldLevelEncryptionProfileList" in response and "Items" in response["FieldLevelEncryptionProfileList"]:
            for profile_summary in response["FieldLevelEncryptionProfileList"]["Items"]:
                profile_id = profile_summary["Id"]
                print(
                    f"Processing CloudFront Field-Level Encryption Profile: {profile_id}")

                attributes = {
                    "id": profile_id,
                }

                self.hcl.process_resource(
                    "aws_cloudfront_field_level_encryption_profile", profile_id.replace("-", "_"), attributes)

    def aws_cloudfront_function(self, function_arn, ftstack):
        resource_type = "aws_cloudfront_function"
        print("Processing CloudFront Functions...")

        # List all functions and find the one that matches the provided ARN
        response = self.aws_clients.cloudfront_client.list_functions()
        if "FunctionList" in response:
            for function_summary in response["FunctionList"]["Items"]:
                current_function_arn = function_summary["FunctionMetadata"]["FunctionARN"]
                if current_function_arn == function_arn:
                    function_name = function_summary["Name"]

                    # Fetch the function's code or details using its name
                    print(f"Processing CloudFront Function: {function_name}")
                    id = function_name

                    attributes = {
                        "id": id,
                        # Add other attributes as needed
                    }

                    self.hcl.process_resource(
                        resource_type, id, attributes)
                    self.hcl.add_stack(resource_type, id, ftstack)
                    return  # Exit after processing the specific function

        print(f"No function found with ARN: {function_arn}")


    def aws_cloudfront_key_group(self, key_group_id):
        print(f"Processing CloudFront Key Group: {key_group_id}")

        response = self.aws_clients.cloudfront_client.get_key_group(Id=key_group_id)
        if "KeyGroup" in response:
            key_group_name = response["KeyGroup"]["KeyGroupName"]

            attributes = {
                "id": key_group_id,
                "name": key_group_name,
            }

            self.hcl.process_resource(
                "aws_cloudfront_key_group", key_group_id.replace("-", "_"), attributes)

    def aws_cloudfront_monitoring_subscription(self, target_distribution_id):
        print("Processing CloudFront Monitoring Subscriptions...")

        paginator = self.aws_clients.cloudfront_client.get_paginator("list_distributions")
        for page in paginator.paginate():
            for distribution_summary in page["DistributionList"]["Items"]:
                distribution_id = distribution_summary["Id"]

                # Skip the distributions that don't match the target_distribution_id
                if distribution_id != target_distribution_id:
                    continue

                distribution_arn = distribution_summary["ARN"]

                try:
                    monitoring_subscription = self.aws_clients.cloudfront_client.get_monitoring_subscription(
                        DistributionId=distribution_id)["MonitoringSubscription"]

                    if monitoring_subscription.get("RealtimeMetricsSubscriptionConfig"):
                        print(
                            f"Processing CloudFront Monitoring Subscription: {distribution_id}")

                        attributes = {
                            "id": distribution_id,
                            "distribution_id": distribution_id,
                            "distribution_arn": distribution_arn,
                        }

                        self.hcl.process_resource(
                            "aws_cloudfront_monitoring_subscription", distribution_id.replace("-", "_"), attributes)
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchMonitoringSubscription':
                        print(
                            f"No monitoring subscription found for distribution: {distribution_id}")
                    else:
                        raise

    def aws_cloudfront_origin_access_identity(self, identity_id):
        print("Processing CloudFront Origin Access Identities...")

        paginator = self.aws_clients.cloudfront_client.get_paginator(
            "list_cloud_front_origin_access_identities")
        for page in paginator.paginate():
            for oai_summary in page["CloudFrontOriginAccessIdentityList"]["Items"]:
                oai_id = oai_summary["Id"]

                # Process only the matching oai_id
                if oai_id != identity_id:
                    continue

                oai_comment = oai_summary["Comment"]
                print(
                    f"Processing CloudFront Origin Access Identity: {oai_id}")

                attributes = {
                    "id": oai_id,
                    "comment": oai_comment,
                }

                self.hcl.process_resource(
                    "aws_cloudfront_origin_access_identity", oai_id.replace("-", "_"), attributes)

    def aws_cloudfront_origin_access_control(self):
        print("Processing CloudFront Origin Access Identities...")

        paginator = self.aws_clients.cloudfront_client.get_paginator(
            "list_origin_access_controls")
        for page in paginator.paginate():
            for oai_summary in page["OriginAccessControlList"]["Items"]:
                oai_id = oai_summary["Id"]
                print(
                    f"Processing CloudFront Origin Access Identity: {oai_id}")

                attributes = {
                    "id": oai_id,
                }

                self.hcl.process_resource(
                    "aws_cloudfront_origin_access_control", oai_id.replace("-", "_"), attributes)

    def aws_cloudfront_origin_request_policy(self, specific_policy_id):
        print("Processing CloudFront Origin Request Policies...")

        # Fetch custom origin request policy IDs
        custom_policy_ids = []
        response = self.aws_clients.cloudfront_client.list_origin_request_policies(Type="custom")
        if "OriginRequestPolicyList" in response and "Items" in response["OriginRequestPolicyList"]:
            for policy in response["OriginRequestPolicyList"]["Items"]:
                custom_policy_ids.append(policy["OriginRequestPolicy"]["Id"])

        # Check if the specific_policy_id is custom
        if specific_policy_id not in custom_policy_ids:
            print(f"Skipping non-custom origin request policy: {specific_policy_id}")
            return

        try:
            policy_response = self.aws_clients.cloudfront_client.get_origin_request_policy(Id=specific_policy_id)
            policy = policy_response["OriginRequestPolicy"]

            print(f"Processing CloudFront Origin Request Policy: {specific_policy_id}")

            attributes = {
                "id": specific_policy_id,
                "name": policy["OriginRequestPolicyConfig"]["Name"],
                "comment": policy["OriginRequestPolicyConfig"].get("Comment", "")
                # Add other required attributes as needed
            }
            self.hcl.process_resource(
                "aws_cloudfront_origin_request_policy", specific_policy_id.replace("-", "_"), attributes)

        except Exception as e:
            print(f"Error occurred while processing origin request policy {specific_policy_id}: {e}")

    def aws_cloudfront_public_key(self):
        print("Processing CloudFront Public Keys...")
        paginator = self.aws_clients.cloudfront_client.get_paginator("list_public_keys")

        for page in paginator.paginate():
            for public_key_summary in page["PublicKeyList"]["Items"]:
                public_key_id = public_key_summary["Id"]
                print(f"Processing CloudFront Public Key: {public_key_id}")

                public_key = self.aws_clients.cloudfront_client.get_public_key(
                    Id=public_key_id)["PublicKey"]
                attributes = {
                    "id": public_key_id,
                    "name": public_key["PublicKeyConfig"]["Name"],
                    "encoded_key": public_key["PublicKeyConfig"]["EncodedKey"],
                    "comment": public_key["PublicKeyConfig"].get("Comment", ""),
                }
                self.hcl.process_resource(
                    "aws_cloudfront_public_key", public_key_id.replace("-", "_"), attributes)

    def aws_cloudfront_public_key(self):
        print("Processing CloudFront Public Keys...")

        response = self.aws_clients.cloudfront_client.list_public_keys()

        for public_key in response.get("PublicKeyList", {}).get("Items", []):
            public_key_id = public_key["Id"]
            print(f"Processing CloudFront Public Key: {public_key_id}")

            attributes = {
                "id": public_key_id,
                "name": public_key["Name"],
                # Add other required attributes as needed
            }

            self.hcl.process_resource(
                "aws_cloudfront_public_key", public_key_id.replace("-", "_"), attributes)

    def aws_cloudfront_realtime_log_config(self):
        print("Processing CloudFront Realtime Log Configs...")

        response = self.aws_clients.cloudfront_client.list_realtime_log_configs()

        if "RealtimeLogConfigs" in response and "Items" in response["RealtimeLogConfigs"]:
            for log_config in response["RealtimeLogConfigs"]["Items"]:
                log_config_id = log_config["ARN"]
                print(
                    f"Processing CloudFront Realtime Log Config: {log_config_id}")

                attributes = {
                    "id": log_config_id,
                    "name": log_config["Name"],
                    "fields": log_config["Fields"],
                    # Add other required attributes as needed
                }

                self.hcl.process_resource(
                    "aws_cloudfront_realtime_log_config", log_config_id.replace("-", "_"), attributes)

    def aws_cloudfront_response_headers_policy(self, specific_policy_id):
        print("Processing CloudFront Response Headers Policies...")

        # Fetch custom response headers policy IDs
        custom_policy_ids = []
        response = self.aws_clients.cloudfront_client.list_response_headers_policies(Type="custom")
        if "ResponseHeadersPolicyList" in response and "Items" in response["ResponseHeadersPolicyList"]:
            for policy in response["ResponseHeadersPolicyList"]["Items"]:
                custom_policy_ids.append(policy["ResponseHeadersPolicy"]["Id"])

        # Check if the specific_policy_id is custom
        if specific_policy_id not in custom_policy_ids:
            print(f"Skipping non-custom response headers policy: {specific_policy_id}")
            return

        try:
            policy_response = self.aws_clients.cloudfront_client.get_response_headers_policy(Id=specific_policy_id)
            policy = policy_response["ResponseHeadersPolicy"]

            print(f"Processing CloudFront Response Headers Policy: {specific_policy_id}")

            attributes = {
                "id": specific_policy_id,
                "name": policy["ResponseHeadersPolicyConfig"]["Name"],
                "comment": policy["ResponseHeadersPolicyConfig"].get("Comment", "")
                # Add other required attributes, like "cors_config", "security_headers_config", etc.
            }
            self.hcl.process_resource(
                "aws_cloudfront_response_headers_policy", specific_policy_id.replace("-", "_"), attributes)

        except Exception as e:
            print(f"Error occurred while processing response headers policy {specific_policy_id}: {e}")

