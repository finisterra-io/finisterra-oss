import os
from utils.hcl import HCL


class Backup:
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


    def backup(self):
        self.hcl.prepare_folder(os.path.join("generated", "backup"))

        self.aws_backup_plan()
        self.aws_backup_vault()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_backup_plan(self):
        print("Processing AWS Backup Plans...")

        paginator = self.aws_clients.backup_client.get_paginator("list_backup_plans")
        for page in paginator.paginate():
            for backup_plan in page["BackupPlansList"]:
                backup_plan_id = backup_plan["BackupPlanId"]
                plan = self.aws_clients.backup_client.get_backup_plan(
                    BackupPlanId=backup_plan_id)["BackupPlan"]
                print(f"Processing AWS Backup Plan: {backup_plan_id}")

                attributes = {
                    "id": backup_plan_id,
                    # "name": plan["BackupPlanName"],
                    # "version": plan["VersionId"],
                    # "arn": plan["BackupPlanArn"],
                    # "rule": plan["Rules"],
                }
                self.hcl.process_resource(
                    "aws_backup_plan", backup_plan_id.replace("-", "_"), attributes)

    def aws_backup_vault(self):
        print("Processing AWS Backup Vaults...")

        paginator = self.aws_clients.backup_client.get_paginator("list_backup_vaults")
        for page in paginator.paginate():
            for backup_vault in page["BackupVaultList"]:
                backup_vault_name = backup_vault["BackupVaultName"]
                vault = self.aws_clients.backup_client.describe_backup_vault(
                    BackupVaultName=backup_vault_name)
                print(f"Processing AWS Backup Vault: {backup_vault_name}")

                attributes = {
                    "id": backup_vault_name,
                    "name": vault["BackupVaultName"],
                    "arn": vault["BackupVaultArn"],
                    "recovery_points": vault["NumberOfRecoveryPoints"],
                }

                if "EncryptionKeyArn" in vault:
                    attributes["kms_key_arn"] = vault["EncryptionKeyArn"]

                self.hcl.process_resource(
                    "aws_backup_vault", backup_vault_name.replace("-", "_"), attributes)
