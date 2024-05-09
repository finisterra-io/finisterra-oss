from ...utils.hcl import HCL
from ...providers.aws.iam_role import IAM
from ...providers.aws.kms import KMS
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.logs import Logs
from ...providers.aws.launchtemplate import LaunchTemplate
from ...providers.aws.utils import get_subnet_names
import logging
import inspect

logger = logging.getLogger('finisterra')


class EKS:
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
        self.kms_instance = KMS(self.provider_instance, self.hcl)
        self.security_group_instance = SECURITY_GROUP(
            self.provider_instance, self.hcl)
        self.logs_instance = Logs(self.provider_instance, self.hcl)
        self.launchtemplate_instance = LaunchTemplate(
            self.provider_instance, self.hcl)

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

    def eks(self):
        self.hcl.prepare_folder()

        self.aws_eks_cluster()
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

    def cluster_matches_filters(self, cluster_tags):
        """
        Check if the cluster's tags match all filter conditions.
        :param cluster_tags: Dictionary of cluster tags
        :return: True if cluster matches all filter conditions, False otherwise.
        """
        return all(
            any(cluster_tags.get(f['Name'].replace(
                'tag:', ''), '') == value for value in f['Values'])
            for f in self.provider_instance.filters
        ) if self.provider_instance.filters else True

    def aws_eks_cluster(self):
        resource_type = 'aws_eks_cluster'
        logger.debug("Processing EKS Clusters...")

        try:
            clusters = self.provider_instance.aws_clients.eks_client.list_clusters()[
                "clusters"]
            filtered_clusters = []

            for cluster_name in clusters:
                cluster_info = self.provider_instance.aws_clients.eks_client.describe_cluster(
                    name=cluster_name)["cluster"]
                cluster_tags = cluster_info.get("tags", {})

                if self.cluster_matches_filters(cluster_tags):
                    filtered_clusters.append((cluster_name, cluster_info))

            if filtered_clusters:
                self.task = self.provider_instance.progress.add_task(
                    f"[cyan]Processing {self.__class__.__name__}...", total=len(filtered_clusters))

            for cluster_name, cluster in filtered_clusters:
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{cluster_name}[/]")
                logger.debug(f"Processing EKS Cluster: {cluster_name}")

                ftstack = "eks"
                if cluster.get("tags", {}).get("ftstack", "eks") != "eks":
                    ftstack = "stack_" + \
                        cluster.get("tags", {}).get("ftstack", "eks")

                # Here, continue with your processing logic as needed
                # The example below is a simplification of your original processing steps
                id = cluster_name

                attributes = {
                    "id": id,
                }
                self.hcl.process_resource(
                    resource_type, cluster_name.replace("-", "_"), attributes)
                self.hcl.add_stack(resource_type, id, ftstack)

                vpc_id = cluster["resourcesVpcConfig"]["vpcId"]
                if vpc_id:
                    vpc_name = self.get_vpc_name(vpc_id)
                    if vpc_name:
                        self.hcl.add_additional_data(
                            resource_type, id, "vpc_name", vpc_name)

                subnet_ids = cluster["resourcesVpcConfig"]["subnetIds"]
                if subnet_ids:
                    subnet_names = get_subnet_names(
                        self.provider_instance.aws_clients, subnet_ids)
                    if subnet_names:
                        self.hcl.add_additional_data(
                            "aws_eks_cluster", id, "subnet_names", subnet_names)

                # Call aws_iam_role for the cluster's associated IAM role
                role_name = cluster["roleArn"].split('/')[-1]
                self.iam_role_instance.aws_iam_role(role_name, ftstack)

                # security_groups
                security_group_ids = cluster["resourcesVpcConfig"]["securityGroupIds"]
                # logger.info(f"Security Group IDs: {security_group_ids}")
                for security_group_id in security_group_ids:
                    self.security_group_instance.aws_security_group(
                        security_group_id, ftstack)

                # kms key
                if 'encryptionConfig' in cluster:
                    self.kms_instance.aws_kms_key(
                        cluster['encryptionConfig'][0]['provider']['keyArn'], ftstack)

                # Call aws_eks_addon for each cluster
                self.aws_eks_addon(cluster_name, ftstack)

                # Call aws_eks_identity_provider_config for each cluster
                self.aws_eks_identity_provider_config(cluster_name)

                # Determine the log group name based on a naming convention
                log_group_name = f"/aws/eks/{cluster_name}/cluster"

                # Call aws_cloudwatch_log_group for each cluster's associated log group
                self.logs_instance.aws_cloudwatch_log_group(
                    log_group_name, ftstack)
                # self.aws_cloudwatch_log_group(log_group_name)

                # Extract the security group ID
                security_group_id = cluster["resourcesVpcConfig"]["clusterSecurityGroupId"]
                self.aws_ec2_tag(security_group_id)

                # oidc irsa
                self.aws_iam_openid_connect_provider(cluster_name)

                # eks node group
                self.aws_eks_node_group(cluster_name, ftstack)
        except Exception as e:
            logger.error(f"Error executing eks: {e}")
            return

    def aws_eks_addon(self, cluster_name, ftstack=None):
        resource_type = 'aws_eks_addon'
        logger.debug(f"Processing EKS Add-ons for Cluster: {cluster_name}...")

        addons = self.provider_instance.aws_clients.eks_client.list_addons(
            clusterName=cluster_name)["addons"]

        for addon_name in addons:
            addon = self.provider_instance.aws_clients.eks_client.describe_addon(
                clusterName=cluster_name, addonName=addon_name)["addon"]
            logger.debug(
                f"Processing EKS Add-on: {addon_name} for Cluster: {cluster_name}")

            id = cluster_name + ":" + addon_name
            attributes = {
                "id": id,
                "addon_name": addon_name,
                "cluster_name": cluster_name,
            }
            self.hcl.process_resource(
                resource_type, f"{cluster_name}-{addon_name}".replace("-", "_"), attributes)

            service_account_role_arn = addon.get("serviceAccountRoleArn", "")
            if service_account_role_arn:
                self.iam_role_instance.aws_iam_role(
                    service_account_role_arn.split('/')[-1], ftstack)

    def aws_iam_openid_connect_provider(self, cluster_name):
        logger.debug(
            f"Processing IAM OpenID Connect Providers for Cluster: {cluster_name}...")

        # Get cluster details to retrieve OIDC issuer URL
        cluster = self.provider_instance.aws_clients.eks_client.describe_cluster(name=cluster_name)[
            "cluster"]
        expected_oidc_url = cluster.get("identity", {}).get(
            "oidc", {}).get("issuer", "")

        expected_oidc_url = expected_oidc_url.replace("https://", "")

        # Ensure OIDC URL exists for the cluster
        if not expected_oidc_url:
            logger.debug(
                f"  Warning: No OIDC issuer URL found for Cluster: {cluster_name}")
            return

        # List the OIDC identity providers in the AWS account
        oidc_providers = self.provider_instance.aws_clients.iam_client.list_open_id_connect_providers().get(
            "OpenIDConnectProviderList", [])

        for provider in oidc_providers:
            provider_arn = provider["Arn"]

            # Describe the specific OIDC provider using its ARN
            oidc_provider = self.provider_instance.aws_clients.iam_client.get_open_id_connect_provider(
                OpenIDConnectProviderArn=provider_arn
            )

            # Extract the URL for the OIDC provider. This typically serves as a unique identifier.
            provider_url = oidc_provider.get("Url", "")

            # Check if this OIDC provider URL matches the one from the EKS cluster
            if provider_url != expected_oidc_url:
                continue  # Skip if it doesn't match

            logger.debug(
                f"Processing IAM OpenID Connect Provider: {provider_url} for Cluster: {cluster_name}")

            attributes = {
                "id": provider_arn,  # Using the ARN as the unique identifier
                "url": provider_url
            }

            # Convert the provider ARN to a more suitable format for your naming convention if necessary
            resource_type = provider_arn.split(
                ":")[-1].replace(":", "_").replace("-", "_")

            self.hcl.process_resource(
                "aws_iam_openid_connect_provider", resource_type, attributes
            )

    def aws_eks_fargate_profile(self):
        logger.debug("Processing EKS Fargate Profiles...")

        clusters = self.provider_instance.aws_clients.eks_client.list_clusters()[
            "clusters"]

        for cluster_name in clusters:
            fargate_profiles = self.provider_instance.aws_clients.eks_client.list_fargate_profiles(clusterName=cluster_name)[
                "fargateProfileNames"]

            for profile_name in fargate_profiles:
                fargate_profile = self.provider_instance.aws_clients.eks_client.describe_fargate_profile(
                    clusterName=cluster_name, fargateProfileName=profile_name)["fargateProfile"]
                logger.debug(
                    f"Processing EKS Fargate Profile: {profile_name} for Cluster: {cluster_name}")

                attributes = {
                    "id": fargate_profile["fargateProfileArn"],
                    "fargate_profile_name": profile_name,
                    "cluster_name": cluster_name,
                }
                self.hcl.process_resource(
                    "aws_eks_fargate_profile", f"{cluster_name}-{profile_name}".replace("-", "_"), attributes)

    def aws_eks_identity_provider_config(self, cluster_name):
        logger.debug(
            f"Processing EKS Identity Provider Configs for Cluster: {cluster_name}...")

        identity_provider_configs = self.provider_instance.aws_clients.eks_client.list_identity_provider_configs(
            clusterName=cluster_name)["identityProviderConfigs"]

        for config in identity_provider_configs:
            config_name = config["name"]
            config_type = config["type"]
            logger.debug(
                f"Processing EKS Identity Provider Config: {config_name} for Cluster: {cluster_name}")

            attributes = {
                "id": f"{cluster_name}:{config_name}",
                "name": config_name,
                "cluster_name": cluster_name,
            }
            self.hcl.process_resource(f"aws_eks_{config_type.lower()}_identity_provider_config",
                                      f"{cluster_name}-{config_name}".replace("-", "_"), attributes)

    def aws_ec2_tag(self, resource_id):
        logger.debug(f"Processing EC2 Tags for Resource ID: {resource_id}")

        # Fetch the tags for the specified resource
        response = self.provider_instance.aws_clients.ec2_client.describe_tags(
            Filters=[
                {
                    'Name': 'resource-id',
                    'Values': [resource_id]
                }
            ]
        )

        # Extract tags from the response
        tags = response.get('Tags', [])

        # Process each tag
        for tag in tags:
            key = tag.get('Key')
            if key == "Name":
                continue
            value = tag.get('Value')

            # Prepare the attributes
            attributes = {
                "id": f"{resource_id},{key}",
                "key": key,
                "value": value,
                "resource_id": resource_id
            }

            # Process the resource
            self.hcl.process_resource("aws_ec2_tag",
                                      f"{resource_id}-{key}".replace("-", "_"),
                                      attributes)

            logger.debug(
                f"  Prepared tag for Resource {resource_id} with {key} = {value}")

    def aws_eks_node_group(self, cluster_name, ftstack):
        logger.debug("Processing EKS Node Groups...")

        # clusters = self.provider_instance.aws_clients.eks_client.list_clusters()["clusters"]

        # # Check if the provided cluster_name is in the list of clusters
        # if cluster_name not in clusters:
        #     logger.debug(f"Cluster '{cluster_name}' not found!")
        #     return

        node_groups = self.provider_instance.aws_clients.eks_client.list_nodegroups(
            clusterName=cluster_name)["nodegroups"]

        for node_group_name in node_groups:
            node_group = self.provider_instance.aws_clients.eks_client.describe_nodegroup(
                clusterName=cluster_name, nodegroupName=node_group_name)["nodegroup"]
            logger.debug(
                f"Processing EKS Node Group: {node_group_name} for Cluster: {cluster_name}")

            id = cluster_name + ":" + node_group_name
            attributes = {
                "id": id,
                "node_group_name": node_group_name,
                "cluster_name": cluster_name,
            }
            self.hcl.process_resource(
                "aws_eks_node_group", f"{cluster_name}-{node_group_name}".replace("-", "_"), attributes)

            subnet_ids = node_group["subnets"]
            if subnet_ids:
                subnet_names = get_subnet_names(
                    self.provider_instance.aws_clients, subnet_ids)
                if subnet_names:
                    self.hcl.add_additional_data(
                        "aws_eks_node_group", id, "subnet_names", subnet_names)

            # If the node group has a launch template, process it
            if 'launchTemplate' in node_group and 'id' in node_group['launchTemplate']:
                self.launchtemplate_instance.aws_launch_template(
                    node_group['launchTemplate']['id'], ftstack)
                # self.aws_launch_template(node_group['launchTemplate']['id'], ftstack)

            # Process IAM role associated with the EKS node group
            if 'nodeRole' in node_group:
                role_name = node_group['nodeRole'].split('/')[-1]
                self.iam_role_instance.aws_iam_role(role_name, ftstack)

            # Process Auto Scaling schedules for the node group's associated Auto Scaling group
            for asg in node_group.get('resources', {}).get('autoScalingGroups', []):
                self.aws_autoscaling_schedule(node_group_name, asg['name'])

    def aws_autoscaling_schedule(self, node_group_name, autoscaling_group_name):
        logger.debug(
            f"Processing Auto Scaling Schedules for Group: {autoscaling_group_name}...")

        try:
            # List all scheduled actions for the specified Auto Scaling group
            scheduled_actions = self.provider_instance.aws_clients.autoscaling_client.describe_scheduled_actions(
                AutoScalingGroupName=autoscaling_group_name)['ScheduledUpdateGroupActions']

            for action in scheduled_actions:
                id = action['ScheduledActionName']
                logger.debug(
                    f"Processing Auto Scaling Schedule: {id} for Group: {autoscaling_group_name}")

                attributes = {
                    "id": id,
                    "start_time": action.get('StartTime', ''),
                    "end_time": action.get('EndTime', ''),
                    # You can add more attributes as needed
                }
                self.hcl.process_resource(
                    "aws_autoscaling_schedule", id, attributes)

                self.hcl.add_additional_data(
                    "aws_autoscaling_schedule", id, "node_group_name", node_group_name)
        except Exception as e:
            logger.error(
                f"Error processing Auto Scaling schedule for group {autoscaling_group_name}: {str(e)}")
