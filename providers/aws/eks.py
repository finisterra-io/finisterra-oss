import os
from utils.hcl import HCL
from providers.aws.iam_role import IAM_ROLE
from providers.aws.kms import KMS
from providers.aws.security_group import SECURITY_GROUP
from providers.aws.logs import Logs
from providers.aws.launchtemplate import LaunchTemplate

class EKS:
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
        if not hcl:
            self.hcl = HCL(self.schema_data, self.provider_name)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.account_id = aws_account_id

        self.aws_account_id = aws_account_id

        self.iam_role_instance = IAM_ROLE(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.kms_instance = KMS(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.security_group_instance = SECURITY_GROUP(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.logs_instance = Logs(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.launchtemplate_instance = LaunchTemplate(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)


    def get_subnet_names(self, subnet_ids):
        subnet_names = []
        for subnet_id in subnet_ids:
            response = self.aws_clients.ec2_client.describe_subnets(SubnetIds=[subnet_id])

            # Check if 'Subnets' key exists and it's not empty
            if not response or 'Subnets' not in response or not response['Subnets']:
                print(
                    f"No subnet information found for Subnet ID: {subnet_id}")
                continue

            # Extract the 'Tags' key safely using get
            subnet_tags = response['Subnets'][0].get('Tags', [])

            # Extract the subnet name from the tags
            subnet_name = next(
                (tag['Value'] for tag in subnet_tags if tag['Key'] == 'Name'), None)

            if subnet_name:
                subnet_names.append(subnet_name)
            else:
                print(f"No 'Name' tag found for Subnet ID: {subnet_id}")      
        return subnet_names
    
    def get_vpc_name(self, vpc_id):
        response = self.aws_clients.ec2_client.describe_vpcs(VpcIds=[vpc_id])

        if not response or 'Vpcs' not in response or not response['Vpcs']:
            # Handle this case as required, for example:
            print(f"No VPC information found for VPC ID: {vpc_id}")
            return None

        vpc_tags = response['Vpcs'][0].get('Tags', [])
        vpc_name = next((tag['Value']
                        for tag in vpc_tags if tag['Key'] == 'Name'), None)

        if vpc_name is None:
            print(f"No 'Name' tag found for VPC ID: {vpc_id}")

        return vpc_name    

    def eks(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_eks_cluster()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()

    def aws_eks_cluster(self):
        resource_type = 'aws_eks_cluster'
        print("Processing EKS Clusters...")

        clusters = self.aws_clients.eks_client.list_clusters()["clusters"]

        for cluster_name in clusters:
            cluster = self.aws_clients.eks_client.describe_cluster(name=cluster_name)[
                "cluster"]
            tags = cluster.get("tags", {})
            ftstack = "eks"
            if tags.get("ftstack", "eks") != "eks":
                ftstack = "stack_"+tags.get("ftstack", "eks")
            
            # if cluster_name != "dev":
            #     continue

            print(f"Processing EKS Cluster: {cluster_name}")
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
                    self.hcl.add_additional_data(resource_type, id, "vpc_name", vpc_name)

            # Call aws_iam_role for the cluster's associated IAM role
            role_name = cluster["roleArn"].split('/')[-1]
            self.iam_role_instance.aws_iam_role(role_name, ftstack)

            #security_groups
            security_group_ids = cluster["resourcesVpcConfig"]["securityGroupIds"]
            for security_group_id in security_group_ids:
                self.security_group_instance.aws_security_group(security_group_id, ftstack)
            
            #kms key
            if 'encryptionConfig' in cluster:
                self.kms_instance.aws_kms_key(cluster['encryptionConfig'][0]['provider']['keyArn'], ftstack)

            # Call aws_eks_addon for each cluster
            self.aws_eks_addon(cluster_name, ftstack)

            # Call aws_eks_identity_provider_config for each cluster
            self.aws_eks_identity_provider_config(cluster_name)

            # Determine the log group name based on a naming convention
            log_group_name = f"/aws/eks/{cluster_name}/cluster"

            # Call aws_cloudwatch_log_group for each cluster's associated log group
            self.logs_instance.aws_cloudwatch_log_group(log_group_name, ftstack)
            # self.aws_cloudwatch_log_group(log_group_name)

            # Extract the security group ID
            security_group_id = cluster["resourcesVpcConfig"]["clusterSecurityGroupId"]
            self.aws_ec2_tag(security_group_id)

            # oidc irsa
            self.aws_iam_openid_connect_provider(cluster_name)

            # eks node group
            self.aws_eks_node_group(cluster_name, ftstack)


    def aws_eks_addon(self, cluster_name, ftstack=None):
        resource_type = 'aws_eks_addon'
        print(f"Processing EKS Add-ons for Cluster: {cluster_name}...")

        addons = self.aws_clients.eks_client.list_addons(
            clusterName=cluster_name)["addons"]

        for addon_name in addons:
            addon = self.aws_clients.eks_client.describe_addon(
                clusterName=cluster_name, addonName=addon_name)["addon"]
            print(
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
                self.iam_role_instance.aws_iam_role(service_account_role_arn.split('/')[-1], ftstack)

    def aws_iam_openid_connect_provider(self, cluster_name):
        print(
            f"Processing IAM OpenID Connect Providers for Cluster: {cluster_name}...")

        # Get cluster details to retrieve OIDC issuer URL
        cluster = self.aws_clients.eks_client.describe_cluster(name=cluster_name)[
            "cluster"]
        expected_oidc_url = cluster.get("identity", {}).get(
            "oidc", {}).get("issuer", "")

        expected_oidc_url = expected_oidc_url.replace("https://", "")

        # Ensure OIDC URL exists for the cluster
        if not expected_oidc_url:
            print(
                f"  Warning: No OIDC issuer URL found for Cluster: {cluster_name}")
            return

        # List the OIDC identity providers in the AWS account
        oidc_providers = self.aws_clients.iam_client.list_open_id_connect_providers().get(
            "OpenIDConnectProviderList", [])

        for provider in oidc_providers:
            provider_arn = provider["Arn"]

            # Describe the specific OIDC provider using its ARN
            oidc_provider = self.aws_clients.iam_client.get_open_id_connect_provider(
                OpenIDConnectProviderArn=provider_arn
            )

            # Extract the URL for the OIDC provider. This typically serves as a unique identifier.
            provider_url = oidc_provider.get("Url", "")

            # Check if this OIDC provider URL matches the one from the EKS cluster
            if provider_url != expected_oidc_url:
                continue  # Skip if it doesn't match

            print(
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
        print("Processing EKS Fargate Profiles...")

        clusters = self.aws_clients.eks_client.list_clusters()["clusters"]

        for cluster_name in clusters:
            fargate_profiles = self.aws_clients.eks_client.list_fargate_profiles(clusterName=cluster_name)[
                "fargateProfileNames"]

            for profile_name in fargate_profiles:
                fargate_profile = self.aws_clients.eks_client.describe_fargate_profile(
                    clusterName=cluster_name, fargateProfileName=profile_name)["fargateProfile"]
                print(
                    f"Processing EKS Fargate Profile: {profile_name} for Cluster: {cluster_name}")

                attributes = {
                    "id": fargate_profile["fargateProfileArn"],
                    "fargate_profile_name": profile_name,
                    "cluster_name": cluster_name,
                }
                self.hcl.process_resource(
                    "aws_eks_fargate_profile", f"{cluster_name}-{profile_name}".replace("-", "_"), attributes)

    def aws_eks_identity_provider_config(self, cluster_name):
        print(
            f"Processing EKS Identity Provider Configs for Cluster: {cluster_name}...")

        identity_provider_configs = self.aws_clients.eks_client.list_identity_provider_configs(
            clusterName=cluster_name)["identityProviderConfigs"]

        for config in identity_provider_configs:
            config_name = config["name"]
            config_type = config["type"]
            print(
                f"Processing EKS Identity Provider Config: {config_name} for Cluster: {cluster_name}")

            attributes = {
                "id": f"{cluster_name}:{config_name}",
                "name": config_name,
                "cluster_name": cluster_name,
            }
            self.hcl.process_resource(f"aws_eks_{config_type.lower()}_identity_provider_config",
                                      f"{cluster_name}-{config_name}".replace("-", "_"), attributes)

    def aws_ec2_tag(self, resource_id):
        print(f"Processing EC2 Tags for Resource ID: {resource_id}")

        # Fetch the tags for the specified resource
        response = self.aws_clients.ec2_client.describe_tags(
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

            print(
                f"  Prepared tag for Resource {resource_id} with {key} = {value}")

    def aws_eks_node_group(self, cluster_name, ftstack):
        print("Processing EKS Node Groups...")

        # clusters = self.aws_clients.eks_client.list_clusters()["clusters"]

        # # Check if the provided cluster_name is in the list of clusters
        # if cluster_name not in clusters:
        #     print(f"Cluster '{cluster_name}' not found!")
        #     return

        node_groups = self.aws_clients.eks_client.list_nodegroups(
            clusterName=cluster_name)["nodegroups"]

        for node_group_name in node_groups:
            node_group = self.aws_clients.eks_client.describe_nodegroup(
                clusterName=cluster_name, nodegroupName=node_group_name)["nodegroup"]
            print(
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
                subnet_names = self.get_subnet_names(subnet_ids)
                if subnet_names:
                    self.hcl.add_additional_data("aws_eks_node_group", id, "subnet_names", subnet_names)

            # If the node group has a launch template, process it
            if 'launchTemplate' in node_group and 'id' in node_group['launchTemplate']:
                self.launchtemplate_instance.aws_launch_template(node_group['launchTemplate']['id'], ftstack)
                # self.aws_launch_template(node_group['launchTemplate']['id'], ftstack)

            # Process IAM role associated with the EKS node group
            if 'nodeRole' in node_group:
                role_name = node_group['nodeRole'].split('/')[-1]
                self.iam_role_instance.aws_iam_role(role_name, ftstack)

            # Process Auto Scaling schedules for the node group's associated Auto Scaling group
            for asg in node_group.get('resources', {}).get('autoScalingGroups', []):
                self.aws_autoscaling_schedule(node_group_name, asg['name'])

    # def aws_launch_template(self, launch_template_id, ftstack):
    #     print("Processing AWS Launch Template...")

    #     # Describe the latest version of the launch template using the provided ID
    #     response = self.aws_clients.ec2_client.describe_launch_template_versions(
    #         LaunchTemplateId=launch_template_id,
    #         Versions=['$Latest']
    #     )

    #     # Check if we have the launch template versions in the response
    #     if 'LaunchTemplateVersions' not in response or not response['LaunchTemplateVersions']:
    #         print(f"Launch template with ID '{launch_template_id}' not found!")
    #         return

    #     latest_version = response['LaunchTemplateVersions'][0]
    #     launch_template_data = latest_version['LaunchTemplateData']

    #     print(f"Processing Launch Template: {latest_version['LaunchTemplateName']} with ID: {launch_template_id}")

    #     attributes = {
    #         "id": launch_template_id,
    #         "name": latest_version['LaunchTemplateName'],
    #         "version": latest_version['VersionNumber'],
    #         # You can add other attributes from the launch_template as needed
    #     }

    #     self.hcl.process_resource(
    #         "aws_launch_template", f"{latest_version['LaunchTemplateName']}".replace("-", "_"), attributes)
        
    #     #security_groups
    #     security_group_ids = launch_template_data.get("SecurityGroupIds", [])
    #     for security_group_id in security_group_ids:
    #         self.security_group_instance.aws_security_group(security_group_id, ftstack)
        
    #     # Process KMS Key for EBS Volume
    #     if 'BlockDeviceMappings' in launch_template_data:
    #         for mapping in launch_template_data['BlockDeviceMappings']:
    #             if 'Ebs' in mapping and 'KmsKeyId' in mapping['Ebs']:
    #                 kms_key_id = mapping['Ebs']['KmsKeyId']
    #                 print(f"Found KMS Key ID for EBS: {kms_key_id}")
    #                 self.kms_instance.aws_kms_key(kms_key_id, ftstack)
    #                 break  # Assuming we need the first KMS Key ID found
    #     else:
    #         print("No Block Device Mappings with EBS found in the Launch Template.")

    def aws_autoscaling_schedule(self, node_group_name, autoscaling_group_name):
        print(
            f"Processing Auto Scaling Schedules for Group: {autoscaling_group_name}...")

        try:
            # List all scheduled actions for the specified Auto Scaling group
            scheduled_actions = self.aws_clients.autoscaling_client.describe_scheduled_actions(
                AutoScalingGroupName=autoscaling_group_name)['ScheduledUpdateGroupActions']
            
            for action in scheduled_actions:
                id = action['ScheduledActionName']
                print(
                    f"Processing Auto Scaling Schedule: {id} for Group: {autoscaling_group_name}")

                attributes = {
                    "id": id,
                    "start_time": action.get('StartTime', ''),
                    "end_time": action.get('EndTime', ''),
                    # You can add more attributes as needed
                }
                self.hcl.process_resource(
                    "aws_autoscaling_schedule",id, attributes)
                
                self.hcl.add_additional_data("aws_autoscaling_schedule", id, "node_group_name", node_group_name)
        except Exception as e:
            print(
                f"Error processing Auto Scaling schedule for group {autoscaling_group_name}: {str(e)}")
