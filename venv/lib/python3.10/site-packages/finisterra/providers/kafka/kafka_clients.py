import os
from kafka import KafkaAdminClient


class KafkaClients:
    def __init__(self):
        KAFKA_BROKERS = os.environ.get("KAFKA_BROKERS")
        if not KAFKA_BROKERS:
            raise Exception("KAFKA_BROKERS environment variable is not set")
        self.client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKERS, client_id='topic_details_fetcher', security_protocol='SSL')
