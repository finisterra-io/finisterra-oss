from ...utils.hcl import HCL
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.utils import get_subnet_names
import logging
import inspect

logger = logging.getLogger('finisterra')


class MSK:
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

        self.security_group_instance = SECURITY_GROUP(
            self.provider_instance, self.hcl)

    def get_vpc_id(self, sg_ids):
        if not sg_ids:
            return None

        # Get the first security group ID
        first_sg_id = sg_ids[0]

        # Describe the security group to get its VPC ID
        response = self.provider_instance.aws_clients.ec2_client.describe_security_groups(GroupIds=[
            first_sg_id])

        # Extract and return the VPC ID
        vpc_id = response["SecurityGroups"][0]["VpcId"]
        return vpc_id

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

    def msk(self):
        self.hcl.prepare_folder()

        self.aws_msk_cluster()
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

    def aws_msk_cluster(self):
        resource_type = "aws_msk_cluster"
        logger.debug("Processing MSK Clusters...")

        try:
            # Set up pagination for list_clusters
            paginator = self.provider_instance.aws_clients.msk_client.get_paginator(
                "list_clusters")
            page_iterator = paginator.paginate()

            total = 0
            for page in page_iterator:
                total += len(page["ClusterInfoList"])

            if total > 0:
                self.task = self.provider_instance.progress.add_task(
                    f"[cyan]Processing {self.__class__.__name__}...", total=total)

            for page in page_iterator:
                for cluster_info in page["ClusterInfoList"]:
                    cluster_arn = cluster_info["ClusterArn"]
                    cluster_name = cluster_info["ClusterName"]
                    self.provider_instance.progress.update(
                        self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{cluster_name}[/]")
                    logger.debug(f"Processing MSK Cluster: {cluster_name}")
                    id = cluster_arn

                    ftstack = "msk"
                    try:
                        tags_response = self.provider_instance.aws_clients.msk_client.list_tags_for_resource(
                            ResourceArn=cluster_arn)
                        tags = tags_response.get('Tags', {})
                        if tags.get('ftstack', 'msk') != 'msk':
                            ftstack = "stack_"+tags.get('ftstack', 'msk')
                    except Exception as e:
                        logger.error(f"Error occurred: {e}")

                    attributes = {
                        "id": id,
                        # "arn": cluster_arn,
                        # "name": cluster_name,
                    }

                    self.hcl.process_resource(
                        resource_type, id, attributes)
                    self.hcl.add_stack(resource_type, id, ftstack)

                    # Extracting the Security Group IDs for the MSK Cluster
                    cluster_details = self.provider_instance.aws_clients.msk_client.describe_cluster(
                        ClusterArn=cluster_arn
                    )

                    sg_ids = cluster_details["ClusterInfo"]["BrokerNodeGroupInfo"]["SecurityGroups"]

                    # Calling aws_security_group function with the extracted SG IDs
                    for sg in sg_ids:
                        self.security_group_instance.aws_security_group(
                            sg, ftstack)
                    vpc_id = self.get_vpc_id(sg_ids)
                    if vpc_id:
                        self.hcl.add_additional_data(
                            resource_type, id, "vpc_id", vpc_id)
                        vpc_name = self.get_vpc_name(vpc_id)
                        if vpc_name:
                            self.hcl.add_additional_data(
                                resource_type, id, "vpc_name", vpc_name)
                    subnet_ids = cluster_details["ClusterInfo"]["BrokerNodeGroupInfo"]["ClientSubnets"]
                    if subnet_ids:
                        subnet_names = get_subnet_names(
                            self.provider_instance.aws_clients, subnet_ids)
                        if subnet_names:
                            self.hcl.add_additional_data(
                                resource_type, id, "subnet_names", subnet_names)

                    self.aws_msk_configuration(cluster_arn)
                    # self.aws_msk_scram_secret_association(cluster_arn)
                    self.aws_appautoscaling_target(cluster_arn)
                    self.aws_appautoscaling_policy(cluster_arn)
        except Exception as e:
            # Handle other potential exceptions
            logger.error(
                f"Unexpected error occurred while processing MSK clusters: {e}")
            return

    def aws_msk_scram_secret_association(self, cluster_arn):
        logger.debug(
            f"Processing SCRAM Secret Associations for Cluster {cluster_arn}...")

        # Not all MSK methods might support pagination, so ensure this one does.
        secrets = self.provider_instance.aws_clients.msk_client.list_scram_secrets(
            ClusterArn=cluster_arn
        )

        for secret in secrets.get("SecretArnList", []):
            logger.debug(f"Processing SCRAM Secret: {secret}")

            attributes = {
                "id": secret,
                "arn": secret,
                "cluster_arn": cluster_arn,
                'get_vpc_name_msk': self.get_vpc_name_msk,
                'get_vpc_id_msk': self.get_vpc_id_msk,
            }

            self.hcl.process_resource(
                "aws_msk_scram_secret_association", secret, attributes)

    def aws_appautoscaling_target(self, cluster_arn):
        logger.debug(
            f"Processing AppAutoScaling Targets for MSK Cluster ARN {cluster_arn}...")

        paginator = self.provider_instance.aws_clients.appautoscaling_client.get_paginator(
            "describe_scalable_targets")
        page_iterator = paginator.paginate(
            ServiceNamespace='kafka',
            ResourceIds=[cluster_arn]
        )

        for page in page_iterator:
            for target in page["ScalableTargets"]:
                target_id = target["ResourceId"]
                service_namespace = target["ServiceNamespace"]
                scalable_dimension = target["ScalableDimension"]
                resource_id = target["ResourceId"]
                logger.debug(f"Processing AppAutoScaling Target: {target_id}")

                id = f"{service_namespace}/{resource_id}/{scalable_dimension}"

                attributes = {
                    "id": target_id,
                    "service_namespace": service_namespace,
                    "resource_id": resource_id,
                    "scalable_dimension": scalable_dimension,
                }

                self.hcl.process_resource(
                    "aws_appautoscaling_target", target_id, attributes)

    def aws_appautoscaling_policy(self, cluster_arn):
        logger.debug(
            f"Processing AppAutoScaling Policies for MSK Cluster ARN {cluster_arn}...")

        paginator = self.provider_instance.aws_clients.appautoscaling_client.get_paginator(
            "describe_scaling_policies")
        page_iterator = paginator.paginate(
            ServiceNamespace='kafka',
            ResourceId=cluster_arn
        )

        for page in page_iterator:
            for policy in page["ScalingPolicies"]:
                policy_name = policy["PolicyName"]
                service_namespace = policy["ServiceNamespace"]
                resource_id = policy["ResourceId"]
                scalable_dimension = policy["ScalableDimension"]

                id = f"{service_namespace}/{resource_id}/{scalable_dimension}/{policy_name}"

                logger.debug(
                    f"Processing AppAutoScaling Policy: {policy_name}")

                attributes = {
                    "id": id,
                    "name": policy_name,
                    "scalable_dimension": scalable_dimension,
                    "service_namespace": service_namespace,
                    "resource_id": resource_id,
                }

                self.hcl.process_resource(
                    "aws_appautoscaling_policy", id, attributes)

    def aws_msk_configuration(self, cluster_arn):
        logger.debug(
            f"Processing MSK Configuration for Cluster {cluster_arn}...")

        cluster_details = self.provider_instance.aws_clients.msk_client.describe_cluster(
            ClusterArn=cluster_arn
        )

        tmp = cluster_details["ClusterInfo"]["CurrentBrokerSoftwareInfo"]
        if "ConfigurationArn" not in tmp:
            return

        configuration_arn = cluster_details["ClusterInfo"]["CurrentBrokerSoftwareInfo"]["ConfigurationArn"]

        # Get the configuration details using the configuration ARN
        configuration = self.provider_instance.aws_clients.msk_client.describe_configuration(
            Arn=configuration_arn
        )

        config_name = configuration["Name"]

        logger.debug(f"Processing MSK Configuration: {config_name}")

        attributes = {
            "id": configuration_arn,
            "arn": configuration_arn,
            "name": config_name,
        }

        self.hcl.process_resource(
            "aws_msk_configuration", config_name, attributes)

    # def aws_security_group(self, security_group_ids):
    #     logger.debug("Processing Security Groups...")

    #     # Create a response dictionary to collect responses for all security groups
    #     response = self.provider_instance.aws_clients.ec2_client.describe_security_groups(
    #         GroupIds=security_group_ids
    #     )

    #     for security_group in response["SecurityGroups"]:
    #         logger.debug(
    #             f"Processing Security Group: {security_group['GroupName']}")

    #         attributes = {
    #             "id": security_group["GroupId"],
    #             "name": security_group["GroupName"],
    #             "description": security_group.get("Description", ""),
    #             "vpc_id": security_group.get("VpcId", ""),
    #             "owner_id": security_group.get("OwnerId", ""),
    #         }

    #         self.hcl.process_resource(
    #             "aws_security_group", security_group["GroupName"].replace("-", "_"), attributes)

    #         # Process egress rules
    #         for rule in security_group.get('IpPermissionsEgress', []):
    #             self.aws_security_group_rule(
    #                 'egress', security_group, rule)

    #         # Process ingress rules
    #         for rule in security_group.get('IpPermissions', []):
    #             self.aws_security_group_rule(
    #                 'ingress', security_group, rule)

    # def aws_security_group_rule(self, rule_type, security_group, rule):
    #     # Rule identifiers are often constructed by combining security group id, rule type, protocol, ports and security group references
    #     rule_id = f"{security_group['GroupId']}_{rule_type}_{rule.get('IpProtocol', 'all')}"
    #     logger.debug(f"Processing Security Groups Rule {rule_id}...")
    #     if rule.get('FromPort'):
    #         rule_id += f"_{rule['FromPort']}"
    #     if rule.get('ToPort'):
    #         rule_id += f"_{rule['ToPort']}"

    #     attributes = {
    #         "id": rule_id,
    #         "type": rule_type,
    #         "security_group_id": security_group['GroupId'],
    #         "protocol": rule.get('IpProtocol', '-1'),  # '-1' stands for 'all'
    #         "from_port": rule.get('FromPort', 0),
    #         "to_port": rule.get('ToPort', 0),
    #         "cidr_blocks": [ip_range['CidrIp'] for ip_range in rule.get('IpRanges', [])],
    #         "source_security_group_ids": [sg['GroupId'] for sg in rule.get('UserIdGroupPairs', [])]
    #     }

    #     self.hcl.process_resource(
    #         "aws_security_group_rule", rule_id.replace("-", "_"), attributes)
