from ...utils.hcl import HCL
import botocore
import re
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.iam_role import IAM
import logging
import inspect

logger = logging.getLogger('finisterra')


class ElasticBeanstalk:
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

    def elasticbeanstalk(self):
        self.hcl.prepare_folder()
        # self.aws_elastic_beanstalk_application()
        self.aws_elastic_beanstalk_environment()
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

    def aws_elastic_beanstalk_application(self):
        logger.debug("Processing Elastic Beanstalk Applications...")

        applications = self.provider_instance.aws_clients.elasticbeanstalk_client.describe_applications()[
            "Applications"]

        for app in applications:
            app_name = app["ApplicationName"]
            logger.debug(
                f"Processing Elastic Beanstalk Application: {app_name}")

            attributes = {
                "id": app_name,
                "name": app_name,
                "description": app.get("Description", ""),
            }
            self.hcl.process_resource(
                "aws_elastic_beanstalk_application", app_name, attributes)

    def aws_elastic_beanstalk_application_version(self):
        logger.debug("Processing Elastic Beanstalk Application Versions...")

        applications = self.provider_instance.aws_clients.elasticbeanstalk_client.describe_applications()[
            "Applications"]

        for app in applications:
            app_name = app["ApplicationName"]
            versions = self.provider_instance.aws_clients.elasticbeanstalk_client.describe_application_versions(
                ApplicationName=app_name)["ApplicationVersions"]

            for version in versions:
                version_label = version["VersionLabel"]
                version_id = f"{app_name}-{version_label}"
                logger.debug(
                    f"Processing Elastic Beanstalk Application Version: {version_id}")

                source_bundle = version.get("SourceBundle")
                bucket = ""
                bucket_key = ""

                if source_bundle:
                    bucket = source_bundle.get("S3Bucket", "")
                    key = source_bundle.get("S3Key", "")

                attributes = {
                    "id": version_id,
                    "application": app_name,
                    "name": version_label,
                    "description": version.get("Description", ""),
                    "bucket": bucket,
                    "key": key
                }
                self.hcl.process_resource(
                    "aws_elastic_beanstalk_application_version", version_id, attributes)

    def aws_elastic_beanstalk_configuration_template(self):
        logger.debug("Processing Elastic Beanstalk Configuration Templates...")

        applications = self.provider_instance.aws_clients.elasticbeanstalk_client.describe_applications()[
            "Applications"]

        for app in applications:
            app_name = app["ApplicationName"]
            environments = self.provider_instance.aws_clients.elasticbeanstalk_client.describe_environments(
                ApplicationName=app_name)["Environments"]
            templates = {}

            for env in environments:
                try:
                    env_name = env["EnvironmentName"]
                    options = self.provider_instance.aws_clients.elasticbeanstalk_client.describe_configuration_options(
                        ApplicationName=app_name, EnvironmentName=env_name)["Options"]

                    for option in options:
                        namespace = option["Namespace"]
                        name = option.get("OptionName")
                        value = option.get("Value")
                        if namespace.startswith("aws:elasticbeanstalk:"):
                            template_name = namespace.split(":")[-1]
                            if template_name not in templates:
                                templates[template_name] = {
                                    "id": f"{app_name}-{template_name}",
                                    "application": app_name,
                                    "name": template_name,
                                    "options": {},
                                }
                            templates[template_name]["options"][name] = value
                except botocore.exceptions.ClientError as e:
                    logger.error(f"  Error processing KMS Grant: {e}")

                for template_name, template in templates.items():
                    template_id = template["id"]
                    logger.debug(
                        f"Processing Elastic Beanstalk Configuration Template: {template_id}")

                    attributes = {
                        "id": template_id,
                        "application": app_name,
                        "name": template_name,
                        "options": template["options"],
                    }
                    self.hcl.process_resource(
                        "aws_elastic_beanstalk_configuration_template", template_id, attributes)

    def aws_elastic_beanstalk_environment(self):
        resource_type = "aws_elastic_beanstalk_environment"
        logger.debug("Processing Elastic Beanstalk Environments...")

        environments = self.provider_instance.aws_clients.elasticbeanstalk_client.describe_environments()[
            "Environments"]
        if len(environments) > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=len(environments))

        for env in environments:
            env_id = env["EnvironmentId"]
            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{env_id}[/]")

            # if env_id != "xxxxx":
            #     continue
            logger.debug(f"Processing Elastic Beanstalk Environment: {env_id}")
            id = env_id

            ftstack = "beanstalk"
            try:
                tags_response = self.provider_instance.aws_clients.elasticbeanstalk_client.list_tags_for_resource(
                    ResourceArn=env["EnvironmentArn"]
                )
                tags = tags_response.get('ResourceTags', [])
                for tag in tags:
                    if tag['Key'] == 'ftstack':
                        if tag['Value'] != 'beanstalk':
                            ftstack = "stack_"+tag['Value']
                        break
            except Exception as e:
                logger.error(f"Error occurred: {e}")

            attributes = {
                "id": id,
                "name": env["EnvironmentName"],
                "application": env["ApplicationName"],
                "cname_prefix": env.get("CNAMEPrefix", ""),
            }
            self.hcl.process_resource(
                resource_type, id, attributes)

            self.hcl.add_stack(resource_type, id, ftstack)

            try:
                # Retrieve the environment configuration details
                config_settings = self.provider_instance.aws_clients.elasticbeanstalk_client.describe_configuration_settings(
                    ApplicationName=env["ApplicationName"],
                    EnvironmentName=env["EnvironmentName"]
                )

                # Process the Service Role
                service_role = None
                for option_setting in config_settings['ConfigurationSettings'][0]['OptionSettings']:
                    if option_setting['OptionName'] == 'ServiceRole':
                        service_role = option_setting['Value']

                # Process IAM roles
                if service_role:
                    self.service_roles[env_id] = service_role
                    service_role_name = service_role.split('/')[-1]
                    self.iam_role_instance.aws_iam_role(
                        service_role_name, ftstack)

                # Process the EC2 Role
                ec2_instance_profile = None
                for option_setting in config_settings['ConfigurationSettings'][0]['OptionSettings']:
                    if option_setting['OptionName'] == 'IamInstanceProfile':
                        ec2_instance_profile = option_setting['Value']

                if ec2_instance_profile:
                    self.insatce_profiles[env_id] = ec2_instance_profile
                    # self.aws_iam_instance_profile(ec2_instance_profile)
                    instance_profile = self.provider_instance.aws_clients.iam_client.get_instance_profile(
                        InstanceProfileName=ec2_instance_profile)
                    ec2_role = instance_profile['InstanceProfile']['Roles'][0]['Arn']
                    self.ec2_roles[env_id] = ec2_role.split('/')[-1]
                    ec2_role_name = ec2_role.split('/')[-1]
                    self.iam_role_instance.aws_iam_role(ec2_role_name, ftstack)
                    # self.aws_iam_role(ec2_role)

                # Identify the Auto Scaling Group associated with the Elastic Beanstalk environment
                auto_scaling_groups = self.provider_instance.aws_clients.autoscaling_client.describe_auto_scaling_groups()

                for group in auto_scaling_groups['AutoScalingGroups']:
                    # The Elastic Beanstalk environment name is part of the Auto Scaling Group name
                    if re.search(env_id, group['AutoScalingGroupName']):
                        auto_scaling_group = group
                        break

                security_group_ids = []
                # Get the Launch Configuration or Launch Template associated with the Auto Scaling Group
                if 'LaunchConfigurationName' in auto_scaling_group:
                    launch_config_name = auto_scaling_group['LaunchConfigurationName']
                    launch_config = self.provider_instance.aws_clients.autoscaling_client.describe_launch_configurations(
                        LaunchConfigurationNames=[launch_config_name]
                    )['LaunchConfigurations'][0]
                    security_group_names = launch_config['SecurityGroups']
                    for sg in security_group_names:
                        # Get the id by the name using boto3
                        security_group_id = self.provider_instance.aws_clients.ec2_client.describe_security_groups(
                            GroupNames=[sg]
                        )['SecurityGroups'][0]
                        security_group_ids.append(security_group_id['GroupId'])
                elif 'LaunchTemplate' in auto_scaling_group:
                    launch_template_id = auto_scaling_group['LaunchTemplate']['LaunchTemplateId']
                    launch_template_version = self.provider_instance.aws_clients.ec2_client.describe_launch_template_versions(
                        LaunchTemplateId=launch_template_id
                    )['LaunchTemplateVersions'][0]['LaunchTemplateData']
                    security_group_ids = launch_template_version['SecurityGroupIds']

                # Process security groups
                if security_group_ids:
                    self.security_groups[env_id] = security_group_ids[0]
                    for sg in security_group_ids:
                        self.security_group_instance.aws_security_group(
                            sg, ftstack)
                    # self.aws_security_group(security_group_ids)

            except Exception as e:
                # General exception handling if you expect other types of exceptions to be possible
                logger.error(f"An unexpected error occurred: {e}")
