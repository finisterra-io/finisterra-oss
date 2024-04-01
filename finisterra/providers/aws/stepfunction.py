from ...utils.hcl import HCL
from ...providers.aws.iam_role import IAM
from ...providers.aws.logs import Logs
import logging
import inspect

logger = logging.getLogger('finisterra')


class StepFunction:
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

        self.iam_role_instance = IAM(self.provider_instance, self.hcl)
        self.logs_instance = Logs(self.provider_instance, self.hcl)

    def to_list(self, attributes, arg):
        return [attributes.get(arg)]

    def stepfunction(self):
        self.hcl.prepare_folder()

        self.aws_sfn_state_machine()
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

    def aws_sfn_state_machine(self):
        resource_type = "aws_sfn_state_machine"
        logger.debug("Processing State Machines...")

        paginator = self.provider_instance.aws_clients.sfn_client.get_paginator(
            "list_state_machines")
        total = 0
        for page in paginator.paginate():
            total += len(page.get("stateMachines", []))

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for page in paginator.paginate():
            for state_machine_summary in page["stateMachines"]:
                logger.debug(
                    f"Processing State Machine: {state_machine_summary['name']}")
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{state_machine_summary['name']}[/]")

                # if state_machine_summary['name'] != 'xxxxx':
                #     continue

                # Call describe_state_machine to get detailed info, including roleArn
                try:
                    state_machine = self.provider_instance.aws_clients.sfn_client.describe_state_machine(
                        stateMachineArn=state_machine_summary['stateMachineArn']
                    )
                except Exception as e:
                    # Handle other possible exceptions
                    logger.error(f"Unexpected error occurred: {e}")
                    continue

                role_arn = state_machine.get('roleArn', None)
                state_machine_arn = state_machine["stateMachineArn"]

                ftstack = "stepfunction"
                try:
                    tags_response = self.provider_instance.aws_clients.sfn_client.list_tags_for_resource(
                        resourceArn=state_machine_arn)
                    tags = tags_response.get('tags', [])
                    for tag in tags:
                        if tag['key'] == 'ftstack':
                            if tag['value'] != 'stepfunction':
                                ftstack = "stack_"+tag['value']
                            break
                except Exception as e:
                    logger.error(f"Error occurred: {e}")

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
                    logger.debug(
                        f"No IAM role associated with State Machine: {state_machine['name']}")

                # Process CloudWatch Log Group
                logging_configuration = state_machine.get(
                    'loggingConfiguration', {})
                if logging_configuration:
                    destinations = logging_configuration.get(
                        'destinations', [])
                    for destination in destinations:
                        if destination['cloudWatchLogsLogGroup']:
                            logGroupArn = destination['cloudWatchLogsLogGroup']['logGroupArn']
                            log_group = logGroupArn.split(':')[-2]
                            self.logs_instance.aws_cloudwatch_log_group(
                                log_group, ftstack)
