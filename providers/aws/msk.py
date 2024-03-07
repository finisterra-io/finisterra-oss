import os
from utils.hcl import HCL
from providers.aws.security_group import SECURITY_GROUP

class MSK:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.aws_account_id = aws_account_id
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.s3Bucket = s3Bucket
        self.dynamoDBTable = dynamoDBTable
        self.state_key = state_key
        self.workspace_id = workspace_id

        self.modules = modules
        if not hcl:
            self.hcl = HCL(self.schema_data, self.provider_name)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


        self.security_group_instance = SECURITY_GROUP(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)

        
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

    def get_vpc_id(self, sg_ids):
        if not sg_ids:
            return None

        # Get the first security group ID
        first_sg_id = sg_ids[0]

        # Describe the security group to get its VPC ID
        response = self.aws_clients.ec2_client.describe_security_groups(GroupIds=[
                                                            first_sg_id])

        # Extract and return the VPC ID
        vpc_id = response["SecurityGroups"][0]["VpcId"]
        return vpc_id

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


    def msk(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_msk_cluster()

        self.hcl.refresh_state()

        self.hcl.request_tf_code()


    def aws_msk_cluster(self):
        resource_type = "aws_msk_cluster"
        print("Processing MSK Clusters...")

        # Pagination for list_clusters, if applicable
        paginator = self.aws_clients.msk_client.get_paginator("list_clusters")
        page_iterator = paginator.paginate()

        for page in page_iterator:
            for cluster_info in page["ClusterInfoList"]:
                cluster_arn = cluster_info["ClusterArn"]
                cluster_name = cluster_info["ClusterName"]
                print(f"Processing MSK Cluster: {cluster_name}")
                id = cluster_arn

                ftstack = "msk"
                try:
                    tags_response = self.aws_clients.msk_client.list_tags_for_resource(ResourceArn=cluster_arn)
                    tags = tags_response.get('Tags', {})
                    if tags.get('ftstack', 'msk') != 'msk':
                        ftstack = "stack_"+tags.get('ftstack', 'msk')
                except Exception as e:
                    print("Error occurred: ", e)

                attributes = {
                    "id": id,
                    # "arn": cluster_arn,
                    # "name": cluster_name,
                }

                self.hcl.process_resource(
                    resource_type, id, attributes)
                self.hcl.add_stack(resource_type, id, ftstack)

                # Extracting the Security Group IDs for the MSK Cluster
                cluster_details = self.aws_clients.msk_client.describe_cluster(
                    ClusterArn=cluster_arn
                )

                sg_ids = cluster_details["ClusterInfo"]["BrokerNodeGroupInfo"]["SecurityGroups"]

                # Calling aws_security_group function with the extracted SG IDs
                for sg in sg_ids:   
                    self.security_group_instance.aws_security_group(sg, ftstack)
                vpc_id = self.get_vpc_id(sg_ids)
                if vpc_id:
                    self.hcl.add_additional_data(resource_type, id, "vpc_id", vpc_id)
                    vpc_name = self.get_vpc_name(vpc_id)
                    if vpc_name:
                        self.hcl.add_additional_data(resource_type, id, "vpc_name", vpc_name)
                subnet_ids = cluster_details["ClusterInfo"]["BrokerNodeGroupInfo"]["ClientSubnets"]
                if subnet_ids:
                    subnet_names = self.get_subnet_names(subnet_ids)
                    if subnet_names:
                        self.hcl.add_additional_data(resource_type, id, "subnet_names", subnet_names)

                self.aws_msk_configuration(cluster_arn)
                # self.aws_msk_scram_secret_association(cluster_arn)
                self.aws_appautoscaling_target(cluster_arn)
                self.aws_appautoscaling_policy(cluster_arn)

    def aws_msk_scram_secret_association(self, cluster_arn):
        print(
            f"Processing SCRAM Secret Associations for Cluster {cluster_arn}...")

        # Not all MSK methods might support pagination, so ensure this one does.
        secrets = self.aws_clients.msk_client.list_scram_secrets(
            ClusterArn=cluster_arn
        )

        for secret in secrets.get("SecretArnList", []):
            print(f"Processing SCRAM Secret: {secret}")

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
        print(
            f"Processing AppAutoScaling Targets for MSK Cluster ARN {cluster_arn}...")

        paginator = self.aws_clients.appautoscaling_client.get_paginator(
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
                print(f"Processing AppAutoScaling Target: {target_id}")

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
        print(
            f"Processing AppAutoScaling Policies for MSK Cluster ARN {cluster_arn}...")

        paginator = self.aws_clients.appautoscaling_client.get_paginator(
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

                print(f"Processing AppAutoScaling Policy: {policy_name}")

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
        print(f"Processing MSK Configuration for Cluster {cluster_arn}...")

        cluster_details = self.aws_clients.msk_client.describe_cluster(
            ClusterArn=cluster_arn
        )

        tmp = cluster_details["ClusterInfo"]["CurrentBrokerSoftwareInfo"]
        if "ConfigurationArn" not in tmp:
            return

        configuration_arn = cluster_details["ClusterInfo"]["CurrentBrokerSoftwareInfo"]["ConfigurationArn"]

        # Get the configuration details using the configuration ARN
        configuration = self.aws_clients.msk_client.describe_configuration(
            Arn=configuration_arn
        )

        config_name = configuration["Name"]

        print(f"Processing MSK Configuration: {config_name}")

        attributes = {
            "id": configuration_arn,
            "arn": configuration_arn,
            "name": config_name,
        }

        self.hcl.process_resource(
            "aws_msk_configuration", config_name, attributes)

    # def aws_security_group(self, security_group_ids):
    #     print("Processing Security Groups...")

    #     # Create a response dictionary to collect responses for all security groups
    #     response = self.aws_clients.ec2_client.describe_security_groups(
    #         GroupIds=security_group_ids
    #     )

    #     for security_group in response["SecurityGroups"]:
    #         print(
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
    #     print(f"Processing Security Groups Rule {rule_id}...")
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
