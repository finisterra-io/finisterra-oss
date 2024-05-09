from ...utils.hcl import HCL
import logging
import inspect

logger = logging.getLogger('finisterra')


class Cloudmap:
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

    def get_vpc_name(self, vpc_id):
        response = self.provider_instance.aws_clients.ec2_client.describe_vpcs(VpcIds=[
                                                                               vpc_id])

        if not response or 'Vpcs' not in response or not response['Vpcs']:
            # Handle this case as required, for example:
            logger.debug(f"No VPC information found for VPC ID: {vpc_id}")
            return None

        vpc_tags = response['Vpcs'][0].get('Tags', [])
        vpc_name = next((tag['Value']
                        for tag in vpc_tags if tag['Key'] == 'Name'), None)

        if vpc_name is None:
            logger.debug(f"No 'Name' tag found for VPC ID: {vpc_id}")

        return vpc_name

    def cloudmap(self):
        self.hcl.prepare_folder()

        self.aws_service_discovery_private_dns_namespace()
        # self.aws_service_discovery_public_dns_namespace()
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

    def aws_service_discovery_http_namespace(self):
        # logger.debug(f"Processing AWS Service Discovery HTTP Namespaces...")

        paginator = self.provider_instance.aws_clients.cloudmap_client.get_paginator(
            "list_namespaces")
        for page in paginator.paginate():
            for namespace in page["Namespaces"]:
                if namespace["Type"] == "HTTP":
                    namespace_id = namespace["Id"]
                    http_namespace = self.provider_instance.aws_clients.cloudmap_client.get_namespace(Id=namespace_id)[
                        "Namespace"]
                    logger.debug(
                        f"Processing AWS Service Discovery HTTP Namespace: {namespace_id}")

                    attributes = {
                        "id": namespace_id,
                        "name": http_namespace["Name"],
                        "arn": http_namespace["Arn"],
                    }

                    self.hcl.process_resource(
                        "aws_service_discovery_http_namespace", namespace_id.replace("-", "_"), attributes)

    def aws_service_discovery_instance(self):
        logger.debug(f"Processing AWS Service Discovery Instances...")

        paginator = self.provider_instance.aws_clients.cloudmap_client.get_paginator(
            "list_services")
        for page in paginator.paginate():
            for service in page["Services"]:
                service_id = service["Id"]
                instance_paginator = self.provider_instance.aws_clients.cloudmap_client.get_paginator(
                    "list_instances")
                for instance_page in instance_paginator.paginate(ServiceId=service_id):
                    for instance in instance_page["Instances"]:
                        instance_id = instance["Id"]
                        logger.debug(
                            f"Processing AWS Service Discovery Instance: {instance_id}")

                        attributes = {
                            "id": instance_id,
                            "instance_id": instance_id,
                            "service_id": service_id,
                        }

                        if "Attributes" in instance:
                            attributes["attributes"] = instance["Attributes"]

                        self.hcl.process_resource(
                            "aws_service_discovery_instance", instance_id.replace("-", "_"), attributes)

    def aws_service_discovery_private_dns_namespace(self):
        resource_type = "aws_service_discovery_private_dns_namespace"
        # logger.debug(f"Processing AWS Service Discovery Private DNS Namespaces...")

        paginator = self.provider_instance.aws_clients.cloudmap_client.get_paginator(
            "list_namespaces")
        total = 0
        for page in paginator.paginate():
            total += len(page["Namespaces"])

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for page in paginator.paginate():
            for namespace in page["Namespaces"]:
                namespace_id = namespace["Id"]
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{namespace_id}[/]")
                if namespace["Type"] == "DNS_PRIVATE":
                    private_dns_namespace = self.provider_instance.aws_clients.cloudmap_client.get_namespace(
                        Id=namespace_id)["Namespace"]
                    logger.debug(
                        f"Processing AWS Service Discovery Private DNS Namespace: {namespace_id}")

                    # Get the hosted zone ID of the namespace
                    hosted_zone_id = private_dns_namespace["Properties"]["DnsProperties"]["HostedZoneId"]

                    # Get the VPC ID from the hosted zone
                    hosted_zone = self.provider_instance.aws_clients.route53_client.get_hosted_zone(
                        Id=hosted_zone_id)
                    vpc_id = hosted_zone["VPCs"][0]["VPCId"]

                    id = namespace_id

                    ftstack = "cloudmap"
                    try:
                        response = self.provider_instance.aws_clients.cloudmap_client.list_tags_for_resource(
                            ResourceARN=private_dns_namespace["Arn"])
                        tags = response.get('Tags', [])
                        for tag in tags:
                            if tag['Key'] == 'ftstack':
                                if tag['Value'] != 'cloudmap':
                                    ftstack = "stack_"+tag['Value']
                                break
                    except Exception as e:
                        logger.error(f"Error occurred: {e}")

                    attributes = {
                        "id": namespace_id,
                        "name": private_dns_namespace["Name"],
                        "arn": private_dns_namespace["Arn"],
                        "vpc": vpc_id,
                    }

                    self.hcl.process_resource(
                        "aws_service_discovery_private_dns_namespace", namespace_id.replace("-", "_"), attributes)

                    self.aws_service_discovery_service(namespace_id)
                    self.hcl.add_stack(resource_type, id, ftstack)

                    vpc_name = self.get_vpc_name(vpc_id)
                    if vpc_name:
                        if resource_type not in self.hcl.additional_data:
                            self.hcl.additional_data[resource_type] = {}
                        if id not in self.hcl.additional_data[resource_type]:
                            self.hcl.additional_data[resource_type][id] = {}
                        self.hcl.additional_data[resource_type][id]["vpc_name"] = vpc_name

    def aws_service_discovery_public_dns_namespace(self):
        logger.debug(
            f"Processing AWS Service Discovery Public DNS Namespaces...")

        paginator = self.provider_instance.aws_clients.cloudmap_client.get_paginator(
            "list_namespaces")
        for page in paginator.paginate():
            for namespace in page["Namespaces"]:
                if namespace["Type"] == "DNS_PUBLIC":
                    namespace_id = namespace["Id"]
                    public_dns_namespace = self.provider_instance.aws_clients.cloudmap_client.get_namespace(Id=namespace_id)[
                        "Namespace"]
                    logger.debug(
                        f"Processing AWS Service Discovery Public DNS Namespace: {namespace_id}")

                    attributes = {
                        "id": namespace_id,
                        "name": public_dns_namespace["Name"],
                        "arn": public_dns_namespace["Arn"],
                    }

                    self.hcl.process_resource(
                        "aws_service_discovery_public_dns_namespace", namespace_id.replace("-", "_"), attributes)

    def aws_service_discovery_service(self, namespace_id):
        logger.debug(f"Processing AWS Service Discovery Services...")

        paginator = self.provider_instance.aws_clients.cloudmap_client.get_paginator(
            "list_services")
        for page in paginator.paginate(
            Filters=[
                {
                    'Name': 'NAMESPACE_ID',
                    'Values': [
                        namespace_id,
                    ],
                    'Condition': 'EQ'
                },
            ]
        ):
            for service in page["Services"]:
                service_id = service["Id"]
                sd_service = self.provider_instance.aws_clients.cloudmap_client.get_service(Id=service_id)[
                    "Service"]
                logger.debug(
                    f"Processing AWS Service Discovery Service: {service_id}")

                attributes = {
                    "id": service_id,
                }

                self.hcl.process_resource(
                    "aws_service_discovery_service", service_id.replace("-", "_"), attributes)
