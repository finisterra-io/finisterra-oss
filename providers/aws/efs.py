import os
from utils.hcl import HCL


class EFS:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
        self.progress = progress
        self.aws_clients = aws_clients
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.workspace_id = workspace_id
        self.modules = modules
        self.hcl = HCL(self.schema_data, self.provider_name)

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


    def efs(self):
        self.hcl.prepare_folder(os.path.join("generated", "efs"))

        self.aws_efs_access_point()
        self.aws_efs_backup_policy()
        self.aws_efs_file_system()
        self.aws_efs_file_system_policy()
        self.aws_efs_mount_target()
        self.aws_efs_replication_configuration()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_efs_access_point(self):
        print("Processing EFS Access Points...")

        file_systems = self.aws_clients.efs_client.describe_file_systems()["FileSystems"]

        for file_system in file_systems:
            file_system_id = file_system["FileSystemId"]
            access_points = self.aws_clients.efs_client.describe_access_points(
                FileSystemId=file_system_id)["AccessPoints"]

            for access_point in access_points:
                access_point_id = access_point["AccessPointId"]
                print(f"Processing EFS Access Point: {access_point_id}")

                attributes = {
                    "id": access_point_id,
                    "file_system_id": file_system_id,
                }
                self.hcl.process_resource(
                    "aws_efs_access_point", access_point_id.replace("-", "_"), attributes)

    def aws_efs_backup_policy(self):
        print("Processing EFS Backup Policies...")

        file_systems = self.aws_clients.efs_client.describe_file_systems()["FileSystems"]

        for file_system in file_systems:
            file_system_id = file_system["FileSystemId"]
            try:
                backup_policy = self.aws_clients.efs_client.describe_backup_policy(
                    FileSystemId=file_system_id)["BackupPolicy"]
                status = backup_policy["Status"]

                print(
                    f"Processing EFS Backup Policy for FileSystem: {file_system_id}")

                attributes = {
                    "id": file_system_id,
                    "status": status,
                }
                self.hcl.process_resource(
                    "aws_efs_backup_policy", file_system_id.replace("-", "_"), attributes)
            except self.aws_clients.efs_client.exceptions.BackupPolicyNotFoundException:
                print(
                    f"  No Backup Policy found for FileSystem: {file_system_id}")

    def aws_efs_file_system(self):
        print("Processing EFS File Systems...")

        file_systems = self.aws_clients.efs_client.describe_file_systems()["FileSystems"]

        for file_system in file_systems:
            file_system_id = file_system["FileSystemId"]
            print(f"Processing EFS File System: {file_system_id}")

            attributes = {
                "id": file_system_id,
            }
            self.hcl.process_resource(
                "aws_efs_file_system", file_system_id.replace("-", "_"), attributes)

    def aws_efs_file_system_policy(self):
        print("Processing EFS File System Policies...")

        file_systems = self.aws_clients.efs_client.describe_file_systems()["FileSystems"]

        for file_system in file_systems:
            file_system_id = file_system["FileSystemId"]
            try:
                policy = self.aws_clients.efs_client.describe_file_system_policy(
                    FileSystemId=file_system_id)["Policy"]
                print(
                    f"Processing EFS File System Policy for FileSystem: {file_system_id}")

                attributes = {
                    "id": file_system_id,
                    "policy": policy,
                }
                self.hcl.process_resource(
                    "aws_efs_file_system_policy", file_system_id.replace("-", "_"), attributes)
            except self.aws_clients.efs_client.exceptions.PolicyNotFoundException:
                print(
                    f"  No File System Policy found for FileSystem: {file_system_id}")

    def aws_efs_mount_target(self):
        print("Processing EFS Mount Targets...")

        file_systems = self.aws_clients.efs_client.describe_file_systems()["FileSystems"]

        for file_system in file_systems:
            file_system_id = file_system["FileSystemId"]
            mount_targets = self.aws_clients.efs_client.describe_mount_targets(
                FileSystemId=file_system_id)["MountTargets"]

            for mount_target in mount_targets:
                mount_target_id = mount_target["MountTargetId"]
                print(
                    f"Processing EFS Mount Target: {mount_target_id} for FileSystem: {file_system_id}")

                attributes = {
                    "id": mount_target_id,
                    "file_system_id": file_system_id,
                    "subnet_id": mount_target["SubnetId"],
                }
                self.hcl.process_resource(
                    "aws_efs_mount_target", mount_target_id.replace("-", "_"), attributes)

    def aws_efs_replication_configuration(self):
        print("Processing EFS Replication Configurations...")

        file_systems = self.aws_clients.efs_client.describe_file_systems()["FileSystems"]

        for file_system in file_systems:
            file_system_id = file_system["FileSystemId"]
            replication_configurations = file_system.get(
                "ReplicationConfiguration", None)

            if replication_configurations:
                for config in replication_configurations["Rules"]:
                    rule_id = config["RuleId"]
                    print(
                        f"Processing EFS Replication Configuration Rule: {rule_id} for FileSystem: {file_system_id}")

                    attributes = {
                        "id": file_system_id,
                        "rule": {
                            "priority": config["Priority"],
                            "destination": {
                                "file_system_id": config["Destination"]["FileSystemId"],
                            },
                        },
                    }
                    self.hcl.process_resource("aws_efs_replication_configuration",
                                              f"{file_system_id}-{rule_id}".replace("-", "_"), attributes)
