import os
from utils.hcl import HCL
from providers.aws.iam_role import IAM_ROLE
from providers.aws.logs import Logs

class StepFunction:
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
        self.hcl = HCL(self.schema_data, self.provider_name)

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


        self.iam_role_instance = IAM_ROLE(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)        
        self.logs_instance = Logs(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)


    def to_list(self, attributes, arg):
        return [attributes.get(arg)]

    def stepfunction(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_sfn_state_machine()

        self.hcl.refresh_state()

        self.hcl.request_tf_code()


    def aws_sfn_state_machine(self):
        resource_type = "aws_sfn_state_machine"
        print("Processing State Machines...")

        paginator = self.aws_clients.sfn_client.get_paginator("list_state_machines")
        for page in paginator.paginate():
            for state_machine_summary in page["stateMachines"]:
                print(f"Processing State Machine: {state_machine_summary['name']}")

                # if state_machine_summary['name'] != 'dev-fpm-3431_backfill-email-verified':
                #     continue

                # Call describe_state_machine to get detailed info, including roleArn
                state_machine = self.aws_clients.sfn_client.describe_state_machine(
                    stateMachineArn=state_machine_summary['stateMachineArn']
                )

                role_arn = state_machine.get('roleArn', None)
                state_machine_arn = state_machine["stateMachineArn"]

                ftstack = "stepfunction"
                try:
                    tags_response = self.aws_clients.sfn_client.list_tags_for_resource(resourceArn=state_machine_arn)
                    tags = tags_response.get('tags', [])
                    for tag in tags:
                        if tag['key'] == 'ftstack':
                            if tag['value'] != 'stepfunction':
                                ftstack = "stack_"+tag['value']
                            break
                except Exception as e:
                    print("Error occurred: ", e)

                attributes = {
                    "id": state_machine_arn,
                    "name": state_machine["name"],
                    "definition": state_machine["definition"],
                    "role_arn": role_arn,
                }

                self.hcl.process_resource(
                    resource_type, state_machine_arn, attributes)
                
                self.hcl.add_stack(resource_type, state_machine_arn, ftstack)


                # Check if roleArn exists before proceeding
                if role_arn:
                    # Call aws_iam_role with state_machine as an argument
                    role_name = role_arn.split('/')[-1]
                    self.iam_role_instance.aws_iam_role(role_name, ftstack)
                else:
                    print(
                        f"No IAM role associated with State Machine: {state_machine['name']}")

                # Process CloudWatch Log Group
                logging_configuration = state_machine.get('loggingConfiguration', {})
                if logging_configuration:
                    destinations = logging_configuration.get('destinations', [])
                    for destination in destinations:
                        if destination['cloudWatchLogsLogGroup']:
                            logGroupArn = destination['cloudWatchLogsLogGroup']['logGroupArn']
                            log_group = logGroupArn.split(':')[-2]
                            self.logs_instance.aws_cloudwatch_log_group(log_group, ftstack)
