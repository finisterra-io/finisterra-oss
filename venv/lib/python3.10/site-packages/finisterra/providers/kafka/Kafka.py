import logging
import os


from ...utils.filesystem import load_provider_schema
from .kafka_module import KafkaModule
from ..kafka.kafka_clients import KafkaClients

logger = logging.getLogger('finisterra')


class Kafka:
    def __init__(self, progress, script_dir, output_dir, filters):
        self.progress = progress
        self.output_dir = output_dir
        self.provider_name = "registry.terraform.io/mongey/kafka"
        self.provider_version = "~> 0.7.1"
        self.provider_name_short = "kafka"
        self.provider_source = "registry.terraform.io/mongey/kafka"
        KAFKA_BROKERS = os.environ.get("KAFKA_BROKERS")

        # Assuming KAFKA_BROKERS is something like "broker1:9092,broker2:9092,broker3:9092"
        # Transform it into a Terraform-friendly list format ["broker1:9092", "broker2:9092", "broker3:9092"]
        brokers_list = KAFKA_BROKERS.split(",")
        formatted_brokers = '", "'.join(brokers_list)

        self.provider_additional_data = f'provider "kafka" {{\n    bootstrap_servers = ["{formatted_brokers}"]\n}}'

        self.script_dir = script_dir
        self.filters = filters
        self.schema_data = load_provider_schema(self.script_dir, self.provider_name_short,
                                                self.provider_source, self.provider_version)

        self.kafka_clients = KafkaClients()
        self.account_name = self.get_account_name()

    def get_account_name(self):
        account_name = "Kafka"
        return account_name

    def kafka(self):
        instance = KafkaModule(self)
        instance.kafka_module()
        return instance.hcl.unique_ftstacks
