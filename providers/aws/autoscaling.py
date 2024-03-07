import os
from utils.hcl import HCL
from providers.aws.security_group import SECURITY_GROUP
from providers.aws.iam_role import IAM_ROLE
from providers.aws.launchtemplate import LaunchTemplate

class AutoScaling:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {        }
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.workspace_id = workspace_id
        self.modules = modules
        self.hcl = HCL(self.schema_data, self.provider_name)
        self.aws_account_id = aws_account_id
        self.user_data = {}

        self.hcl.region = region
        self.hcl.account_id = aws_account_id



        self.security_group_instance = SECURITY_GROUP(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)        
        self.iam_role_instance = IAM_ROLE(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)        
        self.launchtemplate_instance = LaunchTemplate(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)

    def get_subnet_names(self, subnet_ids):
        subnet_names = []
        for subnet_id in subnet_ids:
            try:
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

            except Exception as e:
                print(f"Error occurred while retrieving subnet information for Subnet ID: {subnet_id}")
                print(f"Error message: {str(e)}")

        return subnet_names

    def autoscaling(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_autoscaling_group()
        self.hcl.refresh_state()
        self.hcl.request_tf_code()



    def aws_autoscaling_attachment(self):
        print("Processing AutoScaling Attachments...")

        as_groups = self.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]

            for elb_name in as_group.get("LoadBalancerNames", []):
                print(
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
        print("Processing AutoScaling Groups...")

        as_groups = self.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]

            # if as_group_name != "production-noovie-web-AutoScalingGroup-1MZ5FBASQRUJL":
            #     continue

            # Check tags to determine if this group is controlled by Elastic Beanstalk or EKS
            is_elasticbeanstalk = any(tag['Key'].startswith(
                'elasticbeanstalk:') for tag in as_group.get('Tags', []))
            is_eks = any(tag['Key'].startswith('eks:')
                         for tag in as_group.get('Tags', []))

            if is_elasticbeanstalk or is_eks:
                print(
                    f"  Skipping Elastic Beanstalk or EKS AutoScaling Group: {as_group_name}")
                continue  # Skip this AutoScaling group and move to the next

            print(f"Processing AutoScaling Group: {as_group_name}")

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
                service_linked_role_name = service_linked_role_arn.split('/')[-1]
                self.iam_role_instance.aws_iam_role(service_linked_role_name, ftstack)

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
                    self.launchtemplate_instance.aws_launch_template(lt_id, ftstack)

            subnet_ids = as_group.get("VPCZoneIdentifier", "").split(",")
            if subnet_ids:
                subnet_names = self.get_subnet_names(subnet_ids)
                if subnet_names:
                    self.hcl.add_additional_data(
                        resource_type, as_group_name, "subnet_names", subnet_names)

    def aws_autoscaling_group_tag(self):
        print("Processing AutoScaling Group Tags...")

        as_groups = self.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]

            for tag in as_group.get("Tags", []):
                key = tag["Key"]
                value = tag["Value"]

                print(
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
        print("Processing AutoScaling Lifecycle Hooks...")

        as_groups = self.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]
            hooks = self.aws_clients.autoscaling_client.describe_lifecycle_hooks(
                AutoScalingGroupName=as_group_name)["LifecycleHooks"]

            for hook in hooks:
                hook_name = hook["LifecycleHookName"]
                print(
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
        print("Processing AutoScaling Notifications...")

        as_groups = self.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
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
                print(
                    f"  No SNS topic found for ASG: {as_group_name}. Skipping AutoScaling Notifications.")
                continue

            for sns_topic_arn in sns_topic_arns:
                print(
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
        response = self.aws_clients.autoscaling_client.describe_notification_configurations(
            AutoScalingGroupNames=[as_group_name])
        sns_topic_arns = [config['TopicARN']
                          for config in response['NotificationConfigurations']]
        return sns_topic_arns

    def aws_autoscaling_policy(self, as_group_name):
        print(f"Processing AutoScaling Policies for group: {as_group_name}")

        # Retrieving policies for the specified AutoScaling group
        try:
            response = self.aws_clients.autoscaling_client.describe_policies(
                AutoScalingGroupName=as_group_name)
        except Exception as e:
            print(
                f"Error retrieving policies for AutoScaling group {as_group_name}: {str(e)}")
            return

        policies = response.get("ScalingPolicies", [])
        if not policies:
            print(f"No policies found for AutoScaling group: {as_group_name}")
            return

        for policy in policies:
            policy_name = policy["PolicyName"]
            print(f"Processing AutoScaling Policy: {policy_name}")

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
        print("Processing AutoScaling Schedules...")

        as_groups = self.aws_clients.autoscaling_client.describe_auto_scaling_groups()[
            "AutoScalingGroups"]

        for as_group in as_groups:
            as_group_name = as_group["AutoScalingGroupName"]
            scheduled_actions = self.aws_clients.autoscaling_client.describe_scheduled_actions(
                AutoScalingGroupName=as_group_name)["ScheduledUpdateGroupActions"]

            for action in scheduled_actions:
                action_name = action["ScheduledActionName"]
                print(
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

    # def aws_launch_template(self, id, ftstack):
    #     print(f"Processing Launch Template: {id}")

    #     try:
    #         response = self.aws_clients.ec2_client.describe_launch_templates(
    #             LaunchTemplateIds=[id])
    #     except Exception as e:
    #         print(f"Error retrieving Launch Template {id}: {str(e)}")
    #         return

    #     launch_templates = response.get("LaunchTemplates", [])
    #     if not launch_templates:
    #         print(f"No launch template found with ID: {id}")
    #         return

    #     launch_template = launch_templates[0]
    #     lt_name = launch_template["LaunchTemplateName"]
    #     print(f"Processing specific Launch Template: {lt_name}")

    #     default_version = launch_template.get("DefaultVersionNumber")
    #     try:
    #         response_version = self.aws_clients.ec2_client.describe_launch_template_versions(
    #             LaunchTemplateId=id,
    #             Versions=[str(default_version)]
    #         )
    #     except Exception as e:
    #         print(
    #             f"Error retrieving version details for Launch Template {lt_name}: {str(e)}")
    #         return

    #     lt_data = response_version["LaunchTemplateVersions"][0]["LaunchTemplateData"]

    #     attributes = {
    #         "id": lt_name,
    #         "image_id": lt_data.get("ImageId", ""),
    #         "instance_type": lt_data.get("InstanceType", ""),
    #     }

    #     # If you have optional data that might not be present in every launch template,
    #     # you can add checks before including them in the 'attributes' dictionary.
    #     if "KeyName" in lt_data:
    #         attributes["key_name"] = lt_data["KeyName"]

    #     if "SecurityGroupIds" in lt_data:
    #         attributes["security_group_ids"] = lt_data["SecurityGroupIds"]
    #         for sg in lt_data["SecurityGroupIds"]:
    #             self.security_group_instance.aws_security_group(sg, ftstack)

    #     if "UserData" in lt_data:
    #         attributes["user_data"] = lt_data["UserData"]

    #         self.hcl.add_additional_data(
    #             "aws_launch_template", lt_name, "user_data", attributes["user_data"])
            
    #         self.user_data[lt_name] = attributes["user_data"]


    #     self.hcl.process_resource(
    #         "aws_launch_template", lt_name.replace("-", "_"), attributes)

    def aws_launch_configuration(self, id, ftstack):
        print(f"Processing Launch Configuration: {id}")

        try:
            response = self.aws_clients.autoscaling_client.describe_launch_configurations(
                LaunchConfigurationNames=[id])
        except Exception as e:
            print(f"Error retrieving Launch Configuration {id}: {str(e)}")
            return

        launch_configurations = response.get("LaunchConfigurations", [])
        if not launch_configurations:
            print(f"No launch configuration found with name: {id}")
            return

        launch_configuration = launch_configurations[0]
        lc_name = launch_configuration["LaunchConfigurationName"]
        print(f"Processing specific Launch Configuration: {lc_name}")

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

            self.user_data[lc_name] = attributes["user_data"]


        self.hcl.process_resource(
            "aws_launch_configuration", lc_name.replace("-", "_"), attributes)

    def aws_cloudwatch_metric_alarm(self, alarm_name):
        print(f"Processing CloudWatch Metric Alarm: {alarm_name}")

        try:
            # Retrieve specific alarm
            alarm = self.aws_clients.cloudwatch_client.describe_alarms(
                AlarmNames=[alarm_name])
        except Exception as e:
            print(f"Error retrieving CloudWatch Alarm {alarm_name}: {str(e)}")
            return  # Exiting the function because there was an error retrieving the alarm

        if not alarm['MetricAlarms']:
            print(f"No alarm data found for: {alarm_name}")
            return  # Exiting the function because no alarm data was returned

        # Since we expect a specific alarm, we take the first element
        metric_alarm = alarm['MetricAlarms'][0]
        print(
            f"  Retrieved details for CloudWatch Metric Alarm: {metric_alarm['AlarmName']}")

        attributes = {
            "id": metric_alarm['AlarmName'],
            "metric_name": metric_alarm['MetricName'],
            "namespace": metric_alarm['Namespace'],
        }

        self.hcl.process_resource("aws_cloudwatch_metric_alarm",
                                  metric_alarm['AlarmName'].replace("-", "_"), attributes)
