import os
from utils.hcl import HCL


class Apigatewayv2:
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


    def apigatewayv2(self):
        self.hcl.prepare_folder(os.path.join("generated", "apigatewayv2"))

        self.aws_apigatewayv2_api()
        self.aws_apigatewayv2_api_mapping()
        self.aws_apigatewayv2_authorizer()
        self.aws_apigatewayv2_deployment()
        # self.aws_apigatewayv2_domain_name() #Need permissions
        self.aws_apigatewayv2_integration()
        self.aws_apigatewayv2_integration_response()
        self.aws_apigatewayv2_model()
        self.aws_apigatewayv2_route()
        self.aws_apigatewayv2_route_response()
        self.aws_apigatewayv2_stage()
        self.aws_apigatewayv2_vpc_link()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_apigatewayv2_api(self):
        print("Processing API Gateway v2 APIs...")

        paginator = self.aws_clients.apigatewayv2_client.get_paginator("get_apis")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for api in page["Items"]:
                print(f"Processing API Gateway v2 API: {api['ApiId']}")

                attributes = {
                    "name": api["Name"],
                    "protocol_type": api["ProtocolType"],
                }
                if "ApiKeySelectionExpression" in api:
                    attributes["api_key_selection_expression"] = api["ApiKeySelectionExpression"]
                if "CorsConfiguration" in api:
                    attributes["cors_configuration"] = api["CorsConfiguration"]
                if "Description" in api:
                    attributes["description"] = api["Description"]
                if "RouteSelectionExpression" in api:
                    attributes["route_selection_expression"] = api["RouteSelectionExpression"]

                self.hcl.process_resource(
                    "aws_apigatewayv2_api", api["ApiId"], attributes)

    def aws_apigatewayv2_api_mapping(self):
        print("Processing API Gateway v2 API Mappings...")

        apis = self.aws_clients.apigatewayv2_client.get_apis()["Items"]
        for api in apis:
            api_id = api["ApiId"]
            print(
                f"Processing API Gateway v2 API Mappings for API ID: {api_id}")

            paginator = self.aws_clients.apigatewayv2_client.get_paginator(
                "get_api_mappings")
            page_iterator = paginator.paginate(ApiId=api_id)

            for page in page_iterator:
                for mapping in page["Items"]:
                    print(
                        f"    Processing API Gateway v2 API Mapping: {mapping['ApiMappingId']}")

                    attributes = {
                        "api_id": api_id,
                        "domain_name": mapping["ApiMappingCustomDomainName"],
                        "stage": mapping["Stage"],
                    }
                    if "ApiMappingKey" in mapping:
                        attributes["api_mapping_key"] = mapping["ApiMappingKey"]

                    self.hcl.process_resource(
                        "aws_apigatewayv2_api_mapping", mapping["ApiMappingId"], attributes)

    def aws_apigatewayv2_authorizer(self):
        print("Processing API Gateway v2 Authorizers...")

        apis = self.aws_clients.apigatewayv2_client.get_apis()["Items"]
        for api in apis:
            api_id = api["ApiId"]
            print(
                f"Processing API Gateway v2 Authorizers for API ID: {api_id}")

            paginator = self.aws_clients.apigatewayv2_client.get_paginator(
                "get_authorizers")
            page_iterator = paginator.paginate(ApiId=api_id)

            for page in page_iterator:
                for authorizer in page["Items"]:
                    print(
                        f"    Processing API Gateway v2 Authorizer: {authorizer['AuthorizerId']}")

                    attributes = {
                        "api_id": api_id,
                        "authorizer_type": authorizer["AuthorizerType"],
                        "name": authorizer["Name"],
                    }
                    if "IdentitySource" in authorizer:
                        attributes["identity_source"] = authorizer["IdentitySource"]
                    if "JwtConfiguration" in authorizer:
                        attributes["jwt_configuration"] = authorizer["JwtConfiguration"]
                    if "AuthorizerResultTtlInSeconds" in authorizer:
                        attributes["authorizer_result_ttl_in_seconds"] = authorizer["AuthorizerResultTtlInSeconds"]

                    self.hcl.process_resource(
                        "aws_apigatewayv2_authorizer", authorizer["AuthorizerId"], attributes)

    def aws_apigatewayv2_deployment(self):
        print("Processing API Gateway v2 Deployments...")

        apis = self.aws_clients.apigatewayv2_client.get_apis()["Items"]
        for api in apis:
            api_id = api["ApiId"]
            print(
                f"Processing API Gateway v2 Deployments for API ID: {api_id}")

            paginator = self.aws_clients.apigatewayv2_client.get_paginator(
                "get_deployments")
            page_iterator = paginator.paginate(ApiId=api_id)

            for page in page_iterator:
                for deployment in page["Items"]:
                    print(
                        f"    Processing API Gateway v2 Deployment: {deployment['DeploymentId']}")

                    attributes = {
                        "api_id": api_id,
                    }
                    if "Description" in deployment:
                        attributes["description"] = deployment["Description"]

                    self.hcl.process_resource(
                        "aws_apigatewayv2_deployment", deployment["DeploymentId"], attributes)

    def aws_apigatewayv2_domain_name(self):
        print("  Processing API Gateway v2 Domain Names")

        paginator = self.aws_clients.apigatewayv2_client.get_paginator("get_domain_names")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for domain_name in page["Items"]:
                print(
                    f"    Processing API Gateway v2 Domain Name: {domain_name['DomainName']}")

                attributes = {
                    "domain_name": domain_name["DomainName"],
                    "domain_name_configuration": domain_name["DomainNameConfigurations"][0],
                }

                self.hcl.process_resource(
                    "aws_apigatewayv2_domain_name", domain_name["DomainName"], attributes)

    def aws_apigatewayv2_integration(self):
        print("Processing API Gateway v2 Integrations...")

        apis = self.aws_clients.apigatewayv2_client.get_apis()["Items"]
        for api in apis:
            api_id = api["ApiId"]
            print(
                f"Processing API Gateway v2 Integrations for API ID: {api_id}")

            paginator = self.aws_clients.apigatewayv2_client.get_paginator(
                "get_integrations")
            page_iterator = paginator.paginate(ApiId=api_id)

            for page in page_iterator:
                for integration in page["Items"]:
                    print(
                        f"    Processing API Gateway v2 Integration: {integration['IntegrationId']}")

                    attributes = {
                        "api_id": api_id,
                        "integration_type": integration["IntegrationType"],
                    }
                    if "IntegrationMethod" in integration:
                        attributes["integration_method"] = integration["IntegrationMethod"]
                    if "IntegrationUri" in integration:
                        attributes["integration_uri"] = integration["IntegrationUri"]
                    if "ConnectionType" in integration:
                        attributes["connection_type"] = integration["ConnectionType"]
                    if "ConnectionId" in integration:
                        attributes["connection_id"] = integration["ConnectionId"]
                    if "TimeoutInMillis" in integration:
                        attributes["timeout_in_millis"] = integration["TimeoutInMillis"]

                    self.hcl.process_resource(
                        "aws_apigatewayv2_integration", integration["IntegrationId"], attributes)

    def aws_apigatewayv2_integration_response(self):
        print("Processing API Gateway v2 Integration Responses...")

        apis = self.aws_clients.apigatewayv2_client.get_apis()["Items"]
        for api in apis:
            api_id = api["ApiId"]
            print(
                f"Processing API Gateway v2 Integration Responses for API ID: {api_id}")

            integrations = self.aws_clients.apigatewayv2_client.get_integrations(ApiId=api_id)[
                "Items"]
            for integration in integrations:
                integration_id = integration["IntegrationId"]
                print(
                    f"    Processing API Gateway v2 Integration Responses for Integration ID: {integration_id}")

                paginator = self.aws_clients.apigatewayv2_client.get_paginator(
                    "get_integration_responses")
                page_iterator = paginator.paginate(
                    ApiId=api_id, IntegrationId=integration_id)

                for page in page_iterator:
                    for integration_response in page["Items"]:
                        print(
                            f"      Processing API Gateway v2 Integration Response: {integration_response['IntegrationResponseId']}")

                        attributes = {
                            "api_id": api_id,
                            "integration_id": integration_id,
                            "integration_response_key": integration_response["IntegrationResponseKey"],
                        }

                        self.hcl.process_resource("aws_apigatewayv2_integration_response",
                                                  integration_response["IntegrationResponseId"], attributes)

    def aws_apigatewayv2_model(self):
        print("Processing API Gateway v2 Models...")

        apis = self.aws_clients.apigatewayv2_client.get_apis()["Items"]
        for api in apis:
            api_id = api["ApiId"]
            print(f"Processing API Gateway v2 Models for API ID: {api_id}")

            paginator = self.aws_clients.apigatewayv2_client.get_paginator("get_models")
            page_iterator = paginator.paginate(ApiId=api_id)

            for page in page_iterator:
                for model in page["Items"]:
                    print(
                        f"    Processing API Gateway v2 Model: {model['Name']}")

                    attributes = {
                        "api_id": api_id,
                        "name": model["Name"],
                        "content_type": model["ContentType"],
                        "schema": model["Schema"],
                    }

                    self.hcl.process_resource(
                        "aws_apigatewayv2_model", model["Name"], attributes)

    def aws_apigatewayv2_route(self):
        print("Processing API Gateway v2 Routes...")

        api_ids = self.aws_clients.apigatewayv2_client.get_apis()["Items"]

        for api in api_ids:
            api_id = api["ApiId"]
            print(f"Processing API Gateway v2 Routes for API ID: {api_id}")

            paginator = self.aws_clients.apigatewayv2_client.get_paginator("get_routes")
            page_iterator = paginator.paginate(ApiId=api_id)

            for page in page_iterator:
                for route in page["Items"]:
                    print(
                        f"    Processing API Gateway v2 Route: {route['RouteId']}")

                    attributes = {
                        "api_id": api_id,
                        "route_key": route["RouteKey"],
                    }

                    if "Target" in route:
                        attributes["target"] = route["Target"]

                    self.hcl.process_resource(
                        "aws_apigatewayv2_route", route["RouteId"], attributes)

    def aws_apigatewayv2_route_response(self):
        print("Processing API Gateway v2 Route Responses...")

        api_ids = self.aws_clients.apigatewayv2_client.get_apis()["Items"]

        for api in api_ids:
            api_id = api["ApiId"]
            print(f"Processing Route Responses for API ID: {api_id}")

            routes = self.aws_clients.apigatewayv2_client.get_routes(ApiId=api_id)["Items"]

            for route in routes:
                route_id = route["RouteId"]
                print(
                    f"    Processing API Gateway v2 Route Responses for Route ID: {route_id}")

                paginator = self.aws_clients.apigatewayv2_client.get_paginator(
                    "get_route_responses")
                page_iterator = paginator.paginate(
                    ApiId=api_id, RouteId=route_id)

                for page in page_iterator:
                    for route_response in page["Items"]:
                        print(
                            f"      Processing API Gateway v2 Route Response: {route_response['RouteResponseId']}")

                        attributes = {
                            "api_id": api_id,
                            "route_id": route_id,
                            "route_response_key": route_response["RouteResponseKey"],
                        }

                        self.hcl.process_resource(
                            "aws_apigatewayv2_route_response", route_response["RouteResponseId"], attributes)

    def aws_apigatewayv2_stage(self):
        print("Processing API Gateway v2 Stages...")

        api_ids = self.aws_clients.apigatewayv2_client.get_apis()["Items"]

        for api in api_ids:
            api_id = api["ApiId"]
            print(f"Processing API Gateway v2 Stages for API ID: {api_id}")

            paginator = self.aws_clients.apigatewayv2_client.get_paginator("get_stages")
            page_iterator = paginator.paginate(ApiId=api_id)

            for page in page_iterator:
                for stage in page["Items"]:
                    print(
                        f"    Processing API Gateway v2 Stage: {stage['StageName']}")

                    attributes = {
                        "api_id": api_id,
                        "name": stage["StageName"],
                    }

                    if "AutoDeploy" in stage:
                        attributes["auto_deploy"] = stage["AutoDeploy"]

                    if "DeploymentId" in stage:
                        attributes["deployment_id"] = stage["DeploymentId"]

                    self.hcl.process_resource(
                        "aws_apigatewayv2_stage", stage["StageName"], attributes)

    def aws_apigatewayv2_vpc_link(self):
        print("Processing API Gateway v2 VPC Links...")

        vpc_links = self.aws_clients.apigatewayv2_client.get_vpc_links()["Items"]

        for vpc_link in vpc_links:
            print(
                f"Processing API Gateway v2 VPC Link: {vpc_link['VpcLinkId']}")

            attributes = {
                "name": vpc_link["Name"],
                "subnet_ids": vpc_link["SubnetIds"],
            }

            if "SecurityGroupIds" in vpc_link:
                attributes["security_group_ids"] = vpc_link["SecurityGroupIds"]

            self.hcl.process_resource(
                "aws_apigatewayv2_vpc_link", vpc_link["VpcLinkId"], attributes)
