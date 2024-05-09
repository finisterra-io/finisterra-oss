from ...utils.hcl import HCL
import json
import logging
import inspect
from ...providers.aws.utils import get_vpc_name, get_subnet_name
from ...providers.aws.iam_role import IAM
from ...providers.aws.security_group import SECURITY_GROUP
import ipaddress


logger = logging.getLogger('finisterra')


class ClientVPN:
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

        self.iam_role_instance = IAM(self.provider_instance, self.hcl)
        self.security_group_instance = SECURITY_GROUP(
            self.provider_instance, self.hcl)

    def client_vpn(self):
        self.hcl.prepare_folder()

        self.aws_ec2_client_vpn_endpoint()
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

    def aws_ec2_client_vpn_endpoint(self, vpn_endpoint_id=None, ftstack=None):
        resource_type = "aws_ec2_client_vpn_endpoint"
        logger.debug("Processing EC2 Client VPN Endpoints...")

        # If vpn_endpoint_id is provided, process only that specific Client VPN Endpoint
        if vpn_endpoint_id:
            if ftstack and self.hcl.id_resource_processed(resource_type, vpn_endpoint_id, ftstack):
                logger.debug(
                    f"Skipping EC2 Client VPN Endpoint: {vpn_endpoint_id} - already processed")
                return

            # Fetch and process the specific Client VPN Endpoint
            try:
                vpn_endpoint = self.provider_instance.aws_clients.ec2_client.describe_client_vpn_endpoints(
                    ClientVpnEndpointIds=[vpn_endpoint_id]
                )["ClientVpnEndpoints"][0]
                self.process_ec2_client_vpn_endpoint(vpn_endpoint, ftstack)
            except Exception as e:
                logger.debug(
                    f"Error fetching EC2 Client VPN Endpoint {vpn_endpoint_id}: {e}")
            return

        try:
            # Process all Client VPN Endpoints if no specific vpn_endpoint_id is provided
            paginator = self.provider_instance.aws_clients.ec2_client.get_paginator(
                "describe_client_vpn_endpoints")

            # Update to paginate with filters if available
            if self.provider_instance.filters:
                pages = paginator.paginate(
                    Filters=self.provider_instance.filters)
            else:
                pages = paginator.paginate()

            total = 0
            for page in pages:
                total += len(page["ClientVpnEndpoints"])
            if total > 0:
                self.task = self.provider_instance.progress.add_task(
                    f"[cyan]Processing {self.__class__.__name__}...", total=total)
            for page in pages:
                for vpn_endpoint in page["ClientVpnEndpoints"]:
                    self.provider_instance.progress.update(
                        self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{vpn_endpoint['ClientVpnEndpointId']}[/]")
                    self.process_ec2_client_vpn_endpoint(vpn_endpoint, ftstack)
        except Exception as e:
            # Catch-all for any other exceptions
            logger.error(f"Unexpected error: {e}")
            return

    def process_ec2_client_vpn_endpoint(self, vpn_endpoint, ftstack=None):
        resource_type = "aws_ec2_client_vpn_endpoint"
        vpn_endpoint_id = vpn_endpoint["ClientVpnEndpointId"]
        logger.debug(f"Processing EC2 Client VPN Endpoint: {vpn_endpoint_id}")
        id = vpn_endpoint_id

        attributes = {
            "id": id,
        }
        vpc_id = vpn_endpoint["VpcId"]
        vpc_name = get_vpc_name(self.provider_instance.aws_clients, vpc_id)
        if vpc_name:
            self.hcl.add_additional_data(
                resource_type, id, "vpc_name", vpc_name)
        self.hcl.process_resource(resource_type, id, attributes)
        if not ftstack:
            ftstack = "vpn"
        self.hcl.add_stack(resource_type, id, ftstack)

        self.aws_ec2_client_vpn_network_association(vpn_endpoint_id)
        self.aws_ec2_client_vpn_authorization_rule(vpn_endpoint_id)
        self.aws_ec2_client_vpn_route(
            vpn_endpoint_id, vpn_endpoint["ClientCidrBlock"])

        AuthenticationOptions = vpn_endpoint.get("AuthenticationOptions")
        for auth in AuthenticationOptions:
            FederatedAuthentication = auth.get("FederatedAuthentication")
            if FederatedAuthentication:
                SamlProviderArn = FederatedAuthentication.get(
                    "SamlProviderArn")
                if SamlProviderArn:
                    self.iam_role_instance.aws_iam_saml_provider(
                        SamlProviderArn, ftstack)

        security_groups = vpn_endpoint.get("SecurityGroupIds")
        for sg in security_groups:
            self.security_group_instance.aws_security_group(
                sg, ftstack)

    def aws_ec2_client_vpn_network_association(self, client_vpn_endpoint_id):
        logger.debug("Processing EC2 Client VPN Network Associations...")
        # Use describe_client_vpn_target_networks to get associations
        paginator = self.provider_instance.aws_clients.ec2_client.get_paginator(
            "describe_client_vpn_target_networks")

        for page in paginator.paginate(ClientVpnEndpointId=client_vpn_endpoint_id):
            for association in page["ClientVpnTargetNetworks"]:
                # Now using the AssociationId directly
                association_id = association["AssociationId"]
                target_subnet = association["TargetNetworkId"]
                logger.debug(
                    f"Processing EC2 Client VPN Network Association ID {association_id} for subnet {target_subnet} in VPN {client_vpn_endpoint_id}")

                attributes = {
                    "id": association_id,
                    "client_vpn_endpoint_id": client_vpn_endpoint_id,
                }
                subnet_name = get_subnet_name(
                    self.provider_instance.aws_clients, target_subnet)
                if subnet_name:
                    self.hcl.add_additional_data(
                        "aws_ec2_client_vpn_network_association", association_id, "subnet_name", subnet_name)

                self.hcl.process_resource(
                    "aws_ec2_client_vpn_network_association", association_id, attributes)

    def aws_ec2_client_vpn_authorization_rule(self, client_vpn_endpoint_id):
        logger.debug("Processing EC2 Client VPN Authorization Rules...")
        paginator = self.provider_instance.aws_clients.ec2_client.get_paginator(
            "describe_client_vpn_authorization_rules")

        for page in paginator.paginate(ClientVpnEndpointId=client_vpn_endpoint_id):
            for rule in page["AuthorizationRules"]:
                # Each rule is identified by its ClientVpnEndpointId and the target network CIDR
                # Along with a description of the rule itself
                logger.debug(
                    f"Processing Authorization Rule for CIDR {rule['DestinationCidr']} in VPN {client_vpn_endpoint_id}")

                # target_network_id = rule.get("TargetNetworkId")
                id = f"{client_vpn_endpoint_id},{rule['DestinationCidr']}"

                attributes = {
                    "id": id,
                    "client_vpn_endpoint_id": client_vpn_endpoint_id,
                }
                self.hcl.process_resource(
                    "aws_ec2_client_vpn_authorization_rule", id, attributes)

    def aws_ec2_client_vpn_route(self, client_vpn_endpoint_id, client_cidr_block):
        logger.debug("Processing EC2 Client VPN Routes...")
        # Use describe_client_vpn_routes to get routes associated with the client_vpn_endpoint_id
        paginator = self.provider_instance.aws_clients.ec2_client.get_paginator(
            "describe_client_vpn_routes")

        client_network = ipaddress.ip_network(client_cidr_block)

        for page in paginator.paginate(ClientVpnEndpointId=client_vpn_endpoint_id):
            for route in page["Routes"]:
                destination_network = ipaddress.ip_network(
                    route["DestinationCidr"])

                # Skip routes within the client VPN CIDR block
                if destination_network.overlaps(client_network):
                    logger.debug(
                        f"Skipping EC2 Client VPN Route for CIDR {route['DestinationCidr']} as it overlaps with the client CIDR block {client_cidr_block}")
                    continue

                # Use the RouteId directly if available; otherwise, create a composite identifier
                target_subnet = route.get("TargetSubnet")
                route_id = route.get(
                    "RouteId", f"{client_vpn_endpoint_id},{target_subnet},{route['DestinationCidr']}")
                logger.debug(
                    f"Processing EC2 Client VPN Route ID {route_id} for CIDR {route['DestinationCidr']} in VPN {client_vpn_endpoint_id}")

                attributes = {
                    "id": route_id,
                    "client_vpn_endpoint_id": client_vpn_endpoint_id,
                    "destination_cidr": route["DestinationCidr"],
                }

                subnet_name = get_subnet_name(
                    self.provider_instance.aws_clients, route["TargetSubnet"])
                if subnet_name:
                    self.hcl.add_additional_data(
                        "aws_ec2_client_vpn_route", route_id, "subnet_name", subnet_name)

                self.hcl.process_resource(
                    "aws_ec2_client_vpn_route", route_id, attributes)
