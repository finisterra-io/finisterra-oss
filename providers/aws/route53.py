import os
from utils.hcl import HCL


class Route53:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {
        }
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.workspace_id = workspace_id
        self.modules = modules
        self.hcl = HCL(self.schema_data, self.provider_name)

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


    def route53(self):
        self.hcl.prepare_folder(os.path.join("generated", "route53"))

        self.aws_route53_delegation_set()
        self.aws_route53_health_check()
        # self.aws_route53_key_signing_key()  # no list_key_signing_keys boto3 api
        if "gov" not in self.region:
            self.aws_route53_hosted_zone_dnssec()
            self.aws_route53_query_log()
            self.aws_route53_traffic_policy()  # Compilation errors
            self.aws_route53_traffic_policy_instance()  # Compilation errors

        self.aws_route53_record()
        self.aws_route53_vpc_association_authorization()
        self.aws_route53_zone()
        self.aws_route53_zone_association()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_route53_delegation_set(self):
        print("Processing Route53 Delegation Sets...")

        delegation_sets = self.aws_clients.route53_client.list_reusable_delegation_sets()[
            "DelegationSets"]
        for delegation_set in delegation_sets:
            delegation_set_id = delegation_set["Id"]
            print(f"Processing Route53 Delegation Set: {delegation_set_id}")

            attributes = {
                "id": delegation_set_id,
                "caller_reference": delegation_set["CallerReference"],
                "name_servers": delegation_set["NameServers"],
            }

            self.hcl.process_resource(
                "aws_route53_delegation_set", delegation_set_id.replace("-", "_"), attributes)

    def aws_route53_health_check(self):
        print("Processing Route53 Health Checks...")

        paginator = self.aws_clients.route53_client.get_paginator("list_health_checks")
        for page in paginator.paginate():
            health_checks = page["HealthChecks"]
            for health_check in health_checks:
                health_check_id = health_check["Id"]
                print(f"Processing Route53 Health Check: {health_check_id}")

                config = health_check["HealthCheckConfig"]
                attributes = {
                    "id": health_check_id,
                    "type": config["Type"],
                }

                if "IPAddress" in config:
                    attributes["ip_address"] = config["IPAddress"]
                if "Port" in config:
                    attributes["port"] = config["Port"]
                if "ResourcePath" in config:
                    attributes["resource_path"] = config["ResourcePath"]
                if "FullyQualifiedDomainName" in config:
                    attributes["fully_qualified_domain_name"] = config["FullyQualifiedDomainName"]
                if "RequestInterval" in config:
                    attributes["request_interval"] = config["RequestInterval"]
                if "FailureThreshold" in config:
                    attributes["failure_threshold"] = config["FailureThreshold"]

                self.hcl.process_resource(
                    "aws_route53_health_check", health_check_id.replace("-", "_"), attributes)

    def aws_route53_hosted_zone_dnssec(self):
        print("Processing Route53 Hosted Zone DNSSEC...")

        paginator = self.aws_clients.route53_client.get_paginator("list_hosted_zones")
        for page in paginator.paginate():
            hosted_zones = page["HostedZones"]
            for hosted_zone in hosted_zones:
                hosted_zone_id = hosted_zone["Id"]

                # Check if hosted zone is public before making get_dnssec() call
                if 'Config' in hosted_zone and hosted_zone['Config']['PrivateZone'] is False:
                    try:
                        dnssec_resp = self.aws_clients.route53_client.get_dnssec(
                            HostedZoneId=hosted_zone_id)
                        dnssec = dnssec_resp["DNSSEC"]
                    except KeyError:
                        print(
                            f"No DNSSEC configuration found for Hosted Zone: {hosted_zone_id}")
                        continue
                    except Exception as e:
                        print(
                            f"Error retrieving DNSSEC configuration for Hosted Zone: {hosted_zone_id} Error: {e}")
                        continue

                    if dnssec["Status"] != "DISABLED":
                        print(
                            f"Processing Route53 Hosted Zone DNSSEC for Hosted Zone: {hosted_zone_id}")

                        attributes = {
                            "id": dnssec["Id"],
                            "hosted_zone_id": hosted_zone_id,
                            "status": dnssec["Status"],
                        }

                        if "KeySigningKey" in dnssec:
                            attributes["key_signing_key"] = dnssec["KeySigningKey"]

                        if "ZSK" in dnssec:
                            attributes["zsk"] = dnssec["ZSK"]

                        self.hcl.process_resource(
                            "aws_route53_hosted_zone_dnssec", hosted_zone_id.replace("/", "_"), attributes)
                else:
                    print(
                        f"Skipping DNSSEC configuration for private Hosted Zone: {hosted_zone_id}")

    # def aws_route53_key_signing_key(self):
    #     print("Processing Route53 Key Signing Key...")

    #     paginator = self.aws_clients.route53_client.get_paginator("list_hosted_zones")
    #     for page in paginator.paginate():
    #         hosted_zones = page["HostedZones"]
    #         for hosted_zone in hosted_zones:
    #             hosted_zone_id = hosted_zone["Id"]
    #             next_token = None

    #             while True:
    #                 ksk_params = {"HostedZoneId": hosted_zone_id}
    #                 if next_token:
    #                     ksk_params["NextToken"] = next_token

    #                 ksk_response = self.aws_clients.route53_client.list_key_signing_keys(
    #                     **ksk_params)
    #                 key_signing_keys = ksk_response["KeySigningKeys"]

    #                 for ksk in key_signing_keys:
    #                     ksk_id = ksk["KeySigningKeyId"]
    #                     print(
    #                         f"Processing Route53 Key Signing Key: {ksk_id} for Hosted Zone: {hosted_zone_id}")

    #                     attributes = {
    #                         "id": ksk_id,
    #                         "hosted_zone_id": hosted_zone_id,
    #                         "name": ksk["Name"],
    #                         "status": ksk["Status"],
    #                         "key_management_service_arn": ksk["KmsArn"],
    #                         "digest_algorithm_mnemonic": ksk["DigestAlgorithmMnemonic"],
    #                         "digest_algorithm_type": ksk["DigestAlgorithmType"],
    #                         "key_tag": ksk["KeyTag"],
    #                         "public_key": ksk["PublicKey"],
    #                         "signing_algorithm_mnemonic": ksk["SigningAlgorithmMnemonic"],
    #                         "signing_algorithm_type": ksk["SigningAlgorithmType"],
    #                     }

    #                     self.hcl.process_resource(
    #                         "aws_route53_key_signing_key", ksk_id.replace("-", "_"), attributes)

    #                 next_token = ksk_response.get("NextToken")
    #                 if not next_token:
    #                     break

    def aws_route53_query_log(self):
        print("Processing Route53 Query Logs...")

        paginator = self.aws_clients.route53_client.get_paginator("list_hosted_zones")
        for page in paginator.paginate():
            hosted_zones = page["HostedZones"]
            for hosted_zone in hosted_zones:
                hosted_zone_id = hosted_zone["Id"]
                try:
                    query_logging_config = self.aws_clients.route53_client.list_query_logging_configs(
                        HostedZoneId=hosted_zone_id)
                    configs = query_logging_config["QueryLoggingConfigs"]

                    for config in configs:
                        if config["HostedZoneId"] == hosted_zone_id:
                            config_id = config["Id"]
                            print(
                                f"Processing Route53 Query Log: {config_id} for Hosted Zone: {hosted_zone_id}")

                            attributes = {
                                "id": config_id,
                                "zone_id": hosted_zone_id,
                                "cloudwatch_log_group_arn": config["CloudWatchLogsLogGroupArn"],
                            }

                            self.hcl.process_resource(
                                "aws_route53_query_log", config_id.replace("-", "_"), attributes)

                except self.aws_clients.route53_client.exceptions.NoSuchQueryLoggingConfig:
                    print(
                        f"  No Route53 Query Log found for Hosted Zone: {hosted_zone_id}")
                    break

    def aws_route53_record(self):
        print("Processing Route53 Records...")

        paginator = self.aws_clients.route53_client.get_paginator("list_hosted_zones")
        for page in paginator.paginate():
            hosted_zones = page["HostedZones"]
            for hosted_zone in hosted_zones:
                hosted_zone_id = hosted_zone["Id"]

                paginator_records = self.aws_clients.route53_client.get_paginator(
                    "list_resource_record_sets")
                for record_page in paginator_records.paginate(HostedZoneId=hosted_zone_id):
                    record_sets = record_page["ResourceRecordSets"]

                    for record in record_sets:
                        record_name = record["Name"].rsplit(
                            ".", 1)[0].replace("\\052", "*")
                        record_type = record["Type"]

                        record_id = f"{hosted_zone_id}-{record_name}-{record_type}"
                        print(
                            f"Processing Route53 Record: {record_name} with Type: {record_type} in Hosted Zone: {hosted_zone_id}")

                        attributes = {
                            "id": record_id,
                            "zone_id": hosted_zone_id,
                            "name": record_name,
                            "type": record_type,
                            "ttl": record.get("TTL", None),
                            "records": [rr["Value"] for rr in record.get("ResourceRecords", [])],
                        }

                        self.hcl.process_resource(
                            "aws_route53_record", record_id.replace("-", "_"), attributes)

    def aws_route53_traffic_policy(self):
        print("Processing Route53 Traffic Policies...")

        next_token = None

        while True:
            traffic_policy_params = {}
            if next_token:
                traffic_policy_params["TrafficPolicyIdMarker"] = next_token

            traffic_policies_response = self.aws_clients.route53_client.list_traffic_policies(
                **traffic_policy_params)
            traffic_policies = traffic_policies_response["TrafficPolicySummaries"]

            for traffic_policy in traffic_policies:
                traffic_policy_id = traffic_policy["Id"]
                traffic_policy_version = traffic_policy["LatestVersion"]

                print(
                    f"Processing Route53 Traffic Policy: {traffic_policy_id} Version: {traffic_policy_version}")

                traffic_policy_detail = self.aws_clients.route53_client.get_traffic_policy(
                    Id=traffic_policy_id,
                    Version=traffic_policy_version
                )["TrafficPolicy"]

                attributes = {
                    "id": traffic_policy_id,
                    "name": traffic_policy_detail["Name"],
                    "version": traffic_policy_version,
                    "document": traffic_policy_detail["Document"],
                }

                self.hcl.process_resource(
                    "aws_route53_traffic_policy", traffic_policy_id.replace("-", "_"), attributes)

            next_token = traffic_policies_response.get("TrafficPolicyIdMarker")
            if not next_token:
                break

    def aws_route53_traffic_policy_instance(self):
        print("Processing Route53 Traffic Policy Instances...")

        next_type_token = None
        next_name_token = None

        while True:
            traffic_policy_instance_params = {}
            if next_type_token:
                traffic_policy_instance_params["TrafficPolicyInstanceTypeMarker"] = next_type_token
            if next_name_token:
                traffic_policy_instance_params["TrafficPolicyInstanceNameMarker"] = next_name_token

            traffic_policy_instances_response = self.aws_clients.route53_client.list_traffic_policy_instances(
                **traffic_policy_instance_params)
            traffic_policy_instances = traffic_policy_instances_response["TrafficPolicyInstances"]

            for instance in traffic_policy_instances:
                instance_id = instance["Id"]
                policy_id = instance["TrafficPolicyId"]
                policy_version = instance["TrafficPolicyVersion"]

                print(
                    f"Processing Route53 Traffic Policy Instance: {instance_id}")

                attributes = {
                    "id": instance_id,
                    "traffic_policy_id": policy_id,
                    "traffic_policy_version": policy_version,
                    "hosted_zone_id": instance["HostedZoneId"],
                    "name": instance["Name"],
                    "ttl": instance["TTL"],
                }

                self.hcl.process_resource(
                    "aws_route53_traffic_policy_instance", instance_id.replace("-", "_"), attributes)

            next_type_token = traffic_policy_instances_response.get(
                "TrafficPolicyInstanceTypeMarker")
            next_name_token = traffic_policy_instances_response.get(
                "TrafficPolicyInstanceNameMarker")
            if not next_type_token and not next_name_token:
                break

    def aws_route53_vpc_association_authorization(self):
        print("Processing Route53 VPC Association Authorizations...")

        paginator = self.aws_clients.route53_client.get_paginator("list_hosted_zones")
        for page in paginator.paginate():
            hosted_zones = page["HostedZones"]
            for hosted_zone in hosted_zones:
                hosted_zone_id = hosted_zone["Id"]

                vpc_association_authorizations = self.aws_clients.route53_client.list_vpc_association_authorizations(
                    HostedZoneId=hosted_zone_id
                )["VPCs"]

                for vpc_assoc_auth in vpc_association_authorizations:
                    vpc_id = vpc_assoc_auth["VPCId"]
                    vpc_region = vpc_assoc_auth["VPCRegion"]

                    print(
                        f"Processing Route53 VPC Association Authorization: Hosted Zone: {hosted_zone_id}, VPC: {vpc_id}")

                    attributes = {
                        "id": f"{hosted_zone_id}:{vpc_id}",
                        "zone_id": hosted_zone_id,
                        "vpc_id": vpc_id,
                        "vpc_region": vpc_region,
                    }

                    self.hcl.process_resource("aws_route53_vpc_association_authorization",
                                              f"{hosted_zone_id.replace('/', '_')}-{vpc_id.replace('-', '_')}", attributes)

    def aws_route53_zone(self):
        print("Processing Route53 Zones...")

        paginator = self.aws_clients.route53_client.get_paginator("list_hosted_zones")
        for page in paginator.paginate():
            hosted_zones = page["HostedZones"]
            for hosted_zone in hosted_zones:
                hosted_zone_id = hosted_zone["Id"]
                name = hosted_zone["Name"]
                private_zone = hosted_zone["Config"]["PrivateZone"]

                print(
                    f"Processing Route53 Zone: {name} (ID: {hosted_zone_id})")

                attributes = {
                    "id": hosted_zone_id,
                    "name": name,
                    "private_zone": private_zone,
                }

                self.hcl.process_resource(
                    "aws_route53_zone", hosted_zone_id.replace("/", "_"), attributes)

    def aws_route53_zone_association(self):
        print("Processing Route53 Zone Associations...")

        paginator = self.aws_clients.route53_client.get_paginator("list_hosted_zones")
        for page in paginator.paginate():
            hosted_zones = page["HostedZones"]
            for hosted_zone in hosted_zones:
                hosted_zone_id = hosted_zone["Id"]

                if hosted_zone["Config"]["PrivateZone"]:
                    associations = self.aws_clients.route53_client.list_vpc_association_authorizations(
                        HostedZoneId=hosted_zone_id)

                    for association in associations["VPCs"]:
                        vpc_id = association["VPCId"]
                        association_id = f"{hosted_zone_id}-{vpc_id}"

                        print(
                            f"Processing Route53 Zone Association: Hosted Zone {hosted_zone_id} with VPC {vpc_id}")

                        attributes = {
                            "id": association_id,
                            "zone_id": hosted_zone_id,
                            "vpc_id": vpc_id,
                        }

                        self.hcl.process_resource(
                            "aws_route53_zone_association", association_id.replace("/", "_"), attributes)
