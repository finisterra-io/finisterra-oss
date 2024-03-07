from ...utils.hcl import HCL
from ...providers.aws.iam_role import IAM
from ...providers.aws.s3 import S3
from ...providers.aws.logs import Logs
import logging
import inspect

logger = logging.getLogger('finisterra')


class VPC:
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

        self.public_subnets = {}
        self.private_subnets = {}
        self.public_route_table_ids = {}
        self.private_route_table_ids = {}
        self.public_nat_gateway_ids = {}
        self.private_route_tables = {}
        self.network_acl_ids = {}
        self.network_acls = {}
        self.dhcp_options_domain_name = {}
        self.default_routes = {}

        self.iam_role_instance = IAM(self.provider_instance, self.hcl)
        self.s3_instance = S3(self.provider_instance, self.hcl)
        self.logs_instance = Logs(self.provider_instance, self.hcl)

    def is_subnet_public(self, subnet_id):
        route_tables = self.provider_instance.aws_clients.ec2_client.describe_route_tables(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}])
        for route_table in route_tables['RouteTables']:
            for route in route_table['Routes']:
                if route.get('GatewayId', '').startswith('igw-'):
                    return True
        return False

    def is_subnet_private(self, subnet_id):
        route_tables = self.provider_instance.aws_clients.ec2_client.describe_route_tables(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}])
        for route_table in route_tables['RouteTables']:
            for route in route_table['Routes']:
                if route.get('GatewayId', '').startswith('igw-'):
                    return False
        return True

    def vpc(self):
        self.hcl.prepare_folder()
        self.aws_vpc()
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

    def aws_vpc(self):
        resource_type = "aws_vpc"
        logger.debug("Processing VPCs...")
        vpcs = self.provider_instance.aws_clients.ec2_client.describe_vpcs()["Vpcs"]
        if len(vpcs) > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=len(vpcs))
        for vpc in vpcs:
            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{vpc['VpcId']}[/]")
            is_default = vpc.get("IsDefault", False)
            if not is_default:
                vpc_id = vpc["VpcId"]
                # if vpc_id != "xxxx":
                #     continue
                logger.debug(f"Processing VPC: {vpc_id}")
                id = vpc_id

                ftstack = "vpc"
                try:
                    tags_response = self.provider_instance.aws_clients.ec2_client.describe_tags(
                        Filters=[{'Name': 'resource-id', 'Values': [vpc_id]}]
                    )
                    tags = tags_response.get('Tags', [])
                    for tag in tags:
                        if tag['Key'] == 'ftstack':
                            if tag['Value'] != "vpc":
                                ftstack = "stack_"+tag['Value']
                            break
                except Exception as e:
                    logger.debug(f"Error occurred: {e}")

                attributes = {
                    "id": id,
                }
                self.hcl.process_resource(
                    resource_type, id, attributes)

                self.hcl.add_stack(resource_type, id, ftstack)

                self.aws_subnet(vpc)  # pass the vpc
                self.aws_internet_gateway(vpc_id)  # pass the vpc_id
                self.aws_route_table(vpc_id)
                # call aws_default_route_table with vpc_id
                self.aws_default_route_table(vpc_id)
                # call aws_default_network_acl with vpc_id
                self.aws_default_network_acl(vpc_id)
                # call aws_default_security_group with vpc_id
                self.aws_default_security_group(vpc_id)
                # call aws_network_acl with vpc_id
                self.aws_network_acl(vpc_id)
                # call aws_flow_log with vpc_id
                self.aws_flow_log(vpc_id, ftstack)
                # call aws_vpc_dhcp_options with vpc_id
                self.aws_vpc_dhcp_options_association(vpc_id)
                # Nat Gateway
                self.aws_nat_gateway(vpc_id)

    def aws_subnet(self, vpc):
        logger.debug("Processing Subnets...")

        vpc_id = vpc["VpcId"]

        subnets = self.provider_instance.aws_clients.ec2_client.describe_subnets()["Subnets"]
        for subnet in subnets:
            if subnet["VpcId"] == vpc_id:
                subnet_id = subnet["SubnetId"]
                logger.debug(f"    Processing Subnet: {subnet_id}")
                attributes = {
                    "id": subnet_id,
                    "vpc_id": vpc_id,
                    "cidr_block": subnet["CidrBlock"],
                    "availability_zone": subnet["AvailabilityZone"],
                }
                self.hcl.process_resource(
                    "aws_subnet", subnet_id.replace("-", "_"), attributes)

                self.aws_route_table_association(subnet_id)
                is_public = self.is_subnet_public(subnet_id)
                self.hcl.add_additional_data(
                    "aws_subnet", subnet_id, "is_public", is_public)
                is_private = self.is_subnet_private(subnet_id)
                self.hcl.add_additional_data(
                    "aws_subnet", subnet_id, "is_private", is_private)

    def aws_internet_gateway(self, vpc_id):
        logger.debug("Processing Internet Gateways...")
        internet_gateways = self.provider_instance.aws_clients.ec2_client.describe_internet_gateways()[
            "InternetGateways"]

        for igw in internet_gateways:
            igw_id = igw["InternetGatewayId"]
            attached_vpc_id = igw["Attachments"][0]["VpcId"] if igw["Attachments"] else ""

            if attached_vpc_id == vpc_id:
                logger.debug(f"Processing Internet Gateway: {igw_id}")

                attributes = {
                    "id": igw_id,
                    "vpc_id": attached_vpc_id,
                }
                self.hcl.process_resource(
                    "aws_internet_gateway", igw_id.replace("-", "_"), attributes)

                route_tables = self.provider_instance.aws_clients.ec2_client.describe_route_tables()[
                    "RouteTables"]

                for rt in route_tables:
                    for route in rt["Routes"]:
                        if route.get("GatewayId", "") == igw_id:  # match the GatewayId
                            # pass the route_table_id and the route
                            self.aws_route(rt["RouteTableId"], route)

    def aws_default_route_table(self, vpc_id):
        logger.debug("Processing Default Route Tables...")
        route_tables = self.provider_instance.aws_clients.ec2_client.describe_route_tables(
            Filters=[{"Name": "association.main", "Values": ["true"]},
                     {"Name": "vpc-id", "Values": [vpc_id]}]  # Filter for the given vpc_id
        )["RouteTables"]

        for route_table in route_tables:
            route_table_id = route_table["RouteTableId"]
            logger.debug(
                f"Processing Default Route Table: {route_table_id} for VPC: {vpc_id}")

            self.default_routes[route_table_id] = []
            for route in route_table["Routes"]:
                if route.get("GatewayId", "") != "local":
                    self.default_routes[route_table_id] = route_table["Routes"]
                    self.default_routes[route_table_id].remove(route)

            attributes = {
                "id": route_table_id,
                "vpc_id": vpc_id,
            }
            self.hcl.process_resource(
                "aws_default_route_table", route_table_id.replace("-", "_"), attributes)

    def aws_default_network_acl(self, vpc_id):
        logger.debug("Processing Default Network ACLs...")
        network_acls = self.provider_instance.aws_clients.ec2_client.describe_network_acls(
            Filters=[{"Name": "default", "Values": ["true"]},
                     {"Name": "vpc-id", "Values": [vpc_id]}]  # Filter for the given vpc_id
        )["NetworkAcls"]
        for network_acl in network_acls:
            network_acl_id = network_acl["NetworkAclId"]
            default_network_acl_id = network_acl["NetworkAclId"]
            logger.debug(
                f"Processing Default Network ACL: {network_acl_id} for VPC: {vpc_id}")

            attributes = {
                "id": network_acl_id,
                "vpc_id": vpc_id,
                "default_network_acl_id": default_network_acl_id,
            }
            self.hcl.process_resource(
                "aws_default_network_acl", network_acl_id.replace("-", "_"), attributes)

    def aws_default_security_group(self, vpc_id):
        logger.debug("Processing Default Security Groups...")
        security_groups = self.provider_instance.aws_clients.ec2_client.describe_security_groups(
            Filters=[{"Name": "group-name", "Values": ["default"]},
                     {"Name": "vpc-id", "Values": [vpc_id]}]  # Filter for the given vpc_id
        )["SecurityGroups"]

        for security_group in security_groups:
            security_group_id = security_group["GroupId"]
            logger.debug(
                f"Processing Default Security Group: {security_group_id} for VPC: {vpc_id}")

            attributes = {
                "id": security_group_id,
                "vpc_id": vpc_id,
            }
            self.hcl.process_resource(
                "aws_default_security_group", security_group_id.replace("-", "_"), attributes)

    def aws_default_subnet(self):
        logger.debug("Processing Default Subnets...")
        subnets = self.provider_instance.aws_clients.ec2_client.describe_subnets(
            Filters=[{"Name": "default-for-az", "Values": ["true"]}]
        )["Subnets"]

        for subnet in subnets:
            vpc_id = subnet["VpcId"]
            subnet_id = subnet["SubnetId"]
            logger.debug(
                f"Processing Default Subnet: {subnet_id} for VPC: {vpc_id}")

            attributes = {
                "id": subnet_id,
                "vpc_id": vpc_id,
                "cidr_block": subnet["CidrBlock"],
                "availability_zone": subnet["AvailabilityZone"],
            }
            self.hcl.process_resource(
                "aws_default_subnet", subnet_id.replace("-", "_"), attributes)

    def aws_default_vpc(self):
        logger.debug("Processing Default VPCs...")
        vpcs = self.provider_instance.aws_clients.ec2_client.describe_vpcs(
            Filters=[{"Name": "isDefault", "Values": ["true"]}]
        )["Vpcs"]

        for vpc in vpcs:
            vpc_id = vpc["VpcId"]
            logger.debug(f"Processing Default VPC: {vpc_id}")

            attributes = {
                "id": vpc_id,
            }
            self.hcl.process_resource(
                "aws_default_vpc", vpc_id.replace("-", "_"), attributes)

    def aws_default_vpc_dhcp_options(self):
        logger.debug("Processing Default VPC DHCP Options...")
        dhcp_options = self.provider_instance.aws_clients.ec2_client.describe_dhcp_options(
            Filters=[{"Name": "default", "Values": ["true"]}]
        )["DhcpOptions"]

        for dhcp_option in dhcp_options:
            dhcp_options_id = dhcp_option["DhcpOptionsId"]
            logger.debug(
                f"Processing Default VPC DHCP Options: {dhcp_options_id}")

            attributes = {
                "id": dhcp_options_id,
            }
            self.hcl.process_resource(
                "aws_default_vpc_dhcp_options", dhcp_options_id.replace("-", "_"), attributes)

    def aws_ec2_managed_prefix_list(self):
        logger.debug("Processing EC2 Managed Prefix Lists...")
        prefix_lists = self.provider_instance.aws_clients.ec2_client.describe_managed_prefix_lists()[
            "PrefixLists"]

        for prefix_list in prefix_lists:
            prefix_list_id = prefix_list["PrefixListId"]
            logger.debug(
                f"Processing EC2 Managed Prefix List: {prefix_list_id}")

            # Get the entries for the prefix list
            entries = self.provider_instance.aws_clients.ec2_client.get_managed_prefix_list_entries(
                PrefixListId=prefix_list_id)["Entries"]

            entry_attributes = []
            for entry in entries:
                entry_attributes.append({
                    "cidr": entry["Cidr"],
                    "description": entry.get("Description", ""),
                })

            attributes = {
                "id": prefix_list_id,
                "name": prefix_list["PrefixListName"],
                "address_family": prefix_list["AddressFamily"],
                "entries": entry_attributes,
            }
            self.hcl.process_resource(
                "aws_ec2_managed_prefix_list", prefix_list_id.replace("-", "_"), attributes)

    def aws_ec2_network_insights_analysis(self):
        logger.debug("Processing EC2 Network Insights Analysis...")
        network_insights_analyses = self.provider_instance.aws_clients.ec2_client.describe_network_insights_analyses()[
            "NetworkInsightsAnalyses"]

        for analysis in network_insights_analyses:
            analysis_id = analysis["NetworkInsightsAnalysisId"]
            logger.debug(
                f"Processing EC2 Network Insights Analysis: {analysis_id}")

            attributes = {
                "id": analysis_id,
                "network_insights_path_id": analysis["NetworkInsightsPathId"],
                "status": analysis["Status"],
                "status_message": analysis.get("StatusMessage", ""),
            }
            self.hcl.process_resource(
                "aws_ec2_network_insights_analysis", analysis_id.replace("-", "_"), attributes)

    def aws_ec2_network_insights_path(self):
        logger.debug("Processing EC2 Network Insights Paths...")
        network_insights_paths = self.provider_instance.aws_clients.ec2_client.describe_network_insights_paths()[
            "NetworkInsightsPaths"]

        for path in network_insights_paths:
            path_id = path["NetworkInsightsPathId"]
            logger.debug(f"Processing EC2 Network Insights Path: {path_id}")

            attributes = {
                "id": path_id,
                "source": path["Source"],
                "destination": path["Destination"],
                "protocol": path.get("Protocol", ""),
            }
            self.hcl.process_resource(
                "aws_ec2_network_insights_path", path_id.replace("-", "_"), attributes)

    def aws_ec2_subnet_cidr_reservation(self):
        logger.debug("Processing Subnet CIDR Reservations...")
        subnets = self.provider_instance.aws_clients.ec2_client.describe_subnets()["Subnets"]

        for subnet in subnets:
            subnet_id = subnet["SubnetId"]
            cidr_reservations_response = self.provider_instance.aws_clients.ec2_client.get_subnet_cidr_reservations(
                SubnetId=subnet_id)

            # Process IPv4 CIDR reservations
            ipv4_cidr_reservations = cidr_reservations_response["SubnetIpv4CidrReservations"]
            for cidr_reservation in ipv4_cidr_reservations:
                reservation_id = cidr_reservation["CidrReservationId"]
                logger.debug(
                    f"Processing IPv4 Subnet CIDR Reservation: {reservation_id} in Subnet: {subnet_id}")

                attributes = {
                    "id": reservation_id,
                    "subnet_id": subnet_id,
                    "cidr_block": cidr_reservation["Cidr"],
                }
                self.hcl.process_resource(
                    "aws_ec2_subnet_cidr_reservation", reservation_id.replace("-", "_"), attributes)

            # Process IPv6 CIDR reservations
            ipv6_cidr_reservations = cidr_reservations_response["SubnetIpv6CidrReservations"]
            for cidr_reservation in ipv6_cidr_reservations:
                reservation_id = cidr_reservation["CidrReservationId"]
                logger.debug(
                    f"Processing IPv6 Subnet CIDR Reservation: {reservation_id} in Subnet: {subnet_id}")

                attributes = {
                    "id": reservation_id,
                    "subnet_id": subnet_id,
                    "cidr_block": cidr_reservation["Cidr"],
                }
                self.hcl.process_resource(
                    "aws_ec2_subnet_cidr_reservation", reservation_id.replace("-", "_"), attributes)

    def aws_ec2_traffic_mirror_filter(self):
        logger.debug("Processing EC2 Traffic Mirror Filters...")
        traffic_mirror_filters = self.provider_instance.aws_clients.ec2_client.describe_traffic_mirror_filters()[
            "TrafficMirrorFilters"]

        for tm_filter in traffic_mirror_filters:
            tm_filter_id = tm_filter["TrafficMirrorFilterId"]
            logger.debug(
                f"Processing EC2 Traffic Mirror Filter: {tm_filter_id}")

            attributes = {
                "id": tm_filter_id,
                "description": tm_filter.get("Description", ""),
            }
            self.hcl.process_resource(
                "aws_ec2_traffic_mirror_filter", tm_filter_id.replace("-", "_"), attributes)

    def aws_ec2_traffic_mirror_filter_rule(self):
        logger.debug("Processing EC2 Traffic Mirror Filter Rules...")
        traffic_mirror_filters = self.provider_instance.aws_clients.ec2_client.describe_traffic_mirror_filters()[
            "TrafficMirrorFilters"]

        for tm_filter in traffic_mirror_filters:
            tm_filter_id = tm_filter["TrafficMirrorFilterId"]

            # Describe the ingress and egress rules for the traffic mirror filter
            ingress_rules = self.provider_instance.aws_clients.ec2_client.describe_traffic_mirror_filter_rules(
                Filters=[{"Name": "traffic-mirror-filter-id",
                          "Values": [tm_filter_id]}],
                Direction="ingress"
            )["TrafficMirrorFilterRules"]

            egress_rules = self.provider_instance.aws_clients.ec2_client.describe_traffic_mirror_filter_rules(
                Filters=[{"Name": "traffic-mirror-filter-id",
                          "Values": [tm_filter_id]}],
                Direction="egress"
            )["TrafficMirrorFilterRules"]

            # Combine ingress and egress rules
            rules = ingress_rules + egress_rules

            for rule in rules:
                rule_id = rule["TrafficMirrorFilterRuleId"]
                logger.debug(
                    f"Processing EC2 Traffic Mirror Filter Rule: {rule_id} for Filter: {tm_filter_id}")

                attributes = {
                    "id": rule_id,
                    "traffic_mirror_filter_id": tm_filter_id,
                    "direction": rule["Direction"],
                    "action": rule["Action"],
                    "protocol": rule["Protocol"],
                    "source_cidr_block": rule["SourceCidrBlock"],
                    "destination_cidr_block": rule["DestinationCidrBlock"],
                    "rule_action": rule["RuleAction"],
                    "rule_number": rule["RuleNumber"],
                }
                self.hcl.process_resource(
                    "aws_ec2_traffic_mirror_filter_rule", rule_id.replace("-", "_"), attributes)

    def aws_ec2_traffic_mirror_session(self):
        logger.debug("Processing EC2 Traffic Mirror Sessions...")
        traffic_mirror_sessions = self.provider_instance.aws_clients.ec2_client.describe_traffic_mirror_sessions()[
            "TrafficMirrorSessions"]

        for tm_session in traffic_mirror_sessions:
            tm_session_id = tm_session["TrafficMirrorSessionId"]
            logger.debug(
                f"Processing EC2 Traffic Mirror Session: {tm_session_id}")

            attributes = {
                "id": tm_session_id,
                "traffic_mirror_target_id": tm_session["TrafficMirrorTargetId"],
                "traffic_mirror_filter_id": tm_session["TrafficMirrorFilterId"],
                "network_interface_id": tm_session["NetworkInterfaceId"],
                "session_number": tm_session["SessionNumber"],
                "virtual_network_id": tm_session.get("VirtualNetworkId", ""),
                "description": tm_session.get("Description", ""),
            }
            self.hcl.process_resource(
                "aws_ec2_traffic_mirror_session", tm_session_id.replace("-", "_"), attributes)

    def aws_ec2_traffic_mirror_target(self):
        logger.debug("Processing EC2 Traffic Mirror Targets...")
        traffic_mirror_targets = self.provider_instance.aws_clients.ec2_client.describe_traffic_mirror_targets()[
            "TrafficMirrorTargets"]

        for tm_target in traffic_mirror_targets:
            tm_target_id = tm_target["TrafficMirrorTargetId"]
            logger.debug(
                f"Processing EC2 Traffic Mirror Target: {tm_target_id}")

            attributes = {
                "id": tm_target_id,
                "description": tm_target.get("Description", ""),
                "network_load_balancer_arn": tm_target.get("NetworkLoadBalancerArn", ""),
                "network_interface_id": tm_target.get("NetworkInterfaceId", ""),
            }
            self.hcl.process_resource(
                "aws_ec2_traffic_mirror_target", tm_target_id.replace("-", "_"), attributes)

    def aws_egress_only_internet_gateway(self):
        logger.debug("Processing Egress Only Internet Gateways...")
        egress_only_igws = self.provider_instance.aws_clients.ec2_client.describe_egress_only_internet_gateways()[
            "EgressOnlyInternetGateways"]

        for egress_only_igw in egress_only_igws:
            egress_only_igw_id = egress_only_igw["EgressOnlyInternetGatewayId"]
            logger.debug(
                f"Processing Egress Only Internet Gateway: {egress_only_igw_id}")

            # Assuming there is only one attachment per egress-only internet gateway
            vpc_id = egress_only_igw["Attachments"][0]["VpcId"] if egress_only_igw["Attachments"] else ""

            attributes = {
                "id": egress_only_igw_id,
                "vpc_id": vpc_id,
            }
            self.hcl.process_resource(
                "aws_egress_only_internet_gateway", egress_only_igw_id.replace("-", "_"), attributes)

    def aws_flow_log(self, vpc_id, ftstack):
        logger.debug("Processing Flow Logs...")
        flow_logs = self.provider_instance.aws_clients.ec2_client.describe_flow_logs()[
            "FlowLogs"]

        for flow_log in flow_logs:
            # Filter out flow_logs not associated with the vpc_id
            if flow_log["ResourceId"] == vpc_id:
                flow_log_id = flow_log["FlowLogId"]
                logger.debug(f"Processing Flow Log: {flow_log_id}")

                attributes = {
                    "id": flow_log_id,
                    "resource_id": flow_log["ResourceId"],
                    "traffic_type": flow_log.get("TrafficType", ""),
                    "log_destination_type": flow_log.get("LogDestinationType", ""),
                    "log_destination": flow_log.get("LogDestination", ""),
                    "log_group_name": flow_log.get("LogGroupName", ""),
                    "iam_role_arn": flow_log.get("DeliverLogsPermissionArn", ""),
                    "max_aggregation_interval": flow_log.get("MaxAggregationInterval", ""),
                }
                self.hcl.process_resource(
                    "aws_flow_log", flow_log_id.replace("-", "_"), attributes)
                # Check if the log destination type is 'cloudwatch-logs'
                if attributes["log_destination_type"] == "cloud-watch-logs":
                    # If so, process a CloudWatch Log Group
                    self.logs_instance.aws_cloudwatch_log_group(
                        attributes["log_group_name"], ftstack)
                    # self.aws_cloudwatch_log_group(attributes["log_group_name"])

                # If IAM role ARN is provided, process the IAM role
                if attributes["iam_role_arn"]:
                    # Assuming the role ARN ends with the role name
                    role_name = attributes["iam_role_arn"].split('/')[-1]
                    self.iam_role_instance.aws_iam_role(role_name, ftstack)
                    # self.aws_iam_role(role_name)

                if attributes["log_destination_type"] == "s3":
                    # If so, process a S3 bucket
                    bucket_name = attributes["log_destination"].split(':')[-1]
                    self.s3_instance.aws_s3_bucket(bucket_name, ftstack)

    def aws_cloudwatch_log_group(self, log_group_name):
        logger.debug(f"Processing CloudWatch Log Group: {log_group_name}...")

        paginator = self.provider_instance.aws_clients.logs_client.get_paginator(
            "describe_log_groups")
        for page in paginator.paginate(logGroupNamePrefix=log_group_name):
            for log_group in page["logGroups"]:
                if log_group["logGroupName"] == log_group_name:
                    logger.debug(
                        f"Processing CloudWatch Log Group: {log_group_name}")

                    attributes = {
                        "id": log_group_name,
                        "name": log_group_name,
                    }

                    self.hcl.process_resource(
                        "aws_cloudwatch_log_group", log_group_name.replace("-", "_"), attributes)
                    return

        logger.debug(f"  Log group: {log_group_name} does not exist.")

    def aws_internet_gateway_attachment(self):
        logger.debug("Processing Internet Gateway Attachments...")
        internet_gateways = self.provider_instance.aws_clients.ec2_client.describe_internet_gateways()[
            "InternetGateways"]

        for igw in internet_gateways:
            igw_id = igw["InternetGatewayId"]

            for attachment in igw["Attachments"]:
                vpc_id = attachment["VpcId"]
                logger.debug(
                    f"Processing Internet Gateway Attachment: {igw_id} <-> {vpc_id}")

                attributes = {
                    "id": f"{igw_id}:{vpc_id}",
                    "internet_gateway_id": igw_id,
                    "vpc_id": vpc_id,
                }
                self.hcl.process_resource(
                    "aws_internet_gateway_attachment", f"{igw_id.replace('-', '_')}-{vpc_id.replace('-', '_')}", attributes)

    def aws_main_route_table_association(self):
        logger.debug("Processing Main Route Table Associations...")
        route_tables = self.provider_instance.aws_clients.ec2_client.describe_route_tables()[
            "RouteTables"]

        for rt in route_tables:
            rt_id = rt["RouteTableId"]
            vpc_id = rt["VpcId"]

            for assoc in rt["Associations"]:
                if assoc["Main"]:
                    assoc_id = assoc["RouteTableAssociationId"]
                    logger.debug(
                        f"Processing Main Route Table Association: {assoc_id} for VPC: {vpc_id}")

                    attributes = {
                        "id": assoc_id,
                        "vpc_id": vpc_id,
                        "route_table_id": rt_id,
                    }
                    self.hcl.process_resource(
                        "aws_main_route_table_association", assoc_id.replace("-", "_"), attributes)

    def aws_nat_gateway(self, vpc_id):
        logger.debug(f"Processing NAT Gateways for VPC: {vpc_id}")

        # Describe all subnets for the given VPC
        subnets = self.provider_instance.aws_clients.ec2_client.describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Subnets']

        # Process NAT gateways for each subnet
        for subnet in subnets:
            subnet_id = subnet['SubnetId']
            nat_gateways = self.provider_instance.aws_clients.ec2_client.describe_nat_gateways(
                Filters=[{'Name': 'subnet-id', 'Values': [subnet_id]}])["NatGateways"]

            # Sort the NAT gateways by CreateTime
            nat_gateways = sorted(
                nat_gateways, key=lambda ng: ng['CreateTime'])

            for nat_gw in nat_gateways:
                nat_gw_id = nat_gw["NatGatewayId"]
                nat_gw_state = nat_gw["State"]

                if nat_gw_state == "available":  # Add this condition
                    logger.debug(f"Processing NAT Gateway: {nat_gw_id}")

                    attributes = {
                        "id": nat_gw_id,
                        "subnet_id": nat_gw["SubnetId"],
                        "allocation_id": nat_gw["NatGatewayAddresses"][0]["AllocationId"],
                        "network_interface_id": nat_gw["NatGatewayAddresses"][0]["NetworkInterfaceId"],
                        "private_ip": nat_gw["NatGatewayAddresses"][0]["PrivateIp"],
                        "public_ip": nat_gw["NatGatewayAddresses"][0]["PublicIp"],
                    }

                    self.hcl.process_resource(
                        "aws_nat_gateway", nat_gw_id.replace("-", "_"), attributes)

                    # Process associated EIPs
                    for address in nat_gw["NatGatewayAddresses"]:
                        self.aws_eip(address["AllocationId"])

                    route_tables = self.provider_instance.aws_clients.ec2_client.describe_route_tables()[
                        "RouteTables"]

                    for rt in route_tables:
                        for route in rt["Routes"]:
                            # match the NatGatewayId
                            if route.get("NatGatewayId", "") == nat_gw_id:
                                # pass the route_table_id and the route
                                self.aws_route(rt["RouteTableId"], route)

                    subnet_cidr = self.provider_instance.aws_clients.ec2_client.describe_subnets(
                        SubnetIds=[nat_gw["SubnetId"]])['Subnets'][0]['CidrBlock']
                    if subnet_cidr:
                        self.hcl.add_additional_data(
                            "aws_nat_gateway", nat_gw_id, "subnet_cidr", subnet_cidr)

    def aws_eip(self, allocation_id):
        logger.debug(
            f"Processing Elastic IPs associated with NAT Gateway: {allocation_id}")

        eip = self.provider_instance.aws_clients.ec2_client.describe_addresses(
            AllocationIds=[allocation_id])["Addresses"][0]
        logger.debug(f"Processing Elastic IP: {allocation_id}")

        attributes = {
            "id": allocation_id,
            "public_ip": eip["PublicIp"],
        }

        if "InstanceId" in eip:
            attributes["instance"] = eip["InstanceId"]

        if "PrivateIpAddress" in eip:
            attributes["private_ip"] = eip["PrivateIpAddress"]

        self.hcl.process_resource(
            "aws_eip", allocation_id.replace("-", "_"), attributes)

        # Get the natgateway using this EIP
        ngs = self.provider_instance.aws_clients.ec2_client.describe_nat_gateways()
        nat_gateway = None

        for ng in ngs["NatGateways"]:
            for address in ng["NatGatewayAddresses"]:
                if address["AllocationId"] == allocation_id:
                    nat_gateway = ng
                    break
        if nat_gateway:
            # Get the name from the tags
            nat_gateway_name = ""
            for tag in nat_gateway["Tags"]:
                if tag["Key"] == "Name":
                    nat_gateway_name = tag["Value"]
                    break
            if not nat_gateway_name:
                nat_gateway_name = nat_gateway["NatGatewayId"]
            self.hcl.add_additional_data(
                "aws_eip", allocation_id, "nat_gateway_name", nat_gateway_name)

    def aws_network_acl(self, vpc_id):
        logger.debug("Processing Network ACLs...")
        network_acls = self.provider_instance.aws_clients.ec2_client.describe_network_acls()[
            "NetworkAcls"]

        for network_acl in network_acls:
            if not network_acl["IsDefault"] and network_acl["VpcId"] == vpc_id:
                network_acl_id = network_acl["NetworkAclId"]
                logger.debug(
                    f"Processing Network ACL: {network_acl_id} for VPC: {vpc_id}")

                attributes = {
                    "id": network_acl_id,
                    "vpc_id": vpc_id,
                }
                self.hcl.process_resource(
                    "aws_network_acl", network_acl_id.replace("-", "_"), attributes)

                # call aws_network_acl_association with network_acl_id
                # self.aws_network_acl_association(network_acl_id)
                self.aws_network_acl_rule(network_acl_id)

    def aws_network_acl_association(self, network_acl_id):
        logger.debug("Processing Network ACL Associations...")
        network_acls = self.provider_instance.aws_clients.ec2_client.describe_network_acls()[
            "NetworkAcls"]

        for network_acl in network_acls:
            if network_acl["NetworkAclId"] == network_acl_id:
                for assoc in network_acl["Associations"]:
                    assoc_id = assoc["NetworkAclAssociationId"]
                    subnet_id = assoc["SubnetId"]
                    logger.debug(
                        f"Processing Network ACL Association: {assoc_id} for Subnet: {subnet_id}")

                    attributes = {
                        "id": assoc_id,
                        "network_acl_id": network_acl_id,
                        "subnet_id": subnet_id,
                    }
                    self.hcl.process_resource(
                        "aws_network_acl_association", assoc_id.replace("-", "_"), attributes)

                # call aws_network_acl_rule with network_acl_id

    def aws_network_acl_rule(self, network_acl_id):
        logger.debug("Processing Network ACL Rules...")
        network_acls = self.provider_instance.aws_clients.ec2_client.describe_network_acls()[
            "NetworkAcls"]

        for network_acl in network_acls:
            if network_acl["NetworkAclId"] == network_acl_id:
                for entry in network_acl["Entries"]:
                    rule_number = entry["RuleNumber"]
                    if rule_number == 32767:
                        continue
                    rule_action = entry["RuleAction"]
                    rule_egress = entry["Egress"]
                    logger.debug(
                        f"Processing Network ACL Rule: {rule_number} for Network ACL: {network_acl_id}")

                    attributes = {
                        "id": f"{network_acl_id}-{rule_number}",
                        "network_acl_id": network_acl_id,
                        "rule_number": rule_number,
                        "protocol": entry["Protocol"],
                        "rule_action": rule_action,
                        "egress": rule_egress,
                        "cidr_block": entry.get("CidrBlock", ""),
                        "ipv6_cidr_block": entry.get("Ipv6CidrBlock", ""),
                    }
                    type = "egress"
                    if not rule_egress:
                        type = "ingress"
                    self.hcl.process_resource(
                        "aws_network_acl_rule", f"{network_acl_id.replace('-', '_')}-{rule_number}-{type}", attributes)

    def aws_network_interface(self, network_interface_id):
        logger.debug(f"Processing Network Interface: {network_interface_id}")
        network_interfaces = self.provider_instance.aws_clients.ec2_client.describe_network_interfaces(NetworkInterfaceIds=[network_interface_id])[
            "NetworkInterfaces"]

        for network_interface in network_interfaces:
            eni_id = network_interface["NetworkInterfaceId"]
            subnet_id = network_interface["SubnetId"]
            description = network_interface.get("Description", "")
            private_ips = [private_ip["PrivateIpAddress"]
                           for private_ip in network_interface["PrivateIpAddresses"]]
            logger.debug(f"Processing Network Interface: {eni_id}")

            attributes = {
                "id": eni_id,
                "subnet_id": subnet_id,
                "description": description,
                "private_ips": private_ips,
            }

            self.hcl.process_resource(
                "aws_network_interface", eni_id.replace("-", "_"), attributes)

    def aws_network_interface_attachment(self, network_interfaces):
        logger.debug("Processing Network Interface Attachments...")

        for eni in network_interfaces:
            eni_id = eni["NetworkInterfaceId"]
            attachment = eni.get("Attachment")
            if attachment and "InstanceId" in attachment:
                attachment_id = attachment["AttachmentId"]
                instance_id = attachment["InstanceId"]
                device_index = attachment["DeviceIndex"]
                logger.debug(
                    f"Processing Network Interface Attachment: {attachment_id} for ENI: {eni_id}")

                attributes = {
                    "id": attachment_id,
                    "instance_id": instance_id,
                    "network_interface_id": eni_id,
                    "device_index": device_index,
                }
                self.hcl.process_resource(
                    "aws_network_interface_attachment", attachment_id.replace("-", "_"), attributes)

    def aws_network_interface_sg_attachment(self, network_interfaces):
        logger.debug(
            "Processing Network Interface Security Group Attachments...")

        for eni in network_interfaces:
            eni_id = eni["NetworkInterfaceId"]

            for sg in eni["Groups"]:
                sg_id = sg["GroupId"]
                logger.debug(
                    f"Processing Security Group Attachment for ENI: {eni_id} and SG: {sg_id}")

                attributes = {
                    "id": f"{eni_id}-{sg_id}",
                    "network_interface_id": eni_id,
                    "security_group_id": sg_id,
                }
                self.hcl.process_resource("aws_network_interface_sg_attachment",
                                          f"{eni_id.replace('-', '_')}-{sg_id.replace('-', '_')}", attributes)

    def aws_route_table(self, vpc_id):
        logger.debug("Processing Route Tables...")
        route_tables = self.provider_instance.aws_clients.ec2_client.describe_route_tables()[
            "RouteTables"]

        # Sort the route_tables list based on CreationTime
        route_tables.sort(key=lambda rt: rt.get('CreateTime', ''))

        for rt in route_tables:
            if rt['VpcId'] == vpc_id:
                # Ignore if it's the default route table
                associations = rt.get('Associations', [])
                if any(assoc.get('Main', False) for assoc in associations):
                    continue

                route_table_id = rt["RouteTableId"]
                logger.debug(
                    f"Processing Route Table: {route_table_id} for VPC: {vpc_id}")

                attributes = {
                    "id": route_table_id,
                    "vpc_id": vpc_id,
                }
                self.hcl.process_resource(
                    "aws_route_table", route_table_id.replace("-", "_"), attributes)

                # self.aws_route(route_table_id)  # pass the route_table_id

    def aws_route(self, route_table_id, route):
        # Describe the route table
        response = self.provider_instance.aws_clients.ec2_client.describe_route_tables(
            RouteTableIds=[route_table_id])

        # Check if it's the main route table
        is_main_route_table = any(assoc.get('Main', False) for rt in response.get(
            'RouteTables', []) for assoc in rt.get('Associations', []))

        if is_main_route_table:
            return

        destination = route.get("DestinationCidrBlock",
                                route.get("DestinationIpv6CidrBlock", ""))

        if not destination:
            return

        # Ignoring local route
        if route.get("GatewayId", "") == "local":
            return

        logger.debug(
            f"Processing Route in Route Table: {route_table_id} for destination: {destination}")

        id = f"{route_table_id.replace('-', '_')}-{destination.replace('/', '-')}"

        attributes = {
            "id": id,
            "route_table_id": route_table_id,
            "destination_cidr_block": route.get("DestinationCidrBlock", ""),
            "destination_ipv6_cidr_block": route.get("DestinationIpv6CidrBlock", ""),
            "gateway_id": route.get("GatewayId", ""),
            "nat_gateway_id": route.get("NatGatewayId", ""),
            "instance_id": route.get("InstanceId", ""),
            "egress_only_gateway_id": route.get("EgressOnlyInternetGatewayId", ""),
            "transit_gateway_id": route.get("TransitGatewayId", ""),
            "local_gateway_id": route.get("LocalGatewayId", ""),
        }

        self.hcl.process_resource(
            "aws_route", id, attributes)

        tags = response['RouteTables'][0].get('Tags', [])
        route_table_name = ""
        for tag in tags:
            if tag['Key'] == 'Name':
                route_table_name = tag['Value']
                break
        if route_table_name:
            self.hcl.add_additional_data(
                "aws_route", id, "route_table_name", route_table_name)

        # using boto3 describe the nat_gateway_id and get the name
        if route.get("NatGatewayId", ""):
            nat_gateway_name = ""
            nat_gateway = self.provider_instance.aws_clients.ec2_client.describe_nat_gateways(
                NatGatewayIds=[route.get("NatGatewayId", "")])["NatGateways"][0]
            for tag in nat_gateway.get('Tags', []):
                if tag['Key'] == 'Name':
                    nat_gateway_name = tag['Value']
                    break
            if nat_gateway_name:
                self.hcl.add_additional_data(
                    "aws_route", id, "nat_gateway_name", nat_gateway_name)

    def aws_route_table_association(self, subnet_id):
        logger.debug("Processing Route Table Associations...")
        route_tables = self.provider_instance.aws_clients.ec2_client.describe_route_tables()[
            "RouteTables"]

        for rt in route_tables:
            # Check if this is a default route table
            if any(assoc.get("Main") for assoc in rt["Associations"]):
                continue  # Skip this route table if it's the default one

            route_table_id = rt["RouteTableId"]

            for assoc in rt["Associations"]:
                # check the subnet_id and ensure this isn't a main association
                if not assoc.get("Main") and assoc["SubnetId"] == subnet_id:
                    assoc_id = assoc["RouteTableAssociationId"]
                    logger.debug(
                        f"Processing Route Table Association: {assoc_id} for Route Table: {route_table_id}")

                    attributes = {
                        "id": assoc_id,
                        "route_table_id": route_table_id,
                        "subnet_id": subnet_id,
                    }
                    self.hcl.process_resource(
                        "aws_route_table_association", assoc_id.replace("-", "_"), attributes)

                    # get the Name tag for the route table
                    route_table_name = ""
                    for tag in rt['Tags']:
                        if tag['Key'] == 'Name':
                            route_table_name = tag['Value']
                            break
                    if route_table_name:
                        self.hcl.add_additional_data(
                            "aws_route_table_association", assoc_id, "route_table_name", route_table_name)
                    # get the cidr for the subnet_id
                    subnet_cidr = self.provider_instance.aws_clients.ec2_client.describe_subnets(
                        SubnetIds=[subnet_id])['Subnets'][0]['CidrBlock']
                    if subnet_cidr:
                        self.hcl.add_additional_data(
                            "aws_route_table_association", assoc_id, "subnet_cidr", subnet_cidr)

    def aws_security_group(self):
        logger.debug("Processing Security Groups...")
        security_groups = self.provider_instance.aws_clients.ec2_client.describe_security_groups()[
            "SecurityGroups"]

        for sg in security_groups:
            sg_id = sg["GroupId"]
            vpc_id = sg["VpcId"]
            tags = sg.get("Tags", [])

            # Skip Elastic Beanstalk security groups
            if any(tag['Key'].startswith("elasticbeanstalk:") for tag in tags):
                logger.debug(
                    f"  Skipping Elastic Beanstalk Security Group: {sg_id} for VPC: {vpc_id}")
                continue

            logger.debug(
                f"Processing Security Group: {sg_id} for VPC: {vpc_id}")

            attributes = {
                "id": sg_id,
                "vpc_id": vpc_id,
                "name": sg.get("GroupName", ""),
                "description": sg.get("Description", ""),
            }
            self.hcl.process_resource(
                "aws_security_group", sg_id.replace("-", "_"), attributes)

    def aws_vpc_dhcp_options(self, dhcp_options_id):
        logger.debug("Processing VPC DHCP Options...")
        dhcp_options = self.provider_instance.aws_clients.ec2_client.describe_dhcp_options(
            DhcpOptionsIds=[dhcp_options_id])["DhcpOptions"][0]

        logger.debug(f"Processing VPC DHCP Options: {dhcp_options_id}")

        attributes = {
            "id": dhcp_options_id,
            "tags": {tag["Key"]: tag["Value"] for tag in dhcp_options.get("Tags", [])},
        }
        for config in dhcp_options["DhcpConfigurations"]:
            key = config["Key"]
            values = [value["Value"] for value in config["Values"]]
            attributes[key.lower()] = values

        self.hcl.process_resource(
            "aws_vpc_dhcp_options", dhcp_options_id.replace("-", "_"), attributes)

    def aws_vpc_dhcp_options_association(self, vpc_id):
        logger.debug("Processing VPC DHCP Options Associations...")
        vpc = self.provider_instance.aws_clients.ec2_client.describe_vpcs(VpcIds=[vpc_id])[
            "Vpcs"][0]
        dhcp_options_id = vpc["DhcpOptionsId"]
        if dhcp_options_id != "default":
            logger.debug(
                f"Processing VPC DHCP Options Association: {dhcp_options_id} for VPC: {vpc_id}")

            assoc_id = f"{dhcp_options_id}-{vpc_id}"
            attributes = {
                "id": assoc_id,
                "vpc_id": vpc_id,
                "dhcp_options_id": dhcp_options_id,
            }
            self.hcl.process_resource(
                "aws_vpc_dhcp_options_association", assoc_id.replace("-", "_"), attributes)

            # Get the DHCP options details
            dhcp_options = self.provider_instance.aws_clients.ec2_client.describe_dhcp_options(
                DhcpOptionsIds=[dhcp_options_id])
            for option in dhcp_options['DhcpOptions']:
                for config in option['DhcpConfigurations']:
                    if config['Key'] == 'domain-name':
                        # save the domain name
                        self.dhcp_options_domain_name[assoc_id] = config['Values'][0]['Value']
                        break

            self.aws_vpc_dhcp_options(dhcp_options_id)

    def aws_vpc_endpoint(self):
        logger.debug("Processing VPC Endpoints...")
        vpc_endpoints = self.provider_instance.aws_clients.ec2_client.describe_vpc_endpoints()[
            "VpcEndpoints"]

        for endpoint in vpc_endpoints:
            endpoint_id = endpoint["VpcEndpointId"]
            vpc_id = endpoint["VpcId"]
            service_name = endpoint["ServiceName"]
            logger.debug(
                f"Processing VPC Endpoint: {endpoint_id} for VPC: {vpc_id}")
            attributes = {
                "id": endpoint_id,
                "vpc_id": vpc_id,
                "service_name": service_name,
                "vpc_endpoint_type": endpoint["VpcEndpointType"],
                "private_dns_enabled": endpoint["PrivateDnsEnabled"],
                "subnet_ids": endpoint.get("SubnetIds", []),
                "policy": endpoint["PolicyDocument"],
            }
            self.hcl.process_resource(
                "aws_vpc_endpoint", endpoint_id.replace("-", "_"), attributes)

    def aws_vpc_endpoint_connection_accepter(self):
        logger.debug("Processing VPC Endpoint Connection Accepters...")
        vpc_endpoints = self.provider_instance.aws_clients.ec2_client.describe_vpc_endpoints()[
            "VpcEndpoints"]

        for endpoint in vpc_endpoints:
            if endpoint["State"] == "pendingAcceptance":
                endpoint_id = endpoint["VpcEndpointId"]
                vpc_id = endpoint["VpcId"]
                service_name = endpoint["ServiceName"]
                logger.debug(
                    f"Processing VPC Endpoint Connection Accepter: {endpoint_id} for VPC: {vpc_id}")

                accepter_id = f"{vpc_id}-{endpoint_id}"
                attributes = {
                    "id": accepter_id,
                    "vpc_endpoint_id": endpoint_id,
                    "vpc_id": vpc_id,
                    "service_name": service_name,
                }
                self.hcl.process_resource(
                    "aws_vpc_endpoint_connection_accepter", accepter_id.replace("-", "_"), attributes)

    def aws_vpc_endpoint_connection_notification(self):
        logger.debug("Processing VPC Endpoint Connection Notifications...")
        connection_notifications = self.provider_instance.aws_clients.ec2_client.describe_vpc_endpoint_connection_notifications()[
            "ConnectionNotificationSet"]

        for notification in connection_notifications:
            notification_id = notification["ConnectionNotificationId"]
            vpc_endpoint_id = notification["VpcEndpointId"]
            service_id = notification["ServiceId"]
            sns_topic_arn = notification["ConnectionNotificationArn"]
            logger.debug(
                f"Processing VPC Endpoint Connection Notification: {notification_id}")

            attributes = {
                "id": notification_id,
                "vpc_endpoint_id": vpc_endpoint_id,
                "service_id": service_id,
                "sns_topic_arn": sns_topic_arn,
                "notification_type": notification["ConnectionNotificationType"],
                "state": notification["ConnectionNotificationState"],
            }
            self.hcl.process_resource(
                "aws_vpc_endpoint_connection_notification", notification_id.replace("-", "_"), attributes)

    def aws_vpc_endpoint_policy(self):
        logger.debug("Processing VPC Endpoint Policies...")
        vpc_endpoints = self.provider_instance.aws_clients.ec2_client.describe_vpc_endpoints()[
            "VpcEndpoints"]

        for endpoint in vpc_endpoints:
            endpoint_id = endpoint["VpcEndpointId"]
            vpc_id = endpoint["VpcId"]
            service_name = endpoint["ServiceName"]
            policy_document = endpoint["PolicyDocument"]
            logger.debug(
                f"Processing VPC Endpoint Policy: {endpoint_id} for VPC: {vpc_id}")

            attributes = {
                "id": endpoint_id,
                "vpc_endpoint_id": endpoint_id,
                "policy": policy_document,
            }
            self.hcl.process_resource(
                "aws_vpc_endpoint_policy", endpoint_id.replace("-", "_"), attributes)

    def aws_vpc_endpoint_route_table_association(self):
        logger.debug("Processing VPC Endpoint Route Table Associations...")
        vpc_endpoints = self.provider_instance.aws_clients.ec2_client.describe_vpc_endpoints()[
            "VpcEndpoints"]

        for endpoint in vpc_endpoints:
            endpoint_id = endpoint["VpcEndpointId"]
            route_table_ids = endpoint.get("RouteTableIds", [])

            for route_table_id in route_table_ids:
                logger.debug(
                    f"Processing VPC Endpoint Route Table Association: {endpoint_id} - {route_table_id}")

                assoc_id = f"{endpoint_id}-{route_table_id}"
                attributes = {
                    "id": assoc_id,
                    "vpc_endpoint_id": endpoint_id,
                    "route_table_id": route_table_id,
                }
                self.hcl.process_resource(
                    "aws_vpc_endpoint_route_table_association", assoc_id.replace("-", "_"), attributes)

    def aws_vpc_endpoint_security_group_association(self):
        logger.debug("Processing VPC Endpoint Security Group Associations...")
        vpc_endpoints = self.provider_instance.aws_clients.ec2_client.describe_vpc_endpoints()[
            "VpcEndpoints"]

        for endpoint in vpc_endpoints:
            endpoint_id = endpoint["VpcEndpointId"]
            security_group_ids = [group["GroupId"]
                                  for group in endpoint.get("Groups", [])]

            for security_group_id in security_group_ids:
                logger.debug(
                    f"Processing VPC Endpoint Security Group Association: {endpoint_id} - {security_group_id}")

                assoc_id = f"{endpoint_id}-{security_group_id}"
                attributes = {
                    "id": assoc_id,
                    "vpc_endpoint_id": endpoint_id,
                    "security_group_id": security_group_id,
                }
                self.hcl.process_resource(
                    "aws_vpc_endpoint_security_group_association", assoc_id.replace("-", "_"), attributes)

    def aws_vpc_endpoint_service(self):
        logger.debug("Processing VPC Endpoint Services...")
        vpc_endpoint_services = self.provider_instance.aws_clients.ec2_client.describe_vpc_endpoint_services()[
            "ServiceDetails"]

        for service in vpc_endpoint_services:
            service_id = service["ServiceId"]
            service_name = service["ServiceName"]

            # Skip default AWS services
            if service_name.startswith('com.amazonaws') or service_name.startswith('aws.'):
                continue

            logger.debug(
                f"Processing VPC Endpoint Service: {service_id} {service_name}")

            attributes = {
                "id": service_id,
                "service_name": service_name,
                "acceptance_required": service["AcceptanceRequired"],
                "availability_zones": service["AvailabilityZones"],
                "base_endpoint_dns_names": service["BaseEndpointDnsNames"],
                "service_type": service["ServiceType"][0]["ServiceType"],
            }
            self.hcl.process_resource(
                "aws_vpc_endpoint_service", service_id.replace("-", "_"), attributes)

    def aws_vpc_endpoint_service_allowed_principal(self):
        logger.debug("Processing VPC Endpoint Service Allowed Principals...")
        vpc_endpoint_services = self.provider_instance.aws_clients.ec2_client.describe_vpc_endpoint_service_configurations()[
            "ServiceConfigurations"]

        for service in vpc_endpoint_services:
            service_id = service["ServiceId"]
            allowed_principals = service.get("AllowedPrincipals", [])

            for principal in allowed_principals:
                logger.debug(
                    f"Processing VPC Endpoint Service Allowed Principal: {principal} for Service: {service_id}")

                assoc_id = f"{service_id}-{principal}"
                attributes = {
                    "id": assoc_id,
                    "vpc_endpoint_service_id": service_id,
                    "principal_arn": principal,
                }
                self.hcl.process_resource(
                    "aws_vpc_endpoint_service_allowed_principal", assoc_id.replace("-", "_"), attributes)

    def aws_vpc_endpoint_subnet_association(self):
        logger.debug("Processing VPC Endpoint Subnet Associations...")
        vpc_endpoints = self.provider_instance.aws_clients.ec2_client.describe_vpc_endpoints()[
            "VpcEndpoints"]

        for endpoint in vpc_endpoints:
            endpoint_id = endpoint["VpcEndpointId"]
            subnet_ids = endpoint["SubnetIds"]

            for subnet_id in subnet_ids:
                logger.debug(
                    f"Processing VPC Endpoint Subnet Association: {endpoint_id} - {subnet_id}")

                assoc_id = f"{endpoint_id}-{subnet_id}"
                attributes = {
                    "id": assoc_id,
                    "vpc_endpoint_id": endpoint_id,
                    "subnet_id": subnet_id,
                }
                self.hcl.process_resource(
                    "aws_vpc_endpoint_subnet_association", assoc_id.replace("-", "_"), attributes)

    def aws_vpc_ipv4_cidr_block_association(self):
        logger.debug("Processing VPC IPv4 CIDR Block Associations...")
        vpcs = self.provider_instance.aws_clients.ec2_client.describe_vpcs()["Vpcs"]

        for vpc in vpcs:
            vpc_id = vpc["VpcId"]
            cidr_blocks = vpc["CidrBlockAssociationSet"]

            for cidr_block in cidr_blocks:
                assoc_id = cidr_block["AssociationId"]
                logger.debug(
                    f"Processing VPC IPv4 CIDR Block Association: {assoc_id} for VPC: {vpc_id}")

                attributes = {
                    "id": assoc_id,
                    "vpc_id": vpc_id,
                    "cidr_block": cidr_block["CidrBlock"],
                }
                self.hcl.process_resource(
                    "aws_vpc_ipv4_cidr_block_association", assoc_id.replace("-", "_"), attributes)

    def aws_vpc_ipv6_cidr_block_association(self):
        logger.debug("Processing VPC IPv6 CIDR Block Associations...")
        vpcs = self.provider_instance.aws_clients.ec2_client.describe_vpcs()["Vpcs"]

        for vpc in vpcs:
            vpc_id = vpc["VpcId"]
            ipv6_cidr_blocks = vpc.get("Ipv6CidrBlockAssociationSet", [])

            for ipv6_cidr_block in ipv6_cidr_blocks:
                assoc_id = ipv6_cidr_block["AssociationId"]
                logger.debug(
                    f"Processing VPC IPv6 CIDR Block Association: {assoc_id} for VPC: {vpc_id}")

                attributes = {
                    "id": assoc_id,
                    "vpc_id": vpc_id,
                    "ipv6_cidr_block": ipv6_cidr_block["Ipv6CidrBlock"],
                }

                if "Ipv6Pool" in ipv6_cidr_block:
                    attributes["ipv6_ipam_pool_id"] = ipv6_cidr_block["Ipv6Pool"]

                self.hcl.process_resource(
                    "aws_vpc_ipv6_cidr_block_association", assoc_id.replace("-", "_"), attributes)

    def aws_vpc_peering_connection(self):
        logger.debug("Processing VPC Peering Connections...")
        vpc_peering_connections = self.provider_instance.aws_clients.ec2_client.describe_vpc_peering_connections()[
            "VpcPeeringConnections"]

        for peering_connection in vpc_peering_connections:
            peering_connection_id = peering_connection["VpcPeeringConnectionId"]
            logger.debug(
                f"Processing VPC Peering Connection: {peering_connection_id}")

            attributes = {
                "id": peering_connection_id,
                "vpc_id": peering_connection["RequesterVpcInfo"]["VpcId"],
                "peer_vpc_id": peering_connection["AccepterVpcInfo"]["VpcId"],
                "peer_owner_id": peering_connection["AccepterVpcInfo"]["OwnerId"],
                "peer_region": peering_connection["AccepterVpcInfo"]["Region"],
            }
            self.hcl.process_resource(
                "aws_vpc_peering_connection", peering_connection_id.replace("-", "_"), attributes)

    def aws_vpc_peering_connection_accepter(self):
        logger.debug("Processing VPC Peering Connection Accepters...")
        vpc_peering_connections = self.provider_instance.aws_clients.ec2_client.describe_vpc_peering_connections()[
            "VpcPeeringConnections"]

        for peering_connection in vpc_peering_connections:
            peering_connection_id = peering_connection["VpcPeeringConnectionId"]
            if peering_connection["Status"]["Code"] != "active":
                continue

            logger.debug(
                f"Processing VPC Peering Connection Accepter: {peering_connection_id}")

            attributes = {
                "id": peering_connection_id,
                "vpc_peering_connection_id": peering_connection_id,
                "auto_accept": True,
            }
            self.hcl.process_resource(
                "aws_vpc_peering_connection_accepter", peering_connection_id.replace("-", "_"), attributes)

    def aws_vpc_peering_connection_options(self):
        logger.debug("Processing VPC Peering Connection Options...")
        vpc_peering_connections = self.provider_instance.aws_clients.ec2_client.describe_vpc_peering_connections()[
            "VpcPeeringConnections"]

        for peering_connection in vpc_peering_connections:
            peering_connection_id = peering_connection["VpcPeeringConnectionId"]
            logger.debug(
                f"Processing VPC Peering Connection Options: {peering_connection_id}")
            attributes = {
                "id": peering_connection_id,
                "vpc_peering_connection_id": peering_connection_id,
            }
            self.hcl.process_resource(
                "aws_vpc_peering_connection_options", peering_connection_id.replace("-", "_"), attributes)

    def aws_vpc_security_group_egress_rule(self):
        logger.debug("Processing VPC Security Group Egress Rules...")
        security_group_rules = self.provider_instance.aws_clients.ec2_client.describe_security_group_rules()[
            "SecurityGroupRules"]

        for rule in security_group_rules:
            rule_id = rule["SecurityGroupRuleId"]
            is_egress = rule["IsEgress"]
            if is_egress:
                attributes = {
                    "id": rule_id,
                }
                self.hcl.process_resource(
                    "aws_vpc_security_group_egress_rule", rule_id.replace("-", "_"), attributes)

    def aws_vpc_security_group_ingress_rule(self):
        logger.debug("Processing VPC Security Group Ingress Rules...")
        security_group_rules = self.provider_instance.aws_clients.ec2_client.describe_security_group_rules()[
            "SecurityGroupRules"]

        for rule in security_group_rules:
            rule_id = rule["SecurityGroupRuleId"]
            is_egress = rule["IsEgress"]
            if not is_egress:
                attributes = {
                    "id": rule_id,
                }
                self.hcl.process_resource(
                    "aws_vpc_security_group_ingress_rule", rule_id.replace("-", "_"), attributes)
