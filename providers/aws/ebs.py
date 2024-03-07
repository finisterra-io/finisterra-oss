import os
from utils.hcl import HCL


class EBS:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {
        
        }
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.workspace_id = workspace_id
        self.modules = modules
        self.hcl = HCL(self.schema_data, self.provider_name)

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


    def ebs(self):
        self.hcl.prepare_folder(os.path.join("generated", "ebs"))

        if "gov" not in self.region:
            # self.aws_ebs_default_kms_key() # fix function to ignore the default kms alias/aws/ebs
            self.aws_ebs_encryption_by_default()
        self.aws_ebs_snapshot()
        self.aws_ebs_volume()
        self.aws_snapshot_create_volume_permission()
        self.aws_volume_attachment()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_ebs_default_kms_key(self):
        print("Processing EBS Default KMS Key...")

        default_kms_key_id = self.aws_clients.ec2_client.get_ebs_default_kms_key_id()[
            "KmsKeyId"]

        # List all aliases
        aliases = self.aws_clients.kms_client.list_aliases()

        # Find the alias for the default key
        default_kms_key_alias = next((alias for alias in aliases['Aliases']
                                      if 'TargetKeyId' in alias and alias['TargetKeyId'] == default_kms_key_id), None)

        if default_kms_key_alias and default_kms_key_alias['AliasName'] == 'alias/aws/ebs':
            print("  Skipping default KMS Key")
            return

        # Retrieve key metadata to get the ARN
        key_metadata = self.aws_clients.kms_client.describe_key(KeyId=default_kms_key_id)
        default_kms_key_arn = key_metadata['KeyMetadata']['Arn']

        print(f"Processing EBS Default KMS Key: {default_kms_key_arn}")

        attributes = {
            "id": default_kms_key_id,
            "key_arn": default_kms_key_arn,
        }
        self.hcl.process_resource(
            "aws_ebs_default_kms_key", default_kms_key_id.replace("-", "_"), attributes)

    def aws_ebs_encryption_by_default(self):
        print("Processing EBS Encryption By Default...")

        encryption_by_default = self.aws_clients.ec2_client.get_ebs_encryption_by_default()[
            "EbsEncryptionByDefault"]

        attributes = {
            "id": "default",
            "enabled": encryption_by_default,
        }
        self.hcl.process_resource(
            "aws_ebs_encryption_by_default", "default", attributes)

    def aws_ebs_snapshot(self):
        print("Processing EBS Snapshots...")

        snapshots = self.aws_clients.ec2_client.describe_snapshots(OwnerIds=["self"])[
            "Snapshots"]

        for snapshot in snapshots:
            snapshot_id = snapshot["SnapshotId"]
            print(f"Processing EBS Snapshot: {snapshot_id}")

            attributes = {
                "id": snapshot_id,
                "volume_id": snapshot["VolumeId"],
                "description": snapshot.get("Description", ""),
            }
            self.hcl.process_resource(
                "aws_ebs_snapshot", snapshot_id.replace("-", "_"), attributes)

    def is_managed_by_auto_scaling_group(self, instance_id):
        response = self.aws_clients.autoscaling_client.describe_auto_scaling_instances(InstanceIds=[
                                                                           instance_id])
        return bool(response["AutoScalingInstances"])

    def aws_ebs_volume(self):
        print("Processing EBS Volumes...")

        volumes = self.aws_clients.ec2_client.describe_volumes()["Volumes"]

        for volume in volumes:
            volume_id = volume["VolumeId"]

            # Check if the volume is attached to an instance managed by an Auto Scaling group
            if "Attachments" in volume and volume["Attachments"]:
                instance_id = volume["Attachments"][0]["InstanceId"]
                if self.is_managed_by_auto_scaling_group(instance_id):
                    print(
                        f"  Skipping EBS Volume (attached to Auto Scaling group instance): {volume_id}")
                    continue

            print(f"Processing EBS Volume: {volume_id}")

            attributes = {
                "id": volume_id,
                "availability_zone": volume["AvailabilityZone"],
                "size": volume["Size"],
                "type": volume["VolumeType"],
                "encrypted": volume["Encrypted"],
                "kms_key_id": volume.get("KmsKeyId", ""),
            }
            self.hcl.process_resource(
                "aws_ebs_volume", volume_id.replace("-", "_"), attributes)

    def aws_snapshot_create_volume_permission(self):
        print("Processing Snapshot Create Volume Permissions...")

        snapshots = self.aws_clients.ec2_client.describe_snapshots(OwnerIds=["self"])[
            "Snapshots"]

        for snapshot in snapshots:
            snapshot_id = snapshot["SnapshotId"]
            permissions = self.aws_clients.ec2_client.describe_snapshot_attribute(
                SnapshotId=snapshot_id, Attribute="createVolumePermission"
            )["CreateVolumePermissions"]

            for permission in permissions:
                user_id = permission["UserId"]

                print(
                    f"Processing Snapshot Create Volume Permission for Snapshot: {snapshot_id}, User ID: {user_id}")

                attributes = {
                    "id": f"{snapshot_id}-{user_id}",
                    "snapshot_id": snapshot_id,
                    "user_id": user_id,
                }
                self.hcl.process_resource(
                    "aws_snapshot_create_volume_permission", f"{snapshot_id}-{user_id}".replace(
                        "-", "_"), attributes
                )

    def aws_volume_attachment(self):
        print("Processing Volume Attachments...")

        volumes = self.aws_clients.ec2_client.describe_volumes()["Volumes"]

        for volume in volumes:
            volume_id = volume["VolumeId"]

            if "Attachments" in volume:
                for attachment in volume["Attachments"]:
                    instance_id = attachment["InstanceId"]

                    # Check if the instance is managed by an Auto Scaling group
                    if self.is_managed_by_auto_scaling_group(instance_id):
                        print(
                            f"  Skipping Volume Attachment (instance in Auto Scaling group): {volume_id} -> Instance: {instance_id}")
                        continue

                    device_name = attachment["Device"]

                    print(
                        f"Processing Volume Attachment: {volume_id} -> Instance: {instance_id}")

                    attachment_id = f"{volume_id}-{instance_id}"
                    attributes = {
                        "id": attachment_id,
                        "volume_id": volume_id,
                        "instance_id": instance_id,
                        "device_name": device_name,
                    }
                    self.hcl.process_resource(
                        "aws_volume_attachment", attachment_id.replace(
                            "-", "_"), attributes
                    )
