from ...utils.hcl import HCL
import logging
import inspect
from kafka.admin.acl_resource import ACLOperation, ACLPermissionType, ACLFilter, ACL, ResourcePattern, ResourceType, ACLResourcePatternType, ResourcePatternFilter


logger = logging.getLogger('finisterra')


class KafkaModule:
    def __init__(self, provider_instance, hcl=None):
        self.provider_instance = provider_instance

        if not hcl:
            self.hcl = HCL(self.provider_instance.schema_data)
        else:
            self.hcl = hcl

        self.hcl.output_dir = self.provider_instance.output_dir
        self.hcl.region = "global"
        self.hcl.account_id = ""

        self.hcl.provider_name = self.provider_instance.provider_name
        self.hcl.provider_name_short = self.provider_instance.provider_name_short
        self.hcl.provider_source = self.provider_instance.provider_source
        self.hcl.provider_version = self.provider_instance.provider_version
        self.hcl.provider_additional_data = self.provider_instance.provider_additional_data

        self.hcl.account_name = self.provider_instance.account_name

    def kafka_module(self):
        self.hcl.prepare_folder()
        self.hcl.module = inspect.currentframe().f_code.co_name

        self.kafka_topic()
        # self.kafka_acl()
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

    def kafka_topic(self, ftstack=None):
        resource_name = "kafka_topic"

        topics = self.provider_instance.kafka_clients.client.list_topics()
        total = len(topics)

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for topic in topics:
            logger.debug(f"Processing {resource_name}: {topic}")
            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{topic}[/]")
            ftstack = "kafka"

            id = topic
            attributes = {
                "id": id,
            }

            self.hcl.process_resource(
                resource_name, id, attributes)
            self.hcl.add_stack(resource_name, id, ftstack)

    def kafka_acl(self, ftstack=None):
        resource_name = "kafka_acl"

        resource_pattern_filter_group = ResourcePatternFilter(resource_type=ResourceType.GROUP,
                                                              resource_name="*",
                                                              pattern_type=ACLResourcePatternType.LITERAL)
        acl_filter = ACLFilter(principal="*",
                               host="*",
                               operation=ACLOperation.ANY,
                               permission_type=ACLPermissionType.ANY,
                               resource_pattern=resource_pattern_filter_group)
        acls = self.provider_instance.kafka_clients.client.describe_acls(
            acl_filter)
        print(acls)
        total = len(acls)

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for acl in acls:
            logger.debug(f"Processing {resource_name}: {acl}")
            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{acl}[/]")
            ftstack = "kafka"

            # The identifier for an ACL might be a combination of its attributes
            id = f"{acl.principal}_{acl.host}_{acl.operation}_{acl.permission_type}"
            attributes = {
                "resource_name": acl.resource_name,
                "resource_type": acl.resource_type,
                "acl_principal": acl.principal,
                "host": acl.host,
                "operation": acl.operation,
                "permission_type": acl.permission_type,
                "topic": acl.topic,
                "consumer_group": acl.consumer_group
            }

            self.hcl.process_resource(
                resource_name, id, attributes)
            self.hcl.add_stack(resource_name, id, ftstack)
