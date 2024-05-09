from ...utils.hcl import HCL
import base64
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.kms import KMS
from ...providers.aws.iam_role import IAM
import logging
from botocore.exceptions import ClientError
import inspect
import botocore
from ...providers.aws.utils import get_vpc_name

logger = logging.getLogger('finisterra')


class EC2:
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
        self.iam_role_instance = IAM(self.provider_instance, self.hcl)

    def decode_base64(self, encoded_str):
        if encoded_str is not None:
            # Decode the base64 string
            decoded_bytes = base64.b64decode(encoded_str)
            # Convert the bytes to a string
            decoded_str = decoded_bytes.decode('utf-8')
            return decoded_str
        else:
            return "No data to decode."

    def ec2_get_user_data(self, instance_id):
        response = self.provider_instance.aws_clients.ec2_client.describe_instance_attribute(
            InstanceId=instance_id,
            Attribute='userData'
        )
        if "UserData" in response:
            if "value" in response["UserData"]:
                return self.decode_base64(response["UserData"]["Value"])
        return None

    def get_subnet_name_ec2(self, subnet_id):
        subnet_name = ""
        response = self.provider_instance.aws_clients.ec2_client.describe_subnets(SubnetIds=[
            subnet_id])

        # Check if 'Subnets' key exists and it's not empty
        if not response or 'Subnets' not in response or not response['Subnets']:
            logger.debug(
                f"No subnet information found for Subnet ID: {subnet_id}")
            return ""

        # Extract the 'Tags' key safely using get
        subnet_tags = response['Subnets'][0].get('Tags', [])

        # Extract the subnet name from the tags
        subnet_name = next(
            (tag['Value'] for tag in subnet_tags if tag['Key'] == 'Name'), None)

        return subnet_name

    def ec2_get_device_name(self, volume_id):
        if not volume_id:
            return None

        response = self.provider_instance.aws_clients.ec2_client.describe_volumes(VolumeIds=[
            volume_id])

        # Check if the volume exists and has attachments
        if response["Volumes"] and response["Volumes"][0]["Attachments"]:
            return response["Volumes"][0]["Attachments"][0]["Device"]

        return None

    def get_kms_alias(self, kms_key_id):
        try:
            value = ""
            response = self.provider_instance.aws_clients.kms_client.list_aliases()
            aliases = response.get('Aliases', [])
            while 'NextMarker' in response:
                response = self.provider_instance.aws_clients.kms_client.list_aliases(
                    Marker=response['NextMarker'])
                aliases.extend(response.get('Aliases', []))
            for alias in aliases:
                if 'TargetKeyId' in alias and alias['TargetKeyId'] == kms_key_id.split('/')[-1]:
                    value = alias['AliasName']
                    break
            return value
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'AccessDeniedException':
                return ""
            else:
                raise e

    def ec2(self):
        self.hcl.prepare_folder()

        self.aws_instance()
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
            self.provider_instance.progress.update(
                self.task, description=f"[cyan]{self.__class__.__name__} [bold]No resources found[/]", total=self.provider_instance.progress.tasks[self.task].total+1)
            self.provider_instance.progress.update(self.task, advance=1)

    def aws_ami(self):
        logger.debug(f"Processing AMIs...")

        images = self.provider_instance.aws_clients.ec2_client.describe_images(Owners=["self"])[
            "Images"]

        for image in images:
            image_id = image["ImageId"]
            logger.debug(f"Processing AMI: {image_id}")

            attributes = {
                "id": image_id,
                "name": image["Name"],
                "description": image.get("Description", ""),
                "architecture": image["Architecture"],
                "virtualization_type": image["VirtualizationType"],
            }
            self.hcl.process_resource(
                "aws_ami", image_id.replace("-", "_"), attributes
            )

    def aws_ami_launch_permission(self):
        logger.debug(f"Processing AMI Launch Permissions...")

        images = self.provider_instance.aws_clients.ec2_client.describe_images(Owners=["self"])[
            "Images"]

        for image in images:
            image_id = image["ImageId"]

            launch_permissions = self.provider_instance.aws_clients.ec2_client.describe_image_attribute(
                ImageId=image_id, Attribute="launchPermission")["LaunchPermissions"]

            for permission in launch_permissions:
                user_id = permission["UserId"]
                logger.debug(
                    f"Processing Launch Permission for AMI: {image_id}, User: {user_id}")

                attributes = {
                    "id": f"{image_id}-{user_id}",
                    "image_id": image_id,
                    "user_id": user_id,
                }
                self.hcl.process_resource(
                    "aws_ami_launch_permission", attributes["id"].replace(
                        "-", "_"), attributes
                )

    def aws_ec2_capacity_reservation(self):
        logger.debug(f"Processing EC2 Capacity Reservations...")

        capacity_reservations = self.provider_instance.aws_clients.ec2_client.describe_capacity_reservations()[
            "CapacityReservations"]

        for reservation in capacity_reservations:
            reservation_id = reservation["CapacityReservationId"]
            logger.debug(
                f"Processing EC2 Capacity Reservation: {reservation_id}")

            attributes = {
                "id": reservation_id,
                "availability_zone": reservation["AvailabilityZone"],
                "instance_type": reservation["InstanceType"],
                "instance_platform": reservation["InstancePlatform"],
                "instance_count": reservation["TotalInstanceCount"],
                "tenancy": reservation["Tenancy"],
                "ebs_optimized": reservation["EbsOptimized"],
                "end_date_type": reservation["EndDateType"],
                "ephemeral_storage": reservation["EphemeralStorage"],
                "instance_match_criteria": reservation["InstanceMatchCriteria"],
            }
            if "EndDate" in reservation:
                attributes["end_date"] = reservation["EndDate"].isoformat

    def aws_ec2_host(self):
        logger.debug(f"Processing EC2 Dedicated Hosts...")

        hosts = self.provider_instance.aws_clients.ec2_client.describe_hosts()[
            "Hosts"]

        for host in hosts:
            host_id = host["HostId"]
            logger.debug(f"Processing EC2 Dedicated Host: {host_id}")

            attributes = {
                "id": host_id,
                "availability_zone": host["AvailabilityZone"],
                "instance_type": host["InstanceType"],
                "auto_placement": host["AutoPlacement"],
                "host_recovery": host["HostRecovery"],
            }
            if "Arn" in host:
                attributes["arn"] = host["Arn"]

            self.hcl.process_resource(
                "aws_ec2_host", host_id.replace("-", "_"), attributes
            )

    def aws_ec2_tag(self):
        logger.debug(f"Processing EC2 Tags...")

        resources = self.provider_instance.aws_clients.ec2_client.describe_tags()
        for resource in resources["Tags"]:
            resource_id = resource["ResourceId"]
            resource_type = resource["ResourceType"]
            key = resource["Key"]
            value = resource["Value"]

            tag_id = f"{resource_id},{key}"
            logger.debug(f"Processing EC2 Tag: {tag_id}")

            attributes = {
                "id": tag_id,
                "resource_id": resource_id,
                "key": key,
                "value": value,
            }
            self.hcl.process_resource(
                "aws_ec2_tag", tag_id.replace("-", "_"), attributes)

    def aws_eip(self, allocation_id):
        logger.debug(f"Processing Elastic IP: {allocation_id}")

        eips = self.provider_instance.aws_clients.ec2_client.describe_addresses(
            AllocationIds=[allocation_id])
        if not eips["Addresses"]:
            logger.debug(
                f"  No Elastic IP found for Allocation ID: {allocation_id}")
            return

        eip = eips["Addresses"][0]

        attributes = {
            "id": allocation_id,
            "public_ip": eip["PublicIp"],
        }

        if "InstanceId" in eip:
            attributes["instance"] = eip["InstanceId"]

        if "NetworkInterfaceId" in eip:
            attributes["network_interface"] = eip["NetworkInterfaceId"]

        if "PrivateIpAddress" in eip:
            attributes["private_ip"] = eip["PrivateIpAddress"]

        self.hcl.process_resource(
            "aws_eip", allocation_id.replace("-", "_"), attributes)

    def aws_eip_association(self):
        logger.debug(f"Processing Elastic IP Associations...")

        eips = self.provider_instance.aws_clients.ec2_client.describe_addresses()
        for eip in eips["Addresses"]:
            if "AssociationId" in eip:
                association_id = eip["AssociationId"]
                logger.debug(
                    f"Processing Elastic IP Association: {association_id}")

                attributes = {
                    "id": association_id,
                    "allocation_id": eip["AllocationId"],
                }

                if "InstanceId" in eip:
                    attributes["instance_id"] = eip["InstanceId"]

                if "NetworkInterfaceId" in eip:
                    attributes["network_interface_id"] = eip["NetworkInterfaceId"]

                if "PrivateIpAddress" in eip:
                    attributes["private_ip_address"] = eip["PrivateIpAddress"]

                self.hcl.process_resource(
                    "aws_eip_association", association_id.replace("-", "_"), attributes)

    def is_managed_by_auto_scaling_group(self, instance_id):
        response = self.provider_instance.aws_clients.autoscaling_client.describe_auto_scaling_instances(InstanceIds=[
            instance_id])
        return bool(response["AutoScalingInstances"])

    def aws_instance(self):
        resource_type = "aws_instance"
        # logger.debug(f"Processing EC2 Instances...")

        if self.provider_instance.filters:
            instances = self.provider_instance.aws_clients.ec2_client.describe_instances(
                Filters=self.provider_instance.filters)
        else:
            instances = self.provider_instance.aws_clients.ec2_client.describe_instances()
        total = 0
        for reservation in instances["Reservations"]:
            total += len(reservation["Instances"])
        self.task = self.provider_instance.progress.add_task(
            f"[cyan]Processing {self.__class__.__name__}...", total=total)

        instance_name = ""
        for reservation in instances["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{instance_id}[/]")

                if self.is_managed_by_auto_scaling_group(instance_id):
                    logger.info(
                        f"  Skipping EC2 Instance (managed by Auto Scaling group): {instance_id}")
                    continue

                # Check if the instance has EKS related tags and skip if it does
                eks_tags = [tag for tag in instance.get(
                    "Tags", []) if tag["Key"].startswith("kubernetes.io/cluster/")]
                if eks_tags:
                    logger.info(
                        f"  Skipping EC2 Instance (managed by EKS): {instance_id}")
                    continue

                # if instance_id != "xxxx``":
                #     continue

                logger.debug(f"Processing EC2 Instance: {instance_id}")
                id = instance_id

                ftstack = "ec2"
                try:
                    tags_response = self.provider_instance.aws_clients.ec2_client.describe_tags(
                        Filters=[{'Name': 'resource-id',
                                  'Values': [instance_id]}]
                    )
                    tags = tags_response.get('Tags', [])
                    for tag in tags:
                        if tag['Key'] == 'Name':
                            instance_name = tag['Value']
                            break
                        if tag['Key'] == 'ftstack':
                            if tag['Value'] != 'ec2':
                                ftstack = "stack_"+tag['Value']
                            break
                except Exception as e:
                    logger.error(f"Error occurred: {e}")

                attributes = {
                    "id": id,
                }

                # Call root_block_device.kms_key_id
                root_device = ""
                if "RootDeviceName" in instance:
                    logger.debug(
                        f" RootDeviceName: {instance['RootDeviceName']}")
                    root_device = instance["RootDeviceName"]
                    # Get the KMS key for the root device
                    response = self.provider_instance.aws_clients.ec2_client.describe_volumes(Filters=[{
                        'Name': 'attachment.instance-id',
                        'Values': [instance_id]
                    }])
                    for volume in response['Volumes']:
                        device = volume['Attachments'][0]['Device']
                        if device == instance["RootDeviceName"]:
                            if 'KmsKeyId' in volume:
                                keyArn = volume['KmsKeyId']
                                type = self.kms_instance.aws_kms_key(
                                    keyArn, ftstack)
                                if type == "MANAGED":
                                    kms_key_alias = self.get_kms_alias(keyArn)
                                    if kms_key_alias:
                                        self.hcl.add_additional_data(
                                            resource_type, id, "kms_key_alias", kms_key_alias)

                if "IamInstanceProfile" in instance:
                    attributes["iam_instance_profile"] = instance["IamInstanceProfile"]["Arn"]
                    iam_instance_profile_id = instance["IamInstanceProfile"]["Arn"].split(
                        "/")[-1]  # Updated this line
                    self.aws_iam_instance_profile(
                        iam_instance_profile_id, ftstack)

                if not instance_name:
                    instance_name = id
                self.hcl.process_resource(
                    resource_type, instance_name, attributes)
                self.hcl.add_stack(resource_type, id, ftstack)

                ec2_get_user_data = self.ec2_get_user_data(instance_id)
                if ec2_get_user_data:
                    if resource_type not in self.hcl.additional_data:
                        self.hcl.additional_data[resource_type] = {}
                    if id not in self.hcl.additional_data[resource_type]:
                        self.hcl.additional_data[resource_type][id] = {}
                    self.hcl.additional_data[resource_type][id]["user_data"] = ec2_get_user_data

                vpc_id = instance.get("VpcId", "")
                vpc_name = get_vpc_name(self.provider_instance.aws_clients, vpc_id)
                if vpc_name:
                    self.hcl.add_additional_data(
                        resource_type, id, "vpc_name", vpc_name)

                subnet_id = instance.get("SubnetId", "")
                if subnet_id:
                    subnet_name = self.get_subnet_name_ec2(subnet_id)
                    if subnet_name:
                        if resource_type not in self.hcl.additional_data:
                            self.hcl.additional_data[resource_type] = {}
                        if id not in self.hcl.additional_data[resource_type]:
                            self.hcl.additional_data[resource_type][id] = {}
                        self.hcl.additional_data[resource_type][id]["subnet_name"] = subnet_name

                # Process all EIPs associated with the instance
                eips_associated = self.provider_instance.aws_clients.ec2_client.describe_addresses(Filters=[{
                    'Name': 'instance-id',
                    'Values': [instance_id]
                }])
                for eip in eips_associated["Addresses"]:
                    self.aws_eip(eip["AllocationId"])

                # Process all EBS volumes associated with the instance
                for block_device in instance.get("BlockDeviceMappings", []):
                    if root_device == block_device["DeviceName"]:
                        continue
                    volume_id = block_device["Ebs"]["VolumeId"]
                    self.aws_ebs_volume(volume_id)

                    # Process the volume attachment for the EBS volume
                    self.aws_volume_attachment(instance_id, block_device)

                    # Get the KMS key for the volume
                    response = self.provider_instance.aws_clients.ec2_client.describe_volumes(
                        VolumeIds=[block_device["Ebs"]["VolumeId"]])
                    for volume in response['Volumes']:
                        if 'KmsKeyId' in volume:
                            keyArn = volume['KmsKeyId']
                            type = self.kms_instance.aws_kms_key(
                                keyArn, ftstack)
                            if type == "MANAGED":
                                kms_key_alias = self.get_kms_alias(keyArn)
                                if kms_key_alias:
                                    if "aws_ebs_volume" not in self.hcl.additional_data:
                                        self.hcl.additional_data["aws_ebs_volume"] = {
                                        }
                                    if volume_id not in self.hcl.additional_data["aws_ebs_volume"]:
                                        self.hcl.additional_data["aws_ebs_volume"][volume_id] = {
                                        }
                                    self.hcl.additional_data["aws_ebs_volume"][volume_id]["kms_key_alias"] = kms_key_alias

                for sg in instance.get("SecurityGroups", []):
                    self.security_group_instance.aws_security_group(
                        sg["GroupId"], ftstack)

                key_pair = instance.get("KeyName", "")
                logger.debug(f"Key Pair: {key_pair}")
                if key_pair:
                    self.aws_key_pair(key_pair, ftstack)

                # disable for now until i know how to handle private and public ips
                # for ni in instance.get("NetworkInterfaces", []):
                #     self.aws_network_interface(ni["NetworkInterfaceId"])

                #     # Process the attachment details for the additional network interface
                #     self.aws_network_interface_attachment(instance_id, ni)

    def aws_iam_instance_profile(self, iam_instance_profile_id, ftstack=None):
        resource_type = "aws_iam_instance_profile"
        logger.debug(
            f"Processing IAM Instance Profile: {iam_instance_profile_id}")

        try:
            response = self.provider_instance.aws_clients.iam_client.get_instance_profile(
                InstanceProfileName=iam_instance_profile_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                logger.info(
                    f"Instance Profile {iam_instance_profile_id} cannot be found.")
            else:
                logger.error(f"An unexpected error occurred: {e}")
            return

        profile = response["InstanceProfile"]

        # Process only the first associated role
        for role in profile["Roles"]:
            role_name = role["RoleName"]
            self.iam_role_instance.aws_iam_role(role_name, ftstack)

    def aws_ebs_volume(self, volume_id):
        resource_type = "aws_ebs_volume"
        logger.debug(f"Processing EBS Volume: {volume_id}")

        volume = self.provider_instance.aws_clients.ec2_client.describe_volumes(VolumeIds=[
            volume_id])

        if not volume["Volumes"]:
            logger.debug(f"  No EBS Volume found for Volume ID: {volume_id}")
            return

        vol = volume["Volumes"][0]
        id = vol["VolumeId"]

        attributes = {
            "id": id,
            "availability_zone": vol["AvailabilityZone"],
            "size": vol["Size"],
            "state": vol["State"],
            "type": vol["VolumeType"],
            "iops": vol["Iops"] if "Iops" in vol else None,
            "encrypted": vol["Encrypted"]
        }

        if "SnapshotId" in vol:
            attributes["snapshot_id"] = vol["SnapshotId"]

        self.hcl.process_resource(
            resource_type, volume_id.replace("-", "_"), attributes)

        device_name = self.ec2_get_device_name(id)
        if device_name:
            if resource_type not in self.hcl.additional_data:
                self.hcl.additional_data[resource_type] = {}
            if id not in self.hcl.additional_data[resource_type]:
                self.hcl.additional_data[resource_type][id] = {}
            self.hcl.additional_data[resource_type][id]["device_name"] = device_name

    def aws_volume_attachment(self, instance_id, block_device):
        device_name = block_device["DeviceName"]
        volume_id = block_device["Ebs"]["VolumeId"]

        logger.debug(
            f"Processing EBS Volume Attachment for Volume: {volume_id} on Instance: {instance_id}")

        attributes = {
            'id': f"{device_name}:{volume_id}:{instance_id}",
            "instance_id": instance_id,
            "volume_id": volume_id,
            "device_name": device_name
        }

        self.hcl.process_resource(
            "aws_volume_attachment", volume_id.replace("-", "_"), attributes)

    def aws_network_interface(self, network_interface_id):
        logger.debug(f"Processing Network Interface: {network_interface_id}")

        network_interface = self.provider_instance.aws_clients.ec2_client.describe_network_interfaces(
            NetworkInterfaceIds=[network_interface_id])

        if not network_interface["NetworkInterfaces"]:
            logger.debug(
                f"  No Network Interface found for ID: {network_interface_id}")
            return

        ni = network_interface["NetworkInterfaces"][0]

        attachment = ni.get("Attachment")
        if not attachment:
            logger.debug(
                f"  Skipping Detached Network Interface: {network_interface_id}")
            return
        if attachment["DeviceIndex"] == 0:
            logger.debug(
                f"  Skipping Primary Network Interface: {network_interface_id}")
            return

        attributes = {
            "id": ni["NetworkInterfaceId"],
            "subnet_id": ni["SubnetId"],
            "description": ni.get("Description", ""),
            "private_ip": ni["PrivateIpAddress"],
            "security_groups": [sg["GroupId"] for sg in ni["Groups"]],
        }

        if "Association" in ni and "PublicIp" in ni["Association"]:
            attributes["public_ip"] = ni["Association"]["PublicIp"]

        self.hcl.process_resource(
            "aws_network_interface", network_interface_id.replace("-", "_"), attributes)

    def aws_network_interface_attachment(self, instance_id, network_interface):
        logger.debug(
            f"Processing Network Interface Attachment for Network Interface: {network_interface['NetworkInterfaceId']} on Instance: {instance_id}")

        if network_interface["Attachment"]["DeviceIndex"] == 0:
            logger.debug(
                f"  Skipping Primary Network Interface: {network_interface['NetworkInterfaceId']}")
            return

        attributes = {
            "id": network_interface["Attachment"]["AttachmentId"],
            "instance_id": instance_id,
            "network_interface_id": network_interface["NetworkInterfaceId"],
            "device_index": network_interface["Attachment"]["DeviceIndex"],
        }

        self.hcl.process_resource(
            "aws_network_interface_attachment", network_interface["NetworkInterfaceId"].replace("-", "_"), attributes)

    def aws_key_pair(self, key_name, ftstack):
        logger.debug(f"Processing EC2 Key Pairs...")
        resource_type = "aws_key_pair"

        # Retrieve all key pairs
        key_pairs = self.provider_instance.aws_clients.ec2_client.describe_key_pairs(
            IncludePublicKey=True)["KeyPairs"]

        for key_pair in key_pairs:
            current_key_name = key_pair["KeyName"]

            # Check if the current key pair is the one we're interested in
            if current_key_name == key_name:
                logger.debug(f"Processing Key Pair: {current_key_name}")

                # Define the attributes for the key pair
                id = current_key_name
                attributes = {
                    "id": current_key_name,
                    "public_key": key_pair.get("PublicKey", ""),
                }

                # Process the resource with a modified key name to fit naming conventions
                self.hcl.process_resource(
                    resource_type, id, attributes)

                self.hcl.add_stack(resource_type, id, ftstack)

                break  # Since we found the key pair, no need to continue the loop
            else:
                # If it's not the key pair we're looking for, log and skip to the next
                logger.debug(f"Skipping Key Pair: {current_key_name}")

    def aws_launch_template(self):
        logger.debug(f"Processing EC2 Launch Templates...")

        launch_templates = self.provider_instance.aws_clients.ec2_client.describe_launch_templates()[
            "LaunchTemplates"]
        for launch_template in launch_templates:
            launch_template_id = launch_template["LaunchTemplateId"]
            logger.debug(f"Processing Launch Template: {launch_template_id}")

            attributes = {
                "id": launch_template_id,
                "name": launch_template.get("LaunchTemplateName", None),
                "arn": launch_template.get("LaunchTemplateArn", None),
                "default_version": launch_template.get("DefaultVersionNumber", None),
                "latest_version": launch_template.get("LatestVersionNumber", None),
            }
            self.hcl.process_resource(
                "aws_launch_template", launch_template_id.replace("-", "_"), attributes)

    def aws_placement_group(self):
        logger.debug(f"Processing EC2 Placement Groups...")

        placement_groups = self.provider_instance.aws_clients.ec2_client.describe_placement_groups()[
            "PlacementGroups"]
        for placement_group in placement_groups:
            placement_group_name = placement_group["GroupName"]
            logger.debug(f"Processing Placement Group: {placement_group_name}")

            attributes = {
                "id": placement_group_name,
                "name": placement_group_name,
                "strategy": placement_group["Strategy"],
            }
            self.hcl.process_resource(
                "aws_placement_group", placement_group_name.replace("-", "_"), attributes)

    def aws_spot_datafeed_subscription(self):
        logger.debug(f"Processing EC2 Spot Datafeed Subscriptions...")

        try:
            spot_datafeed_subscription = self.provider_instance.aws_clients.ec2_client.describe_spot_datafeed_subscription()
            subscription = spot_datafeed_subscription["SpotDatafeedSubscription"]

            bucket_id = subscription["Bucket"]
            logger.debug(f"Processing Spot Datafeed Subscription: {bucket_id}")

            attributes = {
                "id": subscription["OwnerId"],
                "bucket": bucket_id,
                "prefix": subscription.get("Prefix", ""),
            }
            self.hcl.process_resource(
                "aws_spot_datafeed_subscription", bucket_id.replace("-", "_"), attributes)
        except self.provider_instance.aws_clients.ec2_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "InvalidSpotDatafeed.NotFound":
                logger.debug(f"  No Spot Datafeed Subscriptions found")
            else:
                raise

    def aws_spot_fleet_request(self):
        logger.debug(f"Processing EC2 Spot Fleet Requests...")

        spot_fleet_requests = self.provider_instance.aws_clients.ec2_client.describe_spot_fleet_requests()[
            "SpotFleetRequestConfigs"]
        for spot_fleet_request in spot_fleet_requests:
            request_id = spot_fleet_request["SpotFleetRequestId"]
            logger.debug(f"Processing Spot Fleet Request: {request_id}")

            attributes = {
                "id": request_id,
                "spot_price": spot_fleet_request["SpotPrice"],
                "iam_fleet_role": spot_fleet_request["IamFleetRole"],
                "target_capacity": spot_fleet_request["TargetCapacity"],
            }
            self.hcl.process_resource(
                "aws_spot_fleet_request", request_id.replace("-", "_"), attributes)

    def aws_spot_instance_request(self):
        logger.debug(f"Processing EC2 Spot Instance Requests...")

        spot_instance_requests = self.provider_instance.aws_clients.ec2_client.describe_spot_instance_requests()[
            "SpotInstanceRequests"]
        for spot_instance_request in spot_instance_requests:
            request_id = spot_instance_request["SpotInstanceRequestId"]
            logger.debug(f"Processing Spot Instance Request: {request_id}")

            attributes = {
                "id": request_id,
                "spot_price": spot_instance_request["SpotPrice"],
                "instance_type": spot_instance_request["LaunchSpecification"]["InstanceType"],
                "availability_zone_group": spot_instance_request.get("AvailabilityZoneGroup", ""),
            }
            self.hcl.process_resource(
                "aws_spot_instance_request", request_id.replace("-", "_"), attributes)
