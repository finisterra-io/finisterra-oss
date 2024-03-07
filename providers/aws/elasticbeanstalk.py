import os
from utils.hcl import HCL
import botocore
import re
from providers.aws.security_group import SECURITY_GROUP
from providers.aws.iam_role import IAM_ROLE

class ElasticBeanstalk:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.s3Bucket = s3Bucket
        self.dynamoDBTable = dynamoDBTable
        self.state_key = state_key
        self.aws_account_id = aws_account_id
        
        self.workspace_id = workspace_id
        self.modules = modules
        if not hcl:
            self.hcl = HCL(self.schema_data, self.provider_name)
        else:
            self.hcl = hcl

            
        self.service_roles = {}
        self.ec2_roles = {}
        self.insatce_profiles = {}
        self.security_groups = {}


        self.security_group_instance = SECURITY_GROUP(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.iam_role_instance = IAM_ROLE(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)


    def elasticbeanstalk(self):
        self.hcl.prepare_folder(os.path.join("generated"))
        # self.aws_elastic_beanstalk_application()
        self.aws_elastic_beanstalk_environment()

        self.hcl.refresh_state()

        self.hcl.request_tf_code()

    def aws_elastic_beanstalk_application(self):
        print("Processing Elastic Beanstalk Applications...")

        applications = self.aws_clients.elasticbeanstalk_client.describe_applications()[
            "Applications"]

        for app in applications:
            app_name = app["ApplicationName"]
            print(f"Processing Elastic Beanstalk Application: {app_name}")

            attributes = {
                "id": app_name,
                "name": app_name,
                "description": app.get("Description", ""),
            }
            self.hcl.process_resource(
                "aws_elastic_beanstalk_application", app_name, attributes)

    def aws_elastic_beanstalk_application_version(self):
        print("Processing Elastic Beanstalk Application Versions...")

        applications = self.aws_clients.elasticbeanstalk_client.describe_applications()[
            "Applications"]

        for app in applications:
            app_name = app["ApplicationName"]
            versions = self.aws_clients.elasticbeanstalk_client.describe_application_versions(
                ApplicationName=app_name)["ApplicationVersions"]

            for version in versions:
                version_label = version["VersionLabel"]
                version_id = f"{app_name}-{version_label}"
                print(
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
        print("Processing Elastic Beanstalk Configuration Templates...")

        applications = self.aws_clients.elasticbeanstalk_client.describe_applications()[
            "Applications"]

        for app in applications:
            app_name = app["ApplicationName"]
            environments = self.aws_clients.elasticbeanstalk_client.describe_environments(
                ApplicationName=app_name)["Environments"]
            templates = {}

            for env in environments:
                try:
                    env_name = env["EnvironmentName"]
                    options = self.aws_clients.elasticbeanstalk_client.describe_configuration_options(
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
                    print(f"  Error processing KMS Grant: {e}")

                for template_name, template in templates.items():
                    template_id = template["id"]
                    print(
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
        print("Processing Elastic Beanstalk Environments...")

        environments = self.aws_clients.elasticbeanstalk_client.describe_environments()["Environments"]

        for env in environments:
            env_id = env["EnvironmentId"]

            # if env_id != "e-asi52zmcu8":
            #     continue
            print(f"Processing Elastic Beanstalk Environment: {env_id}")
            id = env_id

            ftstack = "beanstalk"
            try:
                tags_response = self.aws_clients.elasticbeanstalk_client.list_tags_for_resource(
                    ResourceArn=env["EnvironmentArn"]
                )
                tags = tags_response.get('ResourceTags', [])
                for tag in tags:
                    if tag['Key'] == 'ftstack':
                        if tag['Value'] != 'beanstalk':
                            ftstack = "stack_"+tag['Value']
                        break
            except Exception as e:
                print("Error occurred: ", e)

            attributes = {
                "id": id,
                "name": env["EnvironmentName"],
                "application": env["ApplicationName"],
                "cname_prefix": env.get("CNAMEPrefix", ""),
            }
            self.hcl.process_resource(
                resource_type, id, attributes)
            
            self.hcl.add_stack(resource_type, id, ftstack)

            # Retrieve the environment configuration details
            config_settings = self.aws_clients.elasticbeanstalk_client.describe_configuration_settings(
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
                self.iam_role_instance.aws_iam_role(service_role_name, ftstack)

            # Process the EC2 Role
            ec2_instance_profile = None
            for option_setting in config_settings['ConfigurationSettings'][0]['OptionSettings']:
                if option_setting['OptionName'] == 'IamInstanceProfile':
                    ec2_instance_profile = option_setting['Value']

            if ec2_instance_profile:
                self.insatce_profiles[env_id] = ec2_instance_profile
                # self.aws_iam_instance_profile(ec2_instance_profile)
                instance_profile = self.aws_clients.iam_client.get_instance_profile(
                    InstanceProfileName=ec2_instance_profile)
                ec2_role = instance_profile['InstanceProfile']['Roles'][0]['Arn']
                self.ec2_roles[env_id] = ec2_role.split('/')[-1]
                ec2_role_name = ec2_role.split('/')[-1]
                self.iam_role_instance.aws_iam_role(ec2_role_name, ftstack)
                # self.aws_iam_role(ec2_role)

            # Identify the Auto Scaling Group associated with the Elastic Beanstalk environment
            auto_scaling_groups = self.aws_clients.autoscaling_client.describe_auto_scaling_groups()

            for group in auto_scaling_groups['AutoScalingGroups']:
                # The Elastic Beanstalk environment name is part of the Auto Scaling Group name
                if re.search(env_id, group['AutoScalingGroupName']):
                    auto_scaling_group = group
                    break

            security_group_ids = []
            # Get the Launch Configuration or Launch Template associated with the Auto Scaling Group
            if 'LaunchConfigurationName' in auto_scaling_group:
                launch_config_name = auto_scaling_group['LaunchConfigurationName']
                launch_config = self.aws_clients.autoscaling_client.describe_launch_configurations(
                    LaunchConfigurationNames=[launch_config_name]
                )['LaunchConfigurations'][0]
                security_group_names = launch_config['SecurityGroups']
                for sg in security_group_names:
                    #Get the id by the name using boto3
                    security_group_id = self.aws_clients.ec2_client.describe_security_groups(
                        GroupNames=[sg]
                    )['SecurityGroups'][0]
                    security_group_ids.append(security_group_id['GroupId'])
            elif 'LaunchTemplate' in auto_scaling_group:
                launch_template_id = auto_scaling_group['LaunchTemplate']['LaunchTemplateId']
                launch_template_version = self.aws_clients.ec2_client.describe_launch_template_versions(
                    LaunchTemplateId=launch_template_id
                )['LaunchTemplateVersions'][0]['LaunchTemplateData']
                security_group_ids = launch_template_version['SecurityGroupIds']

            # Process security groups
            if security_group_ids:
                self.security_groups[env_id] = security_group_ids[0]
                for sg in security_group_ids:
                    self.security_group_instance.aws_security_group(sg, ftstack)
                # self.aws_security_group(security_group_ids)

