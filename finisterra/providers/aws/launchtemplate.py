from ...utils.hcl import HCL
from ...providers.aws.utils import get_subnet_names
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.kms import KMS
import logging
import inspect

logger = logging.getLogger('finisterra')


class LaunchTemplate:
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
        self.kms_instance = KMS(self.provider_instance, self.hcl)

    def launchtemplate(self):
        self.hcl.prepare_folder()
        self.aws_launch_template()
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

    def aws_launch_template(self, launch_template_id=None, ftstack=None):
        logger.debug("Processing AWS Launch Templates...")
        # If launch_template_id is not provided, process all launch templates
        if launch_template_id is None:
            try:
                all_templates_response = self.provider_instance.aws_clients.ec2_client.describe_launch_templates()
            except Exception as e:
                # Catch-all for any other exceptions
                logger.error(f"Unexpected error: {e}")
                return
            if 'LaunchTemplates' not in all_templates_response or not all_templates_response['LaunchTemplates']:
                logger.debug("No launch templates found!")
                return

            if len(all_templates_response['LaunchTemplates']) > 0:
                self.task = self.provider_instance.progress.add_task(f"[cyan]Processing {self.__class__.__name__}...", total=len(
                    all_templates_response['LaunchTemplates']))

            for template in all_templates_response['LaunchTemplates']:
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{template['LaunchTemplateId']}[/]")
                self.process_individual_launch_template(
                    template['LaunchTemplateId'], ftstack)
        else:
            # Process the specified launch template
            self.process_individual_launch_template(
                launch_template_id, ftstack)

    def process_individual_launch_template(self, launch_template_id, ftstack):
        resource_type = "aws_launch_template"
        try:
            response = self.provider_instance.aws_clients.ec2_client.describe_launch_template_versions(
                LaunchTemplateId=launch_template_id,
                Versions=['$Latest']
            )
        except Exception as e:
            # Catch-all for any other exceptions
            logger.error(f"Unexpected error: {e}")
            return

        # Check if we have the launch template versions in the response
        if 'LaunchTemplateVersions' not in response or not response['LaunchTemplateVersions']:
            logger.debug(
                f"Launch template with ID '{launch_template_id}' not found!")
            return

        latest_version = response['LaunchTemplateVersions'][0]
        launch_template_data = latest_version['LaunchTemplateData']

        logger.debug(
            f"Processing Launch Template: {latest_version['LaunchTemplateName']} with ID: {launch_template_id}")

        id = launch_template_id

        # if id != "xxxx":
        #     return

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

        # security_groups
        security_group_ids = launch_template_data.get("SecurityGroupIds", [])
        for security_group_id in security_group_ids:
            self.security_group_instance.aws_security_group(
                security_group_id, ftstack)

        # Process KMS Key for EBS Volume
        if 'BlockDeviceMappings' in launch_template_data:
            for mapping in launch_template_data['BlockDeviceMappings']:
                if 'Ebs' in mapping and 'KmsKeyId' in mapping['Ebs']:
                    kms_key_id = mapping['Ebs']['KmsKeyId']
                    logger.debug(f"Found KMS Key ID for EBS: {kms_key_id}")
                    self.kms_instance.aws_kms_key(kms_key_id, ftstack)
                    break  # Assuming we need the first KMS Key ID found

        network_interfaces = launch_template_data.get("NetworkInterfaces", [])
        for network_interface in network_interfaces:
            security_groups = network_interface.get("Groups", [])
            for security_group in security_groups:
                self.security_group_instance.aws_security_group(
                    security_group, ftstack)
            subnet_id = network_interface.get("SubnetId")
            if subnet_id:
                subnet_names = get_subnet_names(
                    self.provider_instance.aws_clients, [subnet_id])
                if subnet_names:
                    self.hcl.add_additional_data(
                        resource_type, id, "subnet_name", subnet_names[0])

        else:
            logger.debug(
                "No Block Device Mappings with EBS found in the Launch Template.")
