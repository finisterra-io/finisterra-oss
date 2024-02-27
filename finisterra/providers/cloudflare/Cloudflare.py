import os
import os
import subprocess
import json
import logging


from ...utils.filesystem import create_version_file
from ...providers.cloudflare.dns import DNS
from ...providers.cloudflare.cf_clients import CFClients

logger = logging.getLogger('finisterra')


class Cloudflare:
    def __init__(self, progress, script_dir, output_dir):
        self.progress = progress
        self.output_dir = output_dir
        self.provider_name = "registry.terraform.io/hashicorp/cloudflare"
        self.script_dir = script_dir
        self.schema_data = self.load_provider_schema()
        print(self.schema_data['provider_schemas'].keys())

        self.cf_clients_instance = CFClients()

    def create_folder(self, folder):
        if not os.path.exists(folder):
            os.makedirs(folder)

    def load_provider_schema(self):
        # Save current folder
        temp_file = os.path.join(
            self.script_dir, 'terraform_providers_schema.json')

        # If the schema file already exists, load and return its contents
        if not os.path.isfile(temp_file):
            create_version_file(".", "cloudflare",
                                "cloudflare/cloudflare", "~> 4.0")

            logger.info("Initializing Terraform...")
            subprocess.run(["terraform", "init"], check=True)

            logger.info("Loading provider schema...")
            with open(temp_file, 'w') as output:
                subprocess.run(["terraform", "providers", "schema",
                                "-json"], check=True, stdout=output)

        # Load the schema data from the newly created file
        with open(temp_file, "r") as schema_file:
            schema_data = json.load(schema_file)

        return schema_data

    def dns(self):

        instance = DNS(self.progress, self.cf_clients_instance, self.script_dir,
                       self.provider_name, self.schema_data, self.output_dir)
        instance.dns()
        return instance.hcl.unique_ftstacks
