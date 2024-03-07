import os
from utils.hcl import HCL


class SSM:
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


    def ssm(self):
        self.hcl.prepare_folder(os.path.join("generated", "ssm"))

        self.aws_ssm_activation()
        self.aws_ssm_association()
        # self.aws_ssm_default_patch_baseline() # Permission error
        # self.aws_ssm_document()  # Permission error
        self.aws_ssm_maintenance_window()
        self.aws_ssm_maintenance_window_target()
        self.aws_ssm_maintenance_window_task()
        # self.aws_ssm_parameter() #Check how to handle the insecure values
        # self.aws_ssm_patch_baseline() # Permission error
        self.aws_ssm_patch_group()
        self.aws_ssm_resource_data_sync()
        self.aws_ssm_service_setting()

        self.hcl.refresh_state()
        self.hcl.request_tf_code()
        # self.hcl.generate_hcl_file()

    def aws_ssm_activation(self):
        print("Processing SSM Activations...")

        paginator = self.aws_clients.ssm_client.get_paginator("describe_activations")
        for page in paginator.paginate():
            for activation in page["ActivationList"]:
                activation_id = activation["ActivationId"]
                print(f"Processing SSM Activation: {activation_id}")

                attributes = {
                    "id": activation_id,
                    "name": activation["Description"],
                    "iam_role": activation["IamRole"],
                }

                if "RegistrationLimit" in activation:
                    attributes["registration_limit"] = activation["RegistrationLimit"]

                if "ExpirationDate" in activation:
                    attributes["expiration_date"] = activation["ExpirationDate"].isoformat(
                    )

                self.hcl.process_resource(
                    "aws_ssm_activation", activation_id.replace("-", "_"), attributes)

    def aws_ssm_association(self):
        print("Processing SSM Associations...")

        paginator = self.aws_clients.ssm_client.get_paginator("list_associations")
        for page in paginator.paginate():
            for association in page["Associations"]:
                association_id = association.get("AssociationId")
                instance_id = association.get("InstanceId")
                name = association.get("Name")

                print(f"Processing SSM Association: {association_id}")

                attributes = {
                    "id": association_id,
                    "association_id": association_id,
                    "instance_id": instance_id,
                    "name": name,
                }
                self.hcl.process_resource(
                    "aws_ssm_association", association_id.replace("-", "_"), attributes)

    def aws_ssm_default_patch_baseline(self):
        print("Processing SSM Default Patch Baselines...")

        paginator = self.aws_clients.ssm_client.get_paginator("describe_patch_baselines")
        for page in paginator.paginate(Filters=[{"Key": "OWNER", "Values": ["Self"]}]):
            for baseline in page["BaselineIdentities"]:
                if baseline.get("DefaultBaseline"):
                    baseline_id = baseline["BaselineId"]
                    print(
                        f"Processing SSM Default Patch Baseline: {baseline_id}")

                    attributes = {
                        "id": baseline_id,
                        "name": baseline["BaselineName"],
                        "description": baseline.get("BaselineDescription"),
                        "operating_system": baseline["OperatingSystem"],
                    }
                    self.hcl.process_resource(
                        "aws_ssm_patch_baseline", baseline_id.replace("-", "_"), attributes)

    def aws_ssm_document(self):
        print("Processing SSM Documents...")

        paginator = self.aws_clients.ssm_client.get_paginator("list_documents")
        for page in paginator.paginate():
            for doc_info in page["DocumentIdentifiers"]:
                document_name = doc_info["Name"]
                print(f"Processing SSM Document: {document_name}")

                document = self.aws_clients.ssm_client.get_document(Name=document_name)
                content = document["Content"]

                attributes = {
                    "id": document_name,
                    "name": document_name,
                    "content": content,
                }

                if "DocumentFormat" in doc_info:
                    attributes["document_format"] = doc_info["DocumentFormat"]

                if "DocumentType" in doc_info:
                    attributes["document_type"] = doc_info["DocumentType"]

                self.hcl.process_resource(
                    "aws_ssm_document", document_name.replace("-", "_"), attributes)

    def aws_ssm_maintenance_window(self):
        print("Processing SSM Maintenance Windows...")

        paginator = self.aws_clients.ssm_client.get_paginator(
            "describe_maintenance_windows")
        for page in paginator.paginate():
            for window in page["WindowIdentities"]:
                window_id = window["WindowId"]
                print(f"Processing SSM Maintenance Window: {window_id}")

                attributes = {
                    "id": window_id,
                    "name": window["Name"],
                    "schedule": window["Schedule"],
                    "duration": window["Duration"],
                    "cutoff": window["Cutoff"],
                }
                self.hcl.process_resource(
                    "aws_ssm_maintenance_window", window_id.replace("-", "_"), attributes)

    def aws_ssm_maintenance_window_target(self):
        print("Processing SSM Maintenance Window Targets...")

        paginator = self.aws_clients.ssm_client.get_paginator(
            "describe_maintenance_windows")
        for page in paginator.paginate():
            for window in page["WindowIdentities"]:
                window_id = window["WindowId"]

                target_paginator = self.aws_clients.ssm_client.get_paginator(
                    "describe_maintenance_window_targets")
                for target_page in target_paginator.paginate(WindowId=window_id):
                    for target in target_page["Targets"]:
                        target_id = target["WindowTargetId"]
                        print(
                            f"Processing SSM Maintenance Window Target: {target_id}")

                        attributes = {
                            "id": target_id,
                            "window_id": window_id,
                            "resource_type": target["ResourceType"],
                            "targets": target["Targets"],
                        }
                        self.hcl.process_resource(
                            "aws_ssm_maintenance_window_target", target_id.replace("-", "_"), attributes)

    def aws_ssm_maintenance_window_task(self):
        print("Processing SSM Maintenance Window Tasks...")

        paginator = self.aws_clients.ssm_client.get_paginator(
            "describe_maintenance_windows")
        for page in paginator.paginate():
            for window in page["WindowIdentities"]:
                window_id = window["WindowId"]

                task_paginator = self.aws_clients.ssm_client.get_paginator(
                    "describe_maintenance_window_tasks")
                for task_page in task_paginator.paginate(WindowId=window_id):
                    for task in task_page["Tasks"]:
                        task_id = task["WindowTaskId"]
                        print(
                            f"Processing SSM Maintenance Window Task: {task_id}")

                        attributes = {
                            "id": task_id,
                            "window_id": window_id,
                            "task_type": task["Type"],
                            "targets": task["Targets"],
                            "task_arn": task["TaskArn"],
                            "priority": task["Priority"],
                            "service_role_arn": task["ServiceRoleArn"],
                        }
                        self.hcl.process_resource(
                            "aws_ssm_maintenance_window_task", task_id.replace("-", "_"), attributes)

    def aws_ssm_parameter(self):
        print("Processing SSM Parameters...")

        paginator = self.aws_clients.ssm_client.get_paginator("describe_parameters")
        for page in paginator.paginate():
            for parameter in page["Parameters"]:
                parameter_name = parameter["Name"]
                print(f"Processing SSM Parameter: {parameter_name}")

                parameter_details = self.aws_clients.ssm_client.get_parameter(
                    Name=parameter_name, WithDecryption=False)
                attributes = {
                    "id": parameter_name,
                    "name": parameter_name,
                    "type": parameter_details["Parameter"]["Type"],
                    "value": parameter_details["Parameter"]["Value"],
                }
                self.hcl.process_resource(
                    "aws_ssm_parameter", parameter_name.replace("-", "_"), attributes)

    def aws_ssm_patch_baseline(self):
        print("Processing SSM Patch Baselines...")

        paginator = self.aws_clients.ssm_client.get_paginator("describe_patch_baselines")
        for page in paginator.paginate():
            for baseline in page["BaselineIdentities"]:
                baseline_id = baseline["BaselineId"]
                print(f"Processing SSM Patch Baseline: {baseline_id}")

                attributes = {
                    "id": baseline_id,
                }
                self.hcl.process_resource(
                    "aws_ssm_patch_baseline", baseline_id.replace("-", "_"), attributes)

    def aws_ssm_patch_group(self):
        print("Processing SSM Patch Groups...")

        paginator = self.aws_clients.ssm_client.get_paginator("describe_patch_groups")
        for page in paginator.paginate():
            for group in page["Mappings"]:
                group_name = group["PatchGroup"]
                baseline_id = group["BaselineIdentity"]["BaselineId"]
                print(f"Processing SSM Patch Group: {group_name}")

                attributes = {
                    "id": group_name,
                    "baseline_id": baseline_id,
                }
                self.hcl.process_resource(
                    "aws_ssm_patch_group", group_name.replace("-", "_"), attributes)

    def aws_ssm_resource_data_sync(self):
        print("Processing SSM Resource Data Syncs...")

        paginator = self.aws_clients.ssm_client.get_paginator("list_resource_data_sync")
        for page in paginator.paginate():
            for data_sync in page["ResourceDataSyncItems"]:
                sync_name = data_sync["SyncName"]
                print(f"Processing SSM Resource Data Sync: {sync_name}")

                attributes = {
                    "id": sync_name,
                }
                self.hcl.process_resource(
                    "aws_ssm_resource_data_sync", sync_name.replace("-", "_"), attributes)

    def aws_ssm_service_setting(self):
        print("Processing SSM Service Settings...")

        setting_ids = [
            # Add the SettingId values you want to process
            "/ssm/parameter-store/default-parameter-tier",
            "/ssm/parameter-store/high-throughput-enabled",
            "/ssm/parameter-store/throughput-limit",
        ]

        for setting_id in setting_ids:
            try:
                service_setting = self.aws_clients.ssm_client.get_service_setting(
                    SettingId=setting_id)["ServiceSetting"]
                print(f"Processing SSM Service Setting: {setting_id}")

                attributes = {
                    "id": setting_id,
                }
                self.hcl.process_resource(
                    "aws_ssm_service_setting", setting_id.replace("/", "_"), attributes)
            except self.aws_clients.ssm_client.exceptions.ServiceSettingNotFound:
                print(f"  SSM Service Setting not found: {setting_id}")
                continue
            except Exception as e:
                print(
                    f"  An error occurred while processing SSM Service Setting: {setting_id}")
                print(e)
                continue
