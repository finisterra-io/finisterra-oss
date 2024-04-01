from ...utils.hcl import HCL
import json
import logging
import inspect

logger = logging.getLogger('finisterra')


class SQS:
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

    def sqs(self):
        self.hcl.prepare_folder()

        self.aws_sqs_queue()
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

    def aws_sqs_queue(self):
        resource_type = "aws_sqs_queue"
        logger.debug("Processing SQS Queues...")

        paginator = self.provider_instance.aws_clients.sqs_client.get_paginator(
            "list_queues")
        total = 0
        for page in paginator.paginate():
            total += len(page.get("QueueUrls", []))

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for page in paginator.paginate():
            for queue_url in page.get("QueueUrls", []):
                queue_name = queue_url.split("/")[-1]
                self.provider_instance.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{queue_name}[/]")

                # if queue_name != 'xxxxx':
                #     continue

                logger.debug(f"Processing SQS Queue: {queue_name}")
                id = queue_url

                fstack = "sqs"
                try:
                    tags_response = self.provider_instance.aws_clients.sqs_client.list_queue_tags(
                        QueueUrl=queue_url)
                    tags = tags_response.get('Tags', {})
                    if tags.get('ftstack', 'sqs') != 'sqs':
                        fstack = "stack_"+tags.get('ftstack', 'sqs')
                except Exception as e:
                    logger.error(f"Error occurred: {e}")

                attributes = {
                    "id": id,
                }
                self.hcl.process_resource(
                    resource_type, id, attributes)
                self.hcl.add_stack(resource_type, id, fstack)

                # Call aws_sqs_queue_policy with the queue_url as an argument
                self.aws_sqs_queue_policy(queue_url)

                # Get the redrive policy for the queue
                response = self.provider_instance.aws_clients.sqs_client.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=['RedrivePolicy']
                )

                # If a RedrivePolicy exists, extract and add the DLQ ARN to dlq_list
                if 'Attributes' in response and 'RedrivePolicy' in response['Attributes']:
                    redrive_policy = json.loads(
                        response['Attributes']['RedrivePolicy'])
                    if 'deadLetterTargetArn' in redrive_policy:
                        # get the url of the DLQ by the arn
                        deadLetterTargetArn = redrive_policy['deadLetterTargetArn'].split(
                            ":")[-1]
                        try:
                            dlq_url = self.provider_instance.aws_clients.sqs_client.get_queue_url(
                                QueueName=redrive_policy['deadLetterTargetArn'].split(":")[-1])
                            self.hcl.add_additional_data(
                                resource_type, dlq_url['QueueUrl'], "parent_url", queue_url)
                            self.hcl.add_additional_data(
                                resource_type, dlq_url['QueueUrl'], "is_dlq", True)
                        except Exception as e:
                            logger.error(f"Error occurred: {e}")
                            continue

                # Call aws_sqs_queue_redrive_policy with the queue_url as an argument
                self.aws_sqs_queue_redrive_policy(queue_url)
                self.aws_sqs_queue_redrive_allow_policy(queue_url)

    def aws_sqs_queue_policy(self, queue_url):
        logger.debug("Processing SQS Queue Policies...")

        queue_name = queue_url.split("/")[-1]
        response = self.provider_instance.aws_clients.sqs_client.get_queue_attributes(
            QueueUrl=queue_url, AttributeNames=["Policy"])

        if "Attributes" in response and "Policy" in response["Attributes"]:
            policy = response["Attributes"]["Policy"]

            logger.debug(f"Processing SQS Queue Policy: {queue_name}")

            attributes = {
                "id": queue_url,
                "policy": policy,
            }
            self.hcl.process_resource(
                "aws_sqs_queue_policy", queue_name.replace("-", "_"), attributes)
        else:
            logger.debug(f"  No policy found for SQS Queue: {queue_name}")

    def aws_sqs_queue_redrive_policy(self, queue_url):
        logger.debug("Processing SQS Queue Redrive Policies...")

        queue_name = queue_url.split("/")[-1]
        response = self.provider_instance.aws_clients.sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['RedrivePolicy']
        )

        # If a RedrivePolicy exists, process it as a separate resource
        if 'Attributes' in response and 'RedrivePolicy' in response['Attributes']:
            redrive_policy = response['Attributes']['RedrivePolicy']
            logger.debug(f"Processing SQS Queue Redrive Policy: {queue_name}")

            # Process the redrive policy as a separate resource
            attributes = {
                "id": queue_url,
                "redrive_policy": redrive_policy,
            }
            self.hcl.process_resource(
                "aws_sqs_queue_redrive_policy", queue_name.replace("-", "_"), attributes)
        else:
            logger.debug(
                f"  No redrive policy found for SQS Queue: {queue_name}")

    def aws_sqs_queue_redrive_allow_policy(self, queue_url):
        logger.debug("Processing SQS Queue Redrive Allow Policies...")

        queue_name = queue_url.split("/")[-1]
        response = self.provider_instance.aws_clients.sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            # AttributeNames=['RedriveAllowPolicy']
        )

        # If a Policy exists, process it as a separate resource
        if 'Attributes' in response and 'Policy' in response['Attributes']:
            redrive_allow_policy = response['Attributes']['RedriveAllowPolicy']
            logger.debug(
                f"Processing SQS Queue Redrive Allow Policy: {queue_name}")

            # Process the allow policy as a separate resource
            attributes = {
                "id": queue_url,
                "redrive_allow_policy": redrive_allow_policy,
            }
            self.hcl.process_resource(
                "aws_sqs_queue_redrive_allow_policy", queue_name.replace("-", "_"), attributes)
        else:
            logger.debug(
                f"  No allow policy found for SQS Queue: {queue_name}")
