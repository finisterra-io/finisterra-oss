import os
from utils.hcl import HCL
from providers.aws.security_group import SECURITY_GROUP
from providers.aws.kms import KMS

class LaunchTemplate:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.aws_account_id = aws_account_id

        self.workspace_id = workspace_id
        self.modules = modules
        if hcl:
            self.hcl = hcl
        else:
            self.hcl = HCL(self.schema_data, self.provider_name)

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


        self.security_group_instance = SECURITY_GROUP(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.kms_instance = KMS(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)

    def launchtemplate(self):
        self.hcl.prepare_folder(os.path.join("generated"))
        self.aws_launch_template()
        self.hcl.refresh_state()
        self.hcl.request_tf_code()

    def aws_launch_template(self, launch_template_id=None, ftstack=None):
        print("Processing AWS Launch Templates...")


        # If launch_template_id is not provided, process all launch templates
        if launch_template_id is None:
            all_templates_response = self.aws_clients.ec2_client.describe_launch_templates()
            if 'LaunchTemplates' not in all_templates_response or not all_templates_response['LaunchTemplates']:
                print("No launch templates found!")
                return

            for template in all_templates_response['LaunchTemplates']:
                self.process_individual_launch_template(template['LaunchTemplateId'], ftstack)
        else:
            # Process the specified launch template
            self.process_individual_launch_template(launch_template_id, ftstack)

    def process_individual_launch_template(self, launch_template_id, ftstack):
        resource_type = "aws_launch_template"
        response = self.aws_clients.ec2_client.describe_launch_template_versions(
            LaunchTemplateId=launch_template_id,
            Versions=['$Latest']
        )

        # Check if we have the launch template versions in the response
        if 'LaunchTemplateVersions' not in response or not response['LaunchTemplateVersions']:
            print(f"Launch template with ID '{launch_template_id}' not found!")
            return

        latest_version = response['LaunchTemplateVersions'][0]
        launch_template_data = latest_version['LaunchTemplateData']

        print(f"Processing Launch Template: {latest_version['LaunchTemplateName']} with ID: {launch_template_id}")

        id = launch_template_id

        attributes = {
            "id": id,
            "name": latest_version['LaunchTemplateName'],
            "version": latest_version['VersionNumber'],
        }

        if not ftstack:
            ftstack = "launchtemplate"

        self.hcl.process_resource(
            resource_type, id, attributes)
        self.hcl.add_stack(resource_type, id, ftstack)
        
        
        #security_groups
        security_group_ids = launch_template_data.get("SecurityGroupIds", [])
        for security_group_id in security_group_ids:
            self.security_group_instance.aws_security_group(security_group_id, ftstack)
        
        # Process KMS Key for EBS Volume
        if 'BlockDeviceMappings' in launch_template_data:
            for mapping in launch_template_data['BlockDeviceMappings']:
                if 'Ebs' in mapping and 'KmsKeyId' in mapping['Ebs']:
                    kms_key_id = mapping['Ebs']['KmsKeyId']
                    print(f"Found KMS Key ID for EBS: {kms_key_id}")
                    self.kms_instance.aws_kms_key(kms_key_id, ftstack)
                    break  # Assuming we need the first KMS Key ID found
        else:
            print("No Block Device Mappings with EBS found in the Launch Template.")
