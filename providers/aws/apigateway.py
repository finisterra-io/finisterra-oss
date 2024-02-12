import os
from utils.hcl import HCL
from providers.aws.vpc_endpoint import VPCEndPoint
from providers.aws.elbv2 import ELBV2
from providers.aws.logs import Logs
from providers.aws.acm import ACM
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress
from rich.progress import TimeElapsedColumn
from rich.progress import SpinnerColumn
from rich.progress import MofNCompleteColumn
from rich.progress import BarColumn
from rich.progress import TextColumn
from rich.progress import TaskProgressColumn


class Apigateway:
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

        
        self.api_gateway_resource_list = {}

        self.vpc_endpoint_instance = VPCEndPoint(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.elbv2_instance = ELBV2(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.logs_instance = Logs(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.acm_instance = ACM(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)


    def apigateway(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_api_gateway_rest_api()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()


    def aws_api_gateway_account(self):
        print("Processing API Gateway Account...")

        account = self.aws_clients.apigateway_client.get_account()

        attributes = {}

        if "cloudwatchRoleArn" in account:
            attributes["cloudwatch_role_arn"] = account["cloudwatchRoleArn"]

        if "throttleSettings" in account:
            if "burstLimit" in account["throttleSettings"]:
                attributes["throttle_settings_burst_limit"] = account["throttleSettings"]["burstLimit"]
            if "rateLimit" in account["throttleSettings"]:
                attributes["throttle_settings_rate_limit"] = account["throttleSettings"]["rateLimit"]

        attributes["id"] = "api_gateway_account"

        self.hcl.process_resource(
            "aws_api_gateway_account", "api_gateway_account", attributes)

    def aws_api_gateway_rest_api(self):
        resource_type = "aws_api_gateway_rest_api"
        # print("Processing API Gateway REST APIs...")

        rest_apis = self.aws_clients.apigateway_client.get_rest_apis()["items"]

        # Get the region from the client
        region = self.aws_clients.apigateway_client.meta.region_name

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn()
        ) as progress:
            task = progress.add_task("[cyan]Processing API Gateway REST APIs...", total=len(rest_apis))

            for rest_api in rest_apis:
                progress.update(task, advance=1, description=f"[cyan]apigateway [bold]{rest_api['name']}[/]")

                # if rest_api["name"] != "staging-aws-service":
                #     continue

                api_id = rest_api["id"]

                # Construct the ARN for the API Gateway REST API
                arn = f"arn:aws:apigateway:{region}::/restapis/{api_id}"

                ftstack = "apigateway"
                try:
                    response = self.aws_clients.apigateway_client.get_tags(resourceArn=arn)
                    tags = response.get('tags', {})
                    for tag_key, tag_value in tags.items():
                        if tag_key == 'ftstack':
                            if tag_value != 'apigateway':
                                ftstack = "stack_"+tag_value
                            break
                except Exception as e:
                    print("Error occurred: ", e)

                attributes = {
                    "id": api_id,
                }

                resource_name = f"{api_id}"
                self.hcl.process_resource(
                    resource_type, resource_name, attributes)

                endpoint_configuration = rest_api.get("endpointConfiguration", {})
                if "vpcEndpointIds" in endpoint_configuration:
                    for vpc_link_id in endpoint_configuration["vpcEndpointIds"]:
                        self.vpc_endpoint_instance.aws_vpc_endpoint(vpc_link_id, ftstack)

                self.hcl.add_stack(resource_type, api_id, ftstack)

                stages = self.aws_clients.apigateway_client.get_stages(restApiId=api_id)["item"]

                self.aws_api_gateway_method_settings(rest_api["id"], stages)
                self.aws_api_gateway_rest_api_policy(rest_api["id"])
                self.aws_api_gateway_resource(rest_api["id"], ftstack)
                self.aws_api_gateway_stage(rest_api["id"], stages, ftstack)
                self.aws_api_gateway_gateway_response(rest_api["id"])
                self.aws_api_gateway_model(rest_api["id"])
                self.aws_api_gateway_base_path_mapping(rest_api["id"], ftstack)

    def aws_api_gateway_deployment(self, rest_api_id, deployment_id, ftstack):
        print(f"Processing API Gateway Deployment: {deployment_id}")
        attributes = {
            "id": deployment_id,
            "rest_api_id": rest_api_id
        }
        
        # deployment = self.aws_clients.apigateway_client.get_deployment(
        #     restApiId=rest_api_id,
        #     deploymentId=deployment_id
        # )

        # if "description" in deployment:
        #     attributes["description"] = deployment["description"]

        self.hcl.process_resource(
            "aws_api_gateway_deployment", deployment_id, attributes)
        

    def aws_api_gateway_stage(self, rest_api_id, stages, ftstack):
        print("Processing API Gateway Stages...")

        for stage in stages:
            print(f"Processing API Gateway Stage: {stage['stageName']}")

            attributes = {
                "id": rest_api_id + "/" + stage["stageName"],
                "rest_api_id": rest_api_id,
                "stage_name": stage["stageName"],
                "deployment_id": stage["deploymentId"],
                "description": stage.get("description", ""),
            }

            resource_name = f"{rest_api_id}-{stage['stageName']}"
            self.hcl.process_resource(
                "aws_api_gateway_stage", resource_name, attributes)
            
            accessLogSettings = stage.get("accessLogSettings", {})
            if "destinationArn" in accessLogSettings:
                log_group_name = accessLogSettings["destinationArn"].split(":")[-1]
                self.logs_instance.aws_cloudwatch_log_group(log_group_name, ftstack)
            
            self.aws_api_gateway_deployment(rest_api_id, stage["deploymentId"], ftstack)

            # response = self.aws_clients.apigateway_client.get_export(
            #     restApiId=rest_api_id,
            #     stageName="dummy",
            #     exportType='oas30',
            #     parameters={'extensions': 'integrations'},
            #     accepts='application/yaml'
            # )
            # open_api_definition = response['body'].read()
            # # Save the YAML to a file or process it as needed
            # folder = os.path.join(ftstack)
            # os.makedirs(folder, exist_ok=True)
            # api_file_name = os.path.join(folder, f"{rest_api_id}-{stage['stageName']}-api_definition.yaml")
            # with open(api_file_name, 'wb') as file:
            #     file.write(open_api_definition)
            # print("Exported API definition to api_definition.yaml")

    def aws_api_gateway_method(self, rest_api_id, resource_id, ftstack):
        try:
            print(f"Processing API Gateway Methods for resource: {resource_id}...")

            # Attempt to retrieve the resource methods, default to an empty dict if not found
            response = self.aws_clients.apigateway_client.get_resource(restApiId=rest_api_id, resourceId=resource_id)
            methods = response.get("resourceMethods", {})

            for method, details in methods.items():
                # print(f"Processing API Gateway Method: {resource_id} {method}")

                attributes = {
                    "id": rest_api_id + "/" + resource_id + "/" + method,
                    "rest_api_id": rest_api_id,
                    "resource_id": resource_id,
                    "http_method": method,
                }

                resource_name = f"{rest_api_id}-{resource_id}-{method}"
                self.hcl.process_resource("aws_api_gateway_method", resource_name, attributes)
                self.aws_api_gateway_integration(rest_api_id, resource_id, method, ftstack)
                self.aws_api_gateway_method_response(rest_api_id, resource_id, method)

        except Exception as e:
            print(f"An error occurred: {e}")
            # Handle the exception or re-raise it depending on your needs

    def aws_api_gateway_method_settings(self, rest_api_id, stages):
        print("Processing API Gateway Method Settings...")

        for stage in stages:
            settings = stage["methodSettings"]

            for key, setting in settings.items():
                print(f"Processing API Gateway Method Setting: {key}")

                attributes = {
                    "id": rest_api_id + "/" + stage["stageName"] + "/" + key,
                    "rest_api_id": rest_api_id,
                    "stage_name": stage["stageName"],
                    "method_path": key,
                    # "settings": setting,
                }

                resource_name = f"{rest_api_id}-{stage['stageName']}-{key}"
                self.hcl.process_resource(
                    "aws_api_gateway_method_settings", resource_name, attributes)

    def aws_api_gateway_rest_api_policy(self, rest_api_id):
        print("Processing API Gateway REST API Policies...")

        rest_api = self.aws_clients.apigateway_client.get_rest_api(
            restApiId=rest_api_id)

        policy = rest_api.get("policy", None)

        if policy:
            print(
                f"Processing API Gateway REST API Policy for {rest_api['name']}")

            attributes = {
                "id": rest_api_id,
                "rest_api_id": rest_api_id,
                # "policy": policy,
            }

            resource_name = f"{rest_api_id}-policy"
            self.hcl.process_resource(
                "aws_api_gateway_rest_api_policy", resource_name, attributes)


    def aws_api_gateway_vpc_link(self, vpc_link_id, ftstack):
        resource_type = "aws_api_gateway_vpc_link"
        if vpc_link_id:
            if ftstack and self.hcl.id_resource_processed(resource_type, vpc_link_id, ftstack):
                    # print(f"  Skipping VPC Link: {vpc_link_id} - already processed")
                    return
            
        print(f"Processing API Gateway VPC Link: {vpc_link_id}")

        vpc_link = self.aws_clients.apigateway_client.get_vpc_link(
            vpcLinkId=vpc_link_id
        )

        attributes = {
            "id": vpc_link_id,
            "name": vpc_link["name"],
            "description": vpc_link.get("description", ""),
            "target_arns": vpc_link["targetArns"],
        }
        self.hcl.process_resource(resource_type, vpc_link_id, attributes)
        self.hcl.add_stack(resource_type, vpc_link_id, ftstack)

        #find any elb and call self.elbv2_instance
        for target_arn in vpc_link["targetArns"]:
            if target_arn.startswith("arn:aws:elasticloadbalancing:"):
                self.elbv2_instance.aws_lb(target_arn, ftstack)

    # def aws_api_gateway_api_key(self):
    #     print("Processing API Gateway API Keys...")

    #     paginator = self.aws_clients.apigateway_client.get_paginator("get_api_keys")
    #     page_iterator = paginator.paginate()

    #     for page in page_iterator:
    #         for api_key in page["items"]:
    #             print(f"Processing API Gateway API Key: {api_key['id']}")

    #             attributes = {
    #                 "id": api_key["id"],
    #                 "name": api_key["name"],
    #             }

    #             if "description" in api_key:
    #                 attributes["description"] = api_key["description"]

    #             if "enabled" in api_key:
    #                 attributes["enabled"] = api_key["enabled"]

    #             self.hcl.process_resource(
    #                 "aws_api_gateway_api_key", api_key["id"], attributes)

    # def aws_api_gateway_authorizer(self):
    #     print("Processing API Gateway Authorizers...")

    #     rest_apis = self.aws_clients.apigateway_client.get_rest_apis()["items"]

    #     for rest_api in rest_apis:
    #         authorizers = self.aws_clients.apigateway_client.get_authorizers(
    #             restApiId=rest_api["id"])["items"]

    #         for authorizer in authorizers:
    #             authorizer_id = authorizer['id']
    #             print(f"Processing API Gateway Authorizer: {authorizer_id}")

    #             attributes = {
    #                 "id": authorizer_id,
    #                 "rest_api_id": rest_api["id"],
    #                 # "name": authorizer["name"],
    #                 # "type": authorizer["type"],
    #             }

    #             # if "authorizerUri" in authorizer:
    #             #     attributes["authorizer_uri"] = authorizer["authorizerUri"]

    #             # if "authorizerCredentials" in authorizer:
    #             #     attributes["authorizer_credentials"] = authorizer["authorizerCredentials"]

    #             # if "identitySource" in authorizer:
    #             #     attributes["identity_source"] = authorizer["identitySource"]

    #             self.hcl.process_resource(
    #                 "aws_api_gateway_authorizer", authorizer_id, attributes)

    def aws_api_gateway_base_path_mapping(self, api_id, ftstack):
        print("Processing API Gateway Base Path Mappings...")

        domains = self.aws_clients.apigateway_client.get_domain_names()["items"]
        process_domain = False
        for domain in domains:
            base_path_mappings = self.aws_clients.apigateway_client.get_base_path_mappings(
                domainName=domain["domainName"])["items"]

            for base_path_mapping in base_path_mappings:
                if base_path_mapping["restApiId"] == api_id:
                    print(
                        f"Processing API Gateway Base Path Mapping: {base_path_mapping['basePath']}")

                    attributes = {
                        "id": f"{domain['domainName']}/{base_path_mapping['basePath']}",
                        "domain_name": domain["domainName"],
                        "rest_api_id": base_path_mapping["restApiId"],
                        "stage": base_path_mapping["stage"],
                    }

                    if "basePath" in base_path_mapping:
                        attributes["base_path"] = base_path_mapping["basePath"]

                    self.hcl.process_resource(
                        "aws_api_gateway_base_path_mapping", attributes["id"], attributes)
                    process_domain = True
            if process_domain:
                self.aws_api_gateway_domain_name(domain, ftstack)

    # def aws_api_gateway_client_certificate(self):
    #     print("Processing API Gateway Client Certificates...")

    #     client_certificates = self.aws_clients.apigateway_client.get_client_certificates()[
    #         "items"]

    #     for client_certificate in client_certificates:
    #         print(
    #             f"Processing API Gateway Client Certificate: {client_certificate['clientCertificateId']}")

    #         attributes = {
    #             "id": client_certificate['clientCertificateId'],
    #             "description": client_certificate["description"],
    #         }

    #         self.hcl.process_resource("aws_api_gateway_client_certificate",
    #                                   client_certificate["clientCertificateId"], attributes)

    # def aws_api_gateway_documentation_part(self):
    #     print("Processing API Gateway Documentation Parts...")

    #     rest_apis = self.aws_clients.apigateway_client.get_rest_apis()["items"]

    #     for rest_api in rest_apis:
    #         documentation_parts = self.aws_clients.apigateway_client.get_documentation_parts(
    #             restApiId=rest_api["id"])["items"]

    #         for documentation_part in documentation_parts:
    #             print(
    #                 f"Processing API Gateway Documentation Part: {documentation_part['id']}")

    #             attributes = {
    #                 "id": rest_api["id"]+"/"+documentation_part['id'],
    #                 # "location": documentation_part["location"],
    #                 # "properties": documentation_part["properties"],
    #             }

    #             self.hcl.process_resource(
    #                 "aws_api_gateway_documentation_part", documentation_part["id"], attributes)

    # def aws_api_gateway_documentation_version(self):
    #     print("Processing API Gateway Documentation Versions...")

    #     rest_apis = self.aws_clients.apigateway_client.get_rest_apis()["items"]

    #     for rest_api in rest_apis:
    #         documentation_versions = self.aws_clients.apigateway_client.get_documentation_versions(
    #             restApiId=rest_api["id"])["items"]

    #         for documentation_version in documentation_versions:
    #             print(
    #                 f"Processing API Gateway Documentation Version: {documentation_version['version']}")

    #             attributes = {
    #                 "id": rest_api["id"],
    #                 "version": documentation_version["version"],
    #                 "description": documentation_version["description"],
    #             }

    #             self.hcl.process_resource(
    #                 "aws_api_gateway_documentation_version", documentation_version["version"], attributes)

    def aws_api_gateway_domain_name(self, filter_domain, ftstack):
        resource_type = "aws_api_gateway_domain_name"

        domains = self.aws_clients.apigateway_client.get_domain_names()["items"]

        for domain in domains:
            if domain["domainName"] == filter_domain["domainName"]:
                print(f"Processing API Gateway Domain Name: {domain['domainName']}")

                id = domain["domainName"]
                attributes = {
                    "id": id,
                    "domain_name": domain["domainName"],
                    "certificate_arn": domain.get("certificateArn", ""),
                    "security_policy": domain.get("securityPolicy", ""),
                }

                self.hcl.process_resource(
                    resource_type, id, attributes)
                self.hcl.add_stack(resource_type, id, ftstack)

                regional_certificate_arn = domain.get("regionalCertificateArn", "")
                if regional_certificate_arn:
                    self.acm_instance.aws_acm_certificate(regional_certificate_arn, ftstack)
                certificate_arn = domain.get("certificateArn", "")
                if certificate_arn:
                    self.acm_instance.aws_acm_certificate(certificate_arn, ftstack)
                ownership_verification_certificate_arn = domain.get("ownershipVerificationCertificateArn", "")
                if ownership_verification_certificate_arn:
                    self.acm_instance.aws_acm_certificate(ownership_verification_certificate_arn, ftstack)

                

    def aws_api_gateway_gateway_response(self, rest_api_id):
        print(f"Processing API Gateway Gateway Responses for Rest API: {rest_api_id}")

        gateway_responses = self.aws_clients.apigateway_client.get_gateway_responses(
            restApiId=rest_api_id)["items"]

        for gateway_response in gateway_responses:
            print(
                f"Processing API Gateway Gateway Response: {gateway_response['responseType']}")

            attributes = {
                "id": rest_api_id + "/" + gateway_response["responseType"],
                "rest_api_id": rest_api_id,
                "response_type": gateway_response["responseType"],
            }

            resource_name = f"{rest_api_id}-{gateway_response['responseType']}"
            self.hcl.process_resource(
                "aws_api_gateway_gateway_response", resource_name, attributes)

    def aws_api_gateway_integration(self, api_id, resource_id, method, ftstack):
        print("Processing API Gateway Integrations...")
        try:
            # Retrieve the integration for the specified method
            integration = self.aws_clients.apigateway_client.get_integration(
                restApiId=api_id, resourceId=resource_id, httpMethod=method)
            
            path = self.api_gateway_resource_list[api_id][resource_id]

            # print(f"Processing API Gateway Integration: {path} {method}")

            # Prepare the attributes for the integration
            attributes = {
                "id": f"{api_id}/{resource_id}/{method}",
                "rest_api_id": api_id,
                "resource_id": resource_id,
                "http_method": method,
            }

            # Define a unique resource name for the integration
            resource_name = f"{api_id}-{resource_id}-{method}"

            # Process the integration with the attributes
            self.hcl.process_resource("aws_api_gateway_integration", resource_name, attributes)


            connection_type = integration.get("connectionType", None)
            if connection_type == "VPC_LINK":
                vpc_link_id = integration["connectionId"]
                self.aws_api_gateway_vpc_link(vpc_link_id, ftstack)


            self.aws_api_gateway_integration_response(api_id, resource_id, method, integration["integrationResponses"])

        except Exception as e:
            print(f"An error occurred: {e}")
            # Handle the exception or re-raise it depending on your needs
            pass

    def aws_api_gateway_integration_response(self, rest_api_id, resource_id, method, integration_responses):
        print("Processing API Gateway Integration Responses...")
        for status_code in integration_responses:
            # print(f"Processing API Gateway Integration Response: {resource_id} {method} {status_code}")

            attributes = {
                "id": rest_api_id+"/"+resource_id+"/"+method+"/"+status_code,
                "rest_api_id": rest_api_id,
                "resource_id": resource_id,
                "http_method": method,
                "status_code": status_code,
            }

            resource_name = f"{rest_api_id}-{resource_id}-{method}-{status_code}"
            self.hcl.process_resource(
                "aws_api_gateway_integration_response", resource_name, attributes)

    def aws_api_gateway_method_response(self, rest_api_id, resource_id, method):
        print("Processing API Gateway Method Responses...")

        method_details = self.aws_clients.apigateway_client.get_method(
            restApiId=rest_api_id, resourceId=resource_id, httpMethod=method)
        
        for status_code in method_details["methodResponses"].keys():
            # print(f"Processing API Gateway Method Response: {resource_id} {method} {status_code}")

            attributes = {
                "id": rest_api_id + "/" + resource_id + "/" + method + "/" + status_code,
                "rest_api_id": rest_api_id,
                "resource_id": resource_id,
                "http_method": method,
                "status_code": status_code,
            }

            resource_name = f"{rest_api_id}-{resource_id}-{method}-{status_code}"
            self.hcl.process_resource(
                "aws_api_gateway_method_response", resource_name, attributes)

    def aws_api_gateway_model(self, rest_api_id):
        print(f"Processing API Gateway Models for Rest API: {rest_api_id}")

        models = self.aws_clients.apigateway_client.get_models(restApiId=rest_api_id)["items"]

        for model in models:
            print(f"Processing API Gateway Model: {model['name']}")

            attributes = {
                "id": rest_api_id + "/" + model["name"],
                "rest_api_id": rest_api_id,
                "name": model["name"],
            }

            resource_name = f"{rest_api_id}-{model['name']}"
            self.hcl.process_resource("aws_api_gateway_model", resource_name, attributes)

    # def aws_api_gateway_request_validator(self):
    #     print("Processing API Gateway Request Validators...")

    #     rest_apis = self.aws_clients.apigateway_client.get_rest_apis()["items"]

    #     for rest_api in rest_apis:
    #         validators = self.aws_clients.apigateway_client.get_request_validators(
    #             restApiId=rest_api["id"])["items"]

    #         for validator in validators:
    #             print(
    #                 f"Processing API Gateway Request Validator: {validator['name']}")

    #             attributes = {
    #                 "id": rest_api["id"]+"/"+validator["name"],
    #                 "rest_api_id": rest_api["id"],
    #                 "name": validator["name"],
    #                 "validate_request_body": validator["validateRequestBody"],
    #                 "validate_request_parameters": validator["validateRequestParameters"],
    #             }

    #             resource_name = f"{rest_api['id']}-{validator['name']}"
    #             self.hcl.process_resource(
    #                 "aws_api_gateway_request_validator", resource_name, attributes)

    def aws_api_gateway_resource(self, api_id, ftstack):
        print(f"Processing API Gateway Resources for API: {api_id}")

        paginator = self.aws_clients.apigateway_client.get_paginator("get_resources")

        page_iterator = paginator.paginate(restApiId=api_id)
        max_parallel_workers = 1
        with ThreadPoolExecutor(max_workers=max_parallel_workers) as executor:
            # Prepare a list of futures
            futures = []        

            for page in page_iterator:
                resources = page["items"]

                for resource in resources:
                    future = executor.submit(self.single_aws_api_gateway_resource, resource, api_id, ftstack)
                    futures.append(future)

            for future in as_completed(futures):
                pass                    


    def single_aws_api_gateway_resource(self, resource, api_id, ftstack):
        resource_type="aws_api_gateway_resource"
        print(f"Processing API Gateway Resource: {resource['path']}")
        resource_id = resource["id"]
        attributes = {
            "id": resource_id,
            "rest_api_id": api_id,
            "parent_id": resource.get("parentId"),
            "path_part": resource.get("pathPart"),
        }

        if resource_type not in self.hcl.additional_data:
            self.hcl.additional_data[resource_type] = {}
        if resource_id not in self.hcl.additional_data[resource_type]:
            self.hcl.additional_data[resource_type][resource_id] = {}
        self.hcl.additional_data[resource_type][resource_id]["path"] = resource.get("path")

        if api_id not in self.api_gateway_resource_list:
            self.api_gateway_resource_list[api_id] = {}
        
        self.api_gateway_resource_list[api_id][resource_id] = resource.get("path")

        resource_name = f"{api_id}-{resource['path'].replace('/', '-')}"
        self.hcl.process_resource(resource_type, resource_name, attributes)

        self.aws_api_gateway_method(api_id, resource_id, ftstack)

    # def aws_api_gateway_usage_plan_key(self):
    #     print("Processing API Gateway Usage Plans and Usage Plan Keys...")

    #     paginator = self.aws_clients.apigateway_client.get_paginator("get_usage_plans")
    #     page_iterator = paginator.paginate()

    #     for page in page_iterator:
    #         for usage_plan in page["items"]:
    #             usage_plan_id = usage_plan["id"]

    #             # Process Usage Plan Keys
    #             paginator_key = self.aws_clients.apigateway_client.get_paginator(
    #                 "get_usage_plan_keys")
    #             page_iterator_key = paginator_key.paginate(
    #                 usagePlanId=usage_plan_id)

    #             for page_key in page_iterator_key:
    #                 for usage_plan_key in page_key["items"]:
    #                     key_id = usage_plan_key["id"]
    #                     key_type = usage_plan_key["type"]

    #                     print(
    #                         f"    Processing API Gateway Usage Plan Key: {key_id}")

    #                     attributes_key = {
    #                         "id": usage_plan_id+"/"+key_id,
    #                         "usage_plan_id": usage_plan_id,
    #                         "key_id": key_id,
    #                         "key_type": key_type,
    #                     }
    #                     self.hcl.process_resource(
    #                         "aws_api_gateway_usage_plan_key", f"{usage_plan_id}-{key_id}", attributes_key)

    # def aws_api_gateway_usage_plan(self):
    #     print("Processing API Gateway Usage Plans...")

    #     paginator = self.aws_clients.apigateway_client.get_paginator("get_usage_plans")
    #     page_iterator = paginator.paginate()

    #     for page in page_iterator:
    #         for usage_plan in page["items"]:
    #             usage_plan_id = usage_plan["id"]
    #             print(f"Processing API Gateway Usage Plan: {usage_plan_id}")

    #             attributes = {
    #                 "id": usage_plan_id,
    #                 "name": usage_plan["name"],
    #                 "description": usage_plan.get("description", ""),
    #                 "api_stages": usage_plan.get("apiStages", []),
    #                 "quota_settings": usage_plan.get("quota", {}),
    #                 "throttle_settings": usage_plan.get("throttle", {}),
    #             }
    #             self.hcl.process_resource(
    #                 "aws_api_gateway_usage_plan", usage_plan_id, attributes)

    # def aws_api_gateway_usage_plan_key(self):
    #     print("Processing API Gateway Usage Plan Keys...")

    #     paginator = self.aws_clients.apigateway_client.get_paginator("get_usage_plans")
    #     page_iterator = paginator.paginate()

    #     for page in page_iterator:
    #         for usage_plan in page["items"]:
    #             usage_plan_id = usage_plan["id"]

    #             # Process Usage Plan Keys
    #             paginator_key = self.aws_clients.apigateway_client.get_paginator(
    #                 "get_usage_plan_keys")
    #             page_iterator_key = paginator_key.paginate(
    #                 usagePlanId=usage_plan_id)

    #             for page_key in page_iterator_key:
    #                 for usage_plan_key in page_key["items"]:
    #                     key_id = usage_plan_key["id"]
    #                     key_type = usage_plan_key["type"]

    #                     print(
    #                         f"Processing API Gateway Usage Plan Key: {key_id}")

    #                     attributes_key = {
    #                         "id": key_id,
    #                         "usage_plan_id": usage_plan_id,
    #                         "key_id": key_id,
    #                         "key_type": key_type,
    #                     }
    #                     self.hcl.process_resource(
    #                         "aws_api_gateway_usage_plan_key", f"{usage_plan_id}-{key_id}", attributes_key)
