from ...utils.hcl import HCL
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.iam_role import IAM
from ...providers.aws.launchtemplate import LaunchTemplate
from ...providers.aws.utils import get_subnet_names
import logging
import inspect

logger = logging.getLogger('finisterra')


class AutoScaling:
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
        self.iam_role_instance = IAM(self.provider_instance, self.hcl)
        self.launchtemplate_instance = LaunchTemplate(
            self.provider_instance, self.hcl)

    def autoscaling(self):
        self.hcl.prepare_folder()

        self.aws_autoscaling_group()
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

    def aws_autoscaling_attachment(self):
        logger.debug(f"Processing AutoScaling Attachments...")

        as_groups = self.provider_instance.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]

            for elb_name in as_group.get("LoadBalancerNames", []):
                logger.debug(
                    f"Processing AutoScaling Attachment: ELB {elb_name} -> ASG: {as_group_name}")

                resource_name = f"{as_group_name}-{elb_name}-attachment"
                attributes = {
                    "id": as_group_name,
                    "elb": elb_name,
                }
                self.hcl.process_resource(
                    "aws_autoscaling_attachment", resource_name.replace("-", "_"), attributes)

    def aws_autoscaling_group(self):
        resource_type = "aws_autoscaling_group"
        # logger.debug(f"Processing AutoScaling Groups...")

        as_groups = self.provider_instance.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        if len(as_groups) > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=len(as_groups))

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]

            # if as_group_name != "xxxx":
            #     continue

            # Check tags to determine if this group is controlled by Elastic Beanstalk or EKS
            is_elasticbeanstalk = any(tag['Key'].startswith(
                'elasticbeanstalk:') for tag in as_group.get('Tags', []))
            is_eks = any(tag['Key'].startswith('eks:')
                         for tag in as_group.get('Tags', []))

            if is_elasticbeanstalk or is_eks:
                logger.debug(
                    f"  Skipping Elastic Beanstalk or EKS AutoScaling Group: {as_group_name}")
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{as_group_name}[/]")
                continue

            logger.debug(f"Processing AutoScaling Group: {as_group_name}")

            id = as_group_name
            attributes = {
                "id": id,
            }

            self.hcl.process_resource(
                resource_type, id, attributes)

            ftstack = "autoscaling"
            # get the autoscaling tags
            if "Tags" in as_group:
                for tag in as_group["Tags"]:
                    if tag["Key"] == "ftstack":
                        ftstack = "stack_"+tag["Value"]
                        break

            self.hcl.add_stack(resource_type, id, ftstack)

            service_linked_role_arn = as_group.get("ServiceLinkedRoleARN", "")
            if service_linked_role_arn:
                service_linked_role_name = service_linked_role_arn.split(
                    '/')[-1]
                self.iam_role_instance.aws_iam_role(
                    service_linked_role_name, ftstack)

            # Here we call the policy processing for this specific group
            self.aws_autoscaling_policy(as_group_name)

            # Check if the AutoScaling group uses a Launch Configuration or Launch Template
            if "LaunchConfigurationName" in as_group:
                lc_name = as_group["LaunchConfigurationName"]
                # Call the method for processing Launch Configurations
                self.aws_launch_configuration(lc_name, ftstack)

            elif "LaunchTemplate" in as_group:
                lt_info = as_group["LaunchTemplate"]
                if "LaunchTemplateId" in lt_info:  # It's possible to have 'LaunchTemplateName' instead of 'LaunchTemplateId'
                    lt_id = lt_info["LaunchTemplateId"]
                    # Call the method for processing Launch Templates
                    # self.aws_launch_template(lt_id, ftstack)
                    self.launchtemplate_instance.aws_launch_template(
                        lt_id, ftstack)

            subnet_ids = as_group.get("VPCZoneIdentifier", "").split(",")
            if subnet_ids:
                subnet_names = get_subnet_names(
                    self.provider_instance.aws_clients, subnet_ids)
                if subnet_names:
                    self.hcl.add_additional_data(
                        resource_type, as_group_name, "subnet_names", subnet_names)

            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{as_group_name}[/]")

    def aws_autoscaling_group_tag(self):
        logger.debug(f"Processing AutoScaling Group Tags...")

        as_groups = self.provider_instance.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]

            for tag in as_group.get("Tags", []):
                key = tag["Key"]
                value = tag["Value"]

                logger.debug(
                    f"Processing AutoScaling Group Tag: {key}={value} for ASG: {as_group_name}")

                resource_name = f"{as_group_name}-tag-{key}"
                attributes = {
                    "id": as_group_name+","+key,
                    "key": key,
                    "value": value,
                }
                self.hcl.process_resource(
                    "aws_autoscaling_group_tag", resource_name.replace("-", "_"), attributes)

    def aws_autoscaling_lifecycle_hook(self):
        logger.debug(f"Processing AutoScaling Lifecycle Hooks...")

        as_groups = self.provider_instance.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]
            hooks = self.provider_instance.aws_clients.autoscaling_client.describe_lifecycle_hooks(
                AutoScalingGroupName=as_group_name)["LifecycleHooks"]

            for hook in hooks:
                hook_name = hook["LifecycleHookName"]
                logger.debug(
                    f"Processing AutoScaling Lifecycle Hook: {hook_name} for ASG: {as_group_name}")

                resource_name = f"{hook_name}".replace(
                    "-", "_")

                attributes = {
                    "id": hook_name,
                    "autoscaling_group_name": as_group_name,
                    # "lifecycle_transition": hook["LifecycleTransition"],
                    # "role_arn": hook["RoleARN"],
                }

                if "NotificationTargetARN" in hook:
                    attributes["notification_target_arn"] = hook["NotificationTargetARN"]

                if "HeartbeatTimeout" in hook:
                    attributes["heartbeat_timeout"] = hook["HeartbeatTimeout"]

                if "DefaultResult" in hook:
                    attributes["default_result"] = hook["DefaultResult"]

                self.hcl.process_resource(
                    "aws_autoscaling_lifecycle_hook", resource_name, attributes)

    def aws_autoscaling_notification(self):
        logger.debug(f"Processing AutoScaling Notifications...")

        as_groups = self.provider_instance.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        notification_types = [
            "autoscaling:EC2_INSTANCE_LAUNCH",
            "autoscaling:EC2_INSTANCE_TERMINATE",
            "autoscaling:EC2_INSTANCE_LAUNCH_ERROR",
            "autoscaling:EC2_INSTANCE_TERMINATE_ERROR",
        ]

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]
            sns_topic_arns = self.get_sns_topic_arns_for_autoscaling_group(
                as_group_name)

            if not sns_topic_arns:
                logger.debug(
                    f"  No SNS topic found for ASG: {as_group_name}. Skipping AutoScaling Notifications.")
                continue

            for sns_topic_arn in sns_topic_arns:
                logger.debug(
                    f"Processing AutoScaling Notification for ASG: {as_group_name} with SNS Topic: {sns_topic_arn}")

                resource_name = f"{as_group_name}-notification-{sns_topic_arn.split(':')[-1]}"
                attributes = {
                    "id": resource_name,
                    "group_names": [as_group_name],
                    "notifications": notification_types,
                    "topic_arn": sns_topic_arn,
                }
                self.hcl.process_resource(
                    "aws_autoscaling_notification", resource_name.replace("-", "_"), attributes)

    def get_sns_topic_arns_for_autoscaling_group(self, as_group_name):
        response = self.provider_instance.aws_clients.autoscaling_client.describe_notification_configurations(
            AutoScalingGroupNames=[as_group_name])
        sns_topic_arns = [config['TopicARN']
                          for config in response['NotificationConfigurations']]
        return sns_topic_arns

    def aws_autoscaling_policy(self, as_group_name):
        logger.debug(
            f"Processing AutoScaling Policies for group: {as_group_name}")

        # Retrieving policies for the specified AutoScaling group
        try:
            response = self.provider_instance.aws_clients.autoscaling_client.describe_policies(
                AutoScalingGroupName=as_group_name)
        except Exception as e:
            logger.error(
                f"Error retrieving policies for AutoScaling group {as_group_name}: {str(e)}")
            return

        policies = response.get("ScalingPolicies", [])
        if not policies:
            logger.debug(
                f"No policies found for AutoScaling group: {as_group_name}")
            return

        for policy in policies:
            policy_name = policy["PolicyName"]
            logger.debug(f"Processing AutoScaling Policy: {policy_name}")

            attributes = {
                "id": policy_name,
                "autoscaling_group_name": as_group_name,
                "adjustment_type": policy["AdjustmentType"],
                "scaling_adjustment": policy["ScalingAdjustment"],
                # ... other attributes you plan to process
            }

            # Optional attributes that may or may not be present in the policy
            if "Cooldown" in policy:
                attributes["cooldown"] = policy["Cooldown"]

            if "MinAdjustmentStep" in policy:
                attributes["min_adjustment_step"] = policy["MinAdjustmentStep"]

            if "EstimatedInstanceWarmup" in policy:
                attributes["estimated_instance_warmup"] = policy["EstimatedInstanceWarmup"]

            # If there are other optional attributes, continue your checks here

            # Process the attributes with your custom function
            self.hcl.process_resource(
                "aws_autoscaling_policy", policy_name.replace("-", "_"), attributes)

            if 'Alarms' in policy:
                for alarm in policy['Alarms']:
                    alarm_name = alarm['AlarmName']
                    self.aws_cloudwatch_metric_alarm(alarm_name)

    def aws_autoscaling_schedule(self):
        logger.debug(f"Processing AutoScaling Schedules...")

        as_groups = self.provider_instance.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]
            scheduled_actions = self.provider_instance.aws_clients.autoscaling_client.describe_scheduled_actions(
                AutoScalingGroupName=as_group_name)["ScheduledUpdateGroupActions"]

            for action in scheduled_actions:
                action_name = action["ScheduledActionName"]
                logger.debug(
                    f"Processing AutoScaling Schedule: {action_name} for ASG: {as_group_name}")

                attributes = {
                    "id": action_name,
                    "name": action_name,
                    "autoscaling_group_name": as_group_name,
                    "desired_capacity": action["DesiredCapacity"],
                    "min_size": action["MinSize"],
                    "max_size": action["MaxSize"],
                }

                if "StartTime" in action:
                    attributes["start_time"] = action["StartTime"].strftime(
                        "%Y-%m-%dT%H:%M:%SZ")

                if "EndTime" in action:
                    attributes["end_time"] = action["EndTime"].strftime(
                        "%Y-%m-%dT%H:%M:%SZ")

                if "Recurrence" in action:
                    attributes["recurrence"] = action["Recurrence"]

                self.hcl.process_resource(
                    "aws_autoscaling_schedule", action_name.replace("-", "_"), attributes)

    def aws_launch_configuration(self, id, ftstack):
        logger.debug(f"Processing Launch Configuration: {id}")

        try:
            response = self.provider_instance.aws_clients.autoscaling_client.describe_launch_configurations(
                LaunchConfigurationNames=[id])
        except Exception as e:
            logger.error(
                f"Error retrieving Launch Configuration {id}: {str(e)}")
            return

        launch_configurations = response.get("LaunchConfigurations", [])
        if not launch_configurations:
            logger.debug(f"No launch configuration found with name: {id}")
            return

        launch_configuration = launch_configurations[0]
        lc_name = launch_configuration["LaunchConfigurationName"]
        logger.debug(f"Processing specific Launch Configuration: {lc_name}")

        attributes = {
            "id": lc_name,
            "image_id": launch_configuration.get("ImageId", ""),
            "instance_type": launch_configuration.get("InstanceType", ""),
            # continue adding all other relevant details you need from launch_configuration
        }

        # If you have optional data that might not be present in every launch configuration,
        # you can add checks before including them in the 'attributes' dictionary.
        if "KeyName" in launch_configuration:
            attributes["key_name"] = launch_configuration["KeyName"]

        if "SecurityGroups" in launch_configuration:
            attributes["security_groups"] = launch_configuration["SecurityGroups"]
            for sg in launch_configuration["SecurityGroups"]:
                self.security_group_instance.aws_security_group(sg, ftstack)

        if "UserData" in launch_configuration:
            attributes["user_data"] = launch_configuration["UserData"]

            self.hcl.add_additional_data(
                "aws_launch_configuration", lc_name, "user_data", attributes["user_data"])

            # self.user_data[lc_name] = attributes["user_data"]

        self.hcl.process_resource(
            "aws_launch_configuration", lc_name.replace("-", "_"), attributes)

    def aws_cloudwatch_metric_alarm(self, alarm_name):
        logger.debug(f"Processing CloudWatch Metric Alarm: {alarm_name}")

        try:
            # Retrieve specific alarm
            alarm = self.provider_instance.aws_clients.cloudwatch_client.describe_alarms(
                AlarmNames=[alarm_name])
        except Exception as e:
            logger.debug(
                f"Error retrieving CloudWatch Alarm {alarm_name}: {str(e)}")
            return  # Exiting the function because there was an error retrieving the alarm

        if not alarm['MetricAlarms']:
            logger.debug(f"No alarm data found for: {alarm_name}")
            return  # Exiting the function because no alarm data was returned

        # Since we expect a specific alarm, we take the first element
        metric_alarm = alarm['MetricAlarms'][0]
        logger.debug(
            f"  Retrieved details for CloudWatch Metric Alarm: {metric_alarm['AlarmName']}")

        attributes = {
            "id": metric_alarm['AlarmName'],
            "metric_name": metric_alarm['MetricName'],
            "namespace": metric_alarm['Namespace'],
        }

        self.hcl.process_resource("aws_cloudwatch_metric_alarm",
                                  metric_alarm['AlarmName'].replace("-", "_"), attributes)
