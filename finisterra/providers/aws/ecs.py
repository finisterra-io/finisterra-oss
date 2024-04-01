import os
from ...utils.hcl import HCL
from ...providers.aws.iam_role import IAM
from ...providers.aws.logs import Logs
from ...providers.aws.kms import KMS
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.target_group import TargetGroup
import logging
import inspect

logger = logging.getLogger('finisterra')


class ECS:
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
        self.logs_instance = Logs(self.provider_instance, self.hcl)
        self.kms_instance = KMS(self.provider_instance, self.hcl)
        self.security_group_instance = SECURITY_GROUP(
            self.provider_instance, self.hcl)
        self.target_group_instance = TargetGroup(
            self.provider_instance, self.hcl)

    def get_subnet_names(self, network_configuration):
        if network_configuration:
            awsvpcConfiguration = network_configuration.get(
                "awsvpcConfiguration")
            subnets = awsvpcConfiguration.get("subnets")
            subnet_names = []
            for subnet_id in subnets:
                response = self.provider_instance.aws_clients.ec2_client.describe_subnets(SubnetIds=[
                    subnet_id])

                # Check if 'Subnets' key exists and it's not empty
                if not response or 'Subnets' not in response or not response['Subnets']:
                    logger.debug(
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
                    logger.debug(
                        f"No 'Name' tag found for Subnet ID: {subnet_id}")

            if subnet_names:
                return subnet_names
        return ""

    def get_vpc_name(self, network_configuration):
        vpc_name = None
        vpc_id = None
        if network_configuration:
            awsvpcConfiguration = network_configuration.get(
                "awsvpcConfiguration")
            subnets = awsvpcConfiguration.get("subnets")
            if subnets:
                # get the vpc id for the first subnet
                subnet_id = subnets[0]
                response = self.provider_instance.aws_clients.ec2_client.describe_subnets(SubnetIds=[
                    subnet_id])
                vpc_id = response['Subnets'][0]['VpcId']
            if vpc_id:
                response = self.provider_instance.aws_clients.ec2_client.describe_vpcs(VpcIds=[
                    vpc_id])
                if not response or 'Vpcs' not in response or not response['Vpcs']:
                    # Handle this case as required, for example:
                    logger.debug(
                        f"No VPC information found for VPC ID: {vpc_id}")
                    return None

                vpc_tags = response['Vpcs'][0].get('Tags', [])
                vpc_name = next((tag['Value']
                                for tag in vpc_tags if tag['Key'] == 'Name'), None)
                return vpc_name
        return ""

    def ecs(self):
        self.hcl.prepare_folder()

        self.aws_ecs_cluster()
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

    def aws_ecs_cluster(self):
        resource_type = "aws_ecs_cluster"
        logger.debug("Processing ECS Clusters...")

        clusters_arns = self.provider_instance.aws_clients.ecs_client.list_clusters()[
            "clusterArns"]
        clusters = self.provider_instance.aws_clients.ecs_client.describe_clusters(
            clusters=clusters_arns, include=["CONFIGURATIONS"])["clusters"]

        if clusters:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=len(clusters))

        for cluster in clusters:
            cluster_name = cluster["clusterName"]
            cluster_arn = cluster["clusterArn"]
            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{cluster_name}[/]")

            # if cluster_name == "xxx":
            #     continue

            logger.debug(f"Processing ECS Cluster: {cluster_name}")
            id = cluster_name

            ftstack = "ecs"
            try:
                tags_response = self.provider_instance.aws_clients.ecs_client.list_tags_for_resource(
                    resourceArn=cluster_arn)
                tags = tags_response.get('tags', [])
                for tag in tags:
                    if tag['key'] == 'ftstack':
                        if tag['value'] != 'ecs':
                            ftstack = "stack_"+tag['value']
                        break
            except Exception as e:
                logger.error(f"Error occurred: {e}")

            attributes = {
                "id": id,
                "name": cluster_name,
            }
            self.hcl.process_resource(
                resource_type, cluster_name.replace("-", "_"), attributes)

            self.hcl.add_stack(resource_type, id, ftstack)

            if os.environ.get('FT_PROCESS_DEPENDENCIES', 'False') != 'False':
                # Extract CloudWatch log group name from cluster configuration
                cloudwatch_log_group_name = None
                kmsKeyId = None
                configuration = cluster.get('configuration', {})
                if configuration:
                    execute_command_configuration = configuration.get(
                        'executeCommandConfiguration', {})
                    if execute_command_configuration:
                        log_configuration = execute_command_configuration.get(
                            'logConfiguration', {})
                        if log_configuration:
                            cloudwatch_log_group_name = log_configuration.get(
                                'cloudWatchLogGroupName')
                            if cloudwatch_log_group_name:
                                self.logs_instance.aws_cloudwatch_log_group(
                                    cloudwatch_log_group_name, ftstack)
                        kmsKeyId = execute_command_configuration.get(
                            'kmsKeyId')

                if cloudwatch_log_group_name:
                    self.logs_instance.aws_cloudwatch_log_group(
                        cloudwatch_log_group_name, ftstack)

                if kmsKeyId:
                    self.kms_instance.aws_kms_key(kmsKeyId, ftstack)

            self.aws_ecs_cluster_capacity_providers(cluster_name)
            self.aws_ecs_capacity_provider(cluster_name)
            self.aws_ecs_service(cluster_name, ftstack)

    def aws_ecs_cluster_capacity_providers(self, cluster_name):
        logger.debug(
            "Processing ECS Cluster Capacity Providers for the specified cluster...")

        cluster_arns = self.provider_instance.aws_clients.ecs_client.list_clusters()[
            "clusterArns"]
        clusters = self.provider_instance.aws_clients.ecs_client.describe_clusters(
            clusters=cluster_arns)["clusters"]

        for cluster in clusters:
            if cluster["clusterName"] == cluster_name:
                capacity_providers = cluster.get("capacityProviders", [])

                for provider in capacity_providers:
                    logger.debug(
                        f"Processing ECS Cluster Capacity Provider: {provider} for Cluster: {cluster_name}")

                    resource_name = f"{cluster_name}-{provider}"
                    attributes = {
                        "id": cluster_name,
                        "capacity_provider": provider,
                    }
                    self.hcl.process_resource(
                        "aws_ecs_cluster_capacity_providers", resource_name.replace("-", "_"), attributes)
            else:
                logger.debug(
                    f"Skipping aws_ecs_cluster_capacity_providers: {cluster['clusterName']}")

    def aws_ecs_capacity_provider(self, cluster_name):
        logger.debug(
            f"Processing ECS Capacity Providers for cluster: {cluster_name}...")

        cluster_arns = self.provider_instance.aws_clients.ecs_client.list_clusters()[
            "clusterArns"]
        clusters = self.provider_instance.aws_clients.ecs_client.describe_clusters(
            clusters=cluster_arns)["clusters"]

        for cluster in clusters:
            if cluster['clusterName'] == cluster_name:
                capacity_providers = cluster.get('capacityProviders', [])

                for provider_name in capacity_providers:
                    provider_details = self.provider_instance.aws_clients.ecs_client.describe_capacity_providers(
                        capacityProviders=[provider_name])["capacityProviders"][0]

                    auto_scaling_group_provider = provider_details.get(
                        'autoScalingGroupProvider', None)

                    if auto_scaling_group_provider:
                        logger.debug(
                            f"Processing ECS Capacity Provider: {provider_name}")

                        attributes = {
                            "id": provider_name,
                            "auto_scaling_group_arn": auto_scaling_group_provider['autoScalingGroupArn'],
                        }
                        self.hcl.process_resource(
                            "aws_ecs_capacity_provider", provider_name.replace("-", "_"), attributes)
                    else:
                        logger.debug(
                            f"Skipping provider: {provider_name} without auto scaling group")

            else:
                logger.debug(
                    f"Skipping aws_ecs_capacity_provider: {cluster['clusterName']}")

    def aws_ecs_service(self, cluster_name, ftstack):
        resource_type = "aws_ecs_service"
        logger.debug(f"Processing ECS Services for cluster: {cluster_name}...")

        clusters_arns = self.provider_instance.aws_clients.ecs_client.list_clusters()[
            "clusterArns"]
        clusters = self.provider_instance.aws_clients.ecs_client.describe_clusters(
            clusters=clusters_arns)["clusters"]

        for cluster in clusters:
            if cluster['clusterName'] == cluster_name:
                cluster_arn = cluster['clusterArn']
                paginator = self.provider_instance.aws_clients.ecs_client.get_paginator(
                    'list_services')

                for page in paginator.paginate(cluster=cluster_arn):
                    services_arns = page["serviceArns"]
                    if not services_arns:
                        logger.debug(
                            f"  No services found for cluster. {cluster_name}")
                        continue
                    services = self.provider_instance.aws_clients.ecs_client.describe_services(
                        cluster=cluster_arn, services=services_arns)["services"]

                    for service in services:
                        service_name = service["serviceName"]

                        # if service_name != "xxx":
                        #     continue

                        service_arn = service["serviceArn"]
                        id = cluster_arn.split("/")[1] + "/" + service_name

                        logger.debug(f"Processing ECS Service: {service_name}")

                        attributes = {
                            "id": id,
                            "arn": service_arn,
                            "name": service_name,
                            "cluster": cluster_arn,
                        }
                        self.hcl.process_resource(
                            resource_type, service_name.replace("-", "_"), attributes)
                        self.hcl.add_stack(resource_type, service_arn, ftstack)

                        network_configuration = service.get(
                            'networkConfiguration', {})
                        if network_configuration:
                            subnet_names = self.get_subnet_names(
                                network_configuration)
                            if subnet_names:
                                self.hcl.add_additional_data(
                                    resource_type, service_arn, "subnet_names", subnet_names)
                            vpc_name = self.get_vpc_name(network_configuration)
                            if vpc_name:
                                self.hcl.add_additional_data(
                                    resource_type, service_arn, "vpc_name", vpc_name)

                        self.aws_appautoscaling_target(
                            cluster_name, service_name)

                        if os.environ.get('FT_PROCESS_DEPENDENCIES', 'False') != 'False':
                            if service.get('roleArn'):
                                role_name = service['roleArn'].split('/')[-1]
                                self.iam_role_instance.aws_iam_role(
                                    role_name, ftstack)

                        # Call task definition for this service's task definition
                        if service.get('taskDefinition'):
                            self.aws_ecs_task_definition(
                                service['taskDefinition'], ftstack)

                        # Process load balancer target groups if present
                        # for lb in service.get('loadBalancers', []):
                        #     if lb.get('targetGroupArn'):
                        #         self.aws_lb_target_group(lb['targetGroupArn'])

                        if os.environ.get('FT_PROCESS_DEPENDENCIES', 'False') != 'False':
                            network_configuration = service.get(
                                'networkConfiguration', {})
                            if network_configuration:
                                aws_vpc_configuration = network_configuration.get(
                                    'awsvpcConfiguration', {})
                                if aws_vpc_configuration:
                                    security_groups = aws_vpc_configuration.get(
                                        'securityGroups', [])
                                    for sg in security_groups:
                                        self.security_group_instance.aws_security_group(
                                            sg, ftstack)

                            # Get the load balancer and the the target group arn
                            load_balancers = service.get('loadBalancers', [])
                            for lb in load_balancers:
                                # lb_name = lb.get('loadBalancerName')
                                target_group_arn = lb.get('targetGroupArn')
                                if target_group_arn:
                                    logger.debug(
                                        f"Processing Target Group: {target_group_arn}...")
                                    self.target_group_instance.aws_lb_target_group(
                                        target_group_arn, ftstack)

                        # Cloudmap
                        serviceRegistries = service.get(
                            'serviceRegistries', [])
                        for serviceRegistry in serviceRegistries:
                            registry_arn = serviceRegistry.get('registryArn')
                            registry_id = registry_arn.split('/')[-1]
                            # Fetching service details using registry_id
                            cloudmap = self.provider_instance.aws_clients.cloudmap_client.get_service(Id=registry_id)[
                                'Service']
                            if cloudmap:
                                registry_name = cloudmap['Name']
                                if registry_name:
                                    self.hcl.add_additional_data(
                                        "aws_service_discovery_service", registry_arn, "registry_name", registry_name)
                                    namespace = self.provider_instance.aws_clients.cloudmap_client.get_namespace(
                                        Id=cloudmap['NamespaceId'])['Namespace']
                                    namespace_name = namespace['Name']
                                    if namespace_name:
                                        self.hcl.add_additional_data(
                                            "aws_service_discovery_service", registry_arn, "namespace_name", namespace_name)

            # else:
            #     logger.debug(f"Skipping aws_ecs_service: {cluster['clusterName']}")

    def aws_ecs_task_definition(self, task_definition_arn, ftstack):
        logger.debug(
            f"Processing ECS Task Definition: {task_definition_arn}...")

        task_definition = self.provider_instance.aws_clients.ecs_client.describe_task_definition(
            taskDefinition=task_definition_arn)["taskDefinition"]

        family = task_definition['family']
        revision = task_definition['revision']
        attributes = {
            "id": task_definition_arn,
            "arn": task_definition_arn,
            "family": family,
        }
        self.hcl.process_resource(
            "aws_ecs_task_definition", family.replace("-", "_")+"_"+str(revision), attributes)

        if os.environ.get('FT_PROCESS_DEPENDENCIES', 'False') != 'False':
            # Process IAM roles for the task
            if task_definition.get('taskRoleArn'):
                role_name = task_definition.get('taskRoleArn').split('/')[-1]
                self.iam_role_instance.aws_iam_role(role_name, ftstack)
            if task_definition.get('executionRoleArn'):
                role_name = task_definition.get(
                    'executionRoleArn').split('/')[-1]
                self.iam_role_instance.aws_iam_role(role_name, ftstack)

    def aws_appautoscaling_target(self, cluster_name, service_name):
        service_namespace = 'ecs'
        resource_id = f'service/{cluster_name}/{service_name}'
        logger.debug(
            f"Processing AppAutoScaling target for ECS service: {service_name} in cluster: {cluster_name}...")

        try:
            response = self.provider_instance.aws_clients.appautoscaling_client.describe_scalable_targets(
                ServiceNamespace=service_namespace,
                ResourceIds=[resource_id]
            )
            scalable_targets = response.get('ScalableTargets', [])

            if scalable_targets:
                # We expect only one target per service
                target = scalable_targets[0]
                logger.debug(
                    f"Processing ECS AppAutoScaling Target: {resource_id}")

                resource_name = f"{service_namespace}-{resource_id.replace('/', '-')}"
                attributes = {
                    "id": resource_id,
                    "resource_id": resource_id,
                    "service_namespace": service_namespace,
                    "scalable_dimension": target['ScalableDimension'],
                }
                self.hcl.process_resource(
                    "aws_appautoscaling_target", resource_name, attributes)

                # Processing scaling policies for the target
                self.aws_appautoscaling_policy(
                    service_namespace, resource_id, target['ScalableDimension'])

                self.aws_appautoscaling_scheduled_action(
                    service_namespace, resource_id, target['ScalableDimension'])

            else:
                logger.debug(
                    f"No AppAutoScaling target found for ECS service: {service_name} in cluster: {cluster_name}")

        except Exception as e:
            logger.debug(
                f"Error processing AppAutoScaling target for ECS service: {service_name} in cluster: {cluster_name}: {str(e)}")

    def aws_appautoscaling_policy(self, service_namespace, resource_id, scalable_dimension):
        logger.debug(
            f"Processing AppAutoScaling policies for resource: {resource_id}...")

        try:
            response = self.provider_instance.aws_clients.appautoscaling_client.describe_scaling_policies(
                ServiceNamespace=service_namespace,
                ResourceId=resource_id
            )
            scaling_policies = response.get('ScalingPolicies', [])

            for policy in scaling_policies:
                logger.debug(
                    f"Processing AppAutoScaling Policy: {policy['PolicyName']} for resource: {resource_id}")

                resource_name = f"{service_namespace}-{resource_id.replace('/', '-')}-{policy['PolicyName']}"
                attributes = {
                    "id": f"{policy['PolicyName']}",
                    "resource_id": resource_id,
                    "service_namespace": service_namespace,
                    "scalable_dimension": scalable_dimension,
                    "name": policy['PolicyName'],
                }
                self.hcl.process_resource(
                    "aws_appautoscaling_policy", resource_name, attributes)
        except Exception as e:
            logger.error(
                f"Error processing AppAutoScaling policies for resource: {resource_id}: {str(e)}")

    def aws_appautoscaling_scheduled_action(self, service_namespace, resource_id, scalable_dimension):
        logger.debug(
            f"Processing AppAutoScaling scheduled actions for resource: {resource_id}...")

        try:
            response = self.provider_instance.aws_clients.appautoscaling_client.describe_scheduled_actions(
                ServiceNamespace=service_namespace,
                ResourceId=resource_id
            )
            scheduled_actions = response.get('ScheduledActions', [])

            for action in scheduled_actions:
                logger.debug(
                    f"Processing AppAutoScaling Scheduled Action: {action['ScheduledActionName']} for resource: {resource_id}")

                resource_name = f"{service_namespace}-{resource_id.replace('/', '-')}-{action['ScheduledActionName']}"
                attributes = {
                    "id": action['ScheduledActionName'],
                    "resource_id": resource_id,
                    "service_namespace": service_namespace,
                    "scalable_dimension": scalable_dimension,
                    "name": action['ScheduledActionName'],
                }
                self.hcl.process_resource(
                    "aws_appautoscaling_scheduled_action", resource_name, attributes)
        except Exception as e:
            logger.error(
                f"Error processing AppAutoScaling scheduled actions for resource: {resource_id}: {str(e)}")

    def aws_ecs_account_setting_default(self):
        logger.debug("Processing ECS Account Setting Defaults...")

        settings = self.provider_instance.aws_clients.ecs_client.list_account_settings()[
            "settings"]
        for setting in settings:
            name = setting["name"]
            value = setting["value"]

            logger.debug(f"Processing ECS Account Setting Default: {name}")

            attributes = {
                "id": name,
                "value": value,
            }
            self.hcl.process_resource(
                "aws_ecs_account_setting_default", name.replace("-", "_"), attributes)

    def aws_ecs_tag(self):
        logger.debug("Processing ECS Tags...")

        # Process tags for ECS clusters
        clusters_arns = self.provider_instance.aws_clients.ecs_client.list_clusters()[
            "clusterArns"]
        for cluster_arn in clusters_arns:
            cluster = self.provider_instance.aws_clients.ecs_client.describe_clusters(
                clusters=[cluster_arn])["clusters"][0]
            cluster_name = cluster["clusterName"]
            self.process_tags_for_resource(
                cluster_name, cluster_arn, "aws_ecs_tag")

            # Process tags for ECS services
            services_arns = self.provider_instance.aws_clients.ecs_client.list_services(
                cluster=cluster_arn)["serviceArns"]
            services = self.provider_instance.aws_clients.ecs_client.describe_services(
                cluster=cluster_arn, services=services_arns)["services"]
            for service in services:
                service_name = service["serviceName"]
                service_arn = service["serviceArn"]
                self.process_tags_for_resource(
                    service_name, service_arn, "aws_ecs_tag")

            # Process tags for ECS tasks and task definitions
            tasks_arns = self.provider_instance.aws_clients.ecs_client.list_tasks(
                cluster=cluster_arn)["taskArns"]
            tasks = self.provider_instance.aws_clients.ecs_client.describe_tasks(
                cluster=cluster_arn, tasks=tasks_arns)["tasks"]
            for task in tasks:
                task_arn = task["taskArn"]
                task_definition_arn = task["taskDefinitionArn"]
                self.process_tags_for_resource(
                    task_arn.split("/")[-1], task_arn, "aws_ecs_tag")
                self.process_tags_for_resource(task_definition_arn.split(
                    "/")[-1], task_definition_arn, "aws_ecs_tag")

    def process_tags_for_resource(self, resource_name, resource_arn, resource_type):
        tags = self.provider_instance.aws_clients.ecs_client.list_tags_for_resource(
            resourceArn=resource_arn)["tags"]
        for tag in tags:
            key = tag["key"]
            value = tag["value"]

            logger.debug(
                f"Processing ECS Tag: {key}={value} for {resource_type}: {resource_name}")

            hcl_resource_name = f"{resource_name}-tag-{key}"
            id = resource_arn + "," + key
            attributes = {
                "id": id,
                "resource_arn": resource_arn,
                "key": key,
                "value": value,
            }
            self.hcl.process_resource(
                resource_type, hcl_resource_name.replace("-", "_"), attributes)

    def aws_ecs_task_set(self):
        logger.debug("Processing ECS Task Sets...")

        clusters_arns = self.provider_instance.aws_clients.ecs_client.list_clusters()[
            "clusterArns"]
        for cluster_arn in clusters_arns:
            services_arns = self.provider_instance.aws_clients.ecs_client.list_services(
                cluster=cluster_arn)["serviceArns"]
            services = self.provider_instance.aws_clients.ecs_client.describe_services(
                cluster=cluster_arn, services=services_arns)["services"]

            for service in services:
                service_name = service["serviceName"]
                task_sets = self.provider_instance.aws_clients.ecs_client.list_task_sets(
                    cluster=cluster_arn, service=service_name)["taskSets"]

                for task_set_arn in task_sets:
                    task_set = self.provider_instance.aws_clients.ecs_client.describe_task_sets(
                        cluster=cluster_arn, service=service_name, taskSets=[task_set_arn])["taskSets"][0]
                    task_set_id = task_set["id"]

                    logger.debug(f"Processing ECS Task Set: {task_set_id}")

                    attributes = {
                        "id": task_set_id,
                        "service": service_name,
                        "cluster": cluster_arn,
                        "task_definition": task_set["taskDefinition"],
                    }
                    self.hcl.process_resource(
                        "aws_ecs_task_set", task_set_id.replace("-", "_"), attributes)

    def aws_lb_target_group(self, target_group_arn):
        logger.debug(
            f"Processing Load Balancer Target Group with ARN: {target_group_arn}")

        # Describe the specific target group using the provided ARN
        response = self.provider_instance.aws_clients.elbv2_client.describe_target_groups(
            TargetGroupArns=[target_group_arn]
        )

        for target_group in response["TargetGroups"]:
            tg_arn = target_group["TargetGroupArn"]
            tg_name = target_group["TargetGroupName"]
            logger.debug(f"Processing Load Balancer Target Group: {tg_name}")

            attributes = {
                "id": tg_arn,
                "arn": tg_arn,
                "name": tg_name,
            }

            self.hcl.process_resource(
                "aws_lb_target_group", tg_name, attributes)
            # Call the aws_lb_listener_rule function with the target_group_arn
            self.aws_lb_listener_rule(target_group_arn)
            self.aws_lb_listener(target_group_arn)

    def aws_lb_listener_rule(self, target_group_arn):
        logger.debug(
            f"Processing Load Balancer Listener Rules for Target Group ARN: {target_group_arn}")

        load_balancers = self.provider_instance.aws_clients.elbv2_client.describe_load_balancers()[
            "LoadBalancers"]

        for lb in load_balancers:
            lb_arn = lb["LoadBalancerArn"]
            # logger.debug(f"Processing Load Balancer: {lb_arn}")

            listeners = self.provider_instance.aws_clients.elbv2_client.describe_listeners(
                LoadBalancerArn=lb_arn)["Listeners"]

            for listener in listeners:
                listener_arn = listener["ListenerArn"]
                # logger.debug(f"Processing Load Balancer Listener: {listener_arn}")

                rules = self.provider_instance.aws_clients.elbv2_client.describe_rules(
                    ListenerArn=listener_arn)["Rules"]

                for rule in rules:
                    # Skip rules that don't match the target group ARN
                    if not any(action.get('TargetGroupArn') == target_group_arn for action in rule['Actions']):
                        continue

                    rule_arn = rule["RuleArn"]
                    rule_id = rule_arn.split("/")[-1]
                    if len(rule["Conditions"]) == 0:
                        continue
                    logger.debug(
                        f"    Processing Load Balancer Listener Rule: {rule_id}")

                    attributes = {
                        "id": rule_arn,
                        "condition": rule["Conditions"],
                    }

                    self.hcl.process_resource(
                        "aws_lb_listener_rule", rule_id, attributes)

    def aws_lb_listener(self, target_group_arn):
        logger.debug(
            f"Processing Load Balancer Listeners for Target Group ARN: {target_group_arn}")

        # Get all Load Balancers
        load_balancer_arns = [lb["LoadBalancerArn"]
                              for lb in self.provider_instance.aws_clients.elbv2_client.describe_load_balancers()["LoadBalancers"]]

        # Get all Listeners for the Load Balancers
        for lb_arn in load_balancer_arns:
            paginator = self.provider_instance.aws_clients.elbv2_client.get_paginator(
                "describe_listeners")
            for page in paginator.paginate(LoadBalancerArn=lb_arn):
                for listener in page["Listeners"]:
                    # Check if the target group ARN is in the default actions
                    for action in listener['DefaultActions']:
                        if action['Type'] == 'forward' and any(tg['TargetGroupArn'] == target_group_arn for tg in action['ForwardConfig']['TargetGroups']):
                            listener_arn = listener["ListenerArn"]
                            logger.debug(
                                f"Processing Listener: {listener_arn}")

                            attributes = {
                                "id": listener_arn,
                            }

                            self.hcl.process_resource(
                                "aws_lb_listener", listener_arn.split("/")[-1], attributes)
