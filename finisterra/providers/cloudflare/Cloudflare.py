import os
import os
import re
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
        self.provider_name = "registry.terraform.io/hashicorp/aws"
        self.script_dir = script_dir
        self.schema_data = self.load_provider_schema()

        self.aws_clients_instance = CFClients()

    def create_folder(self, folder):
        if not os.path.exists(folder):
            os.makedirs(folder)

    def load_provider_schema(self):
        # Save current folder
        current_folder = os.getcwd()
        os.chdir(self.script_dir)
        temp_dir = os.path.join("tmp")
        temp_file = os.path.join(temp_dir, 'terraform_providers_schema.json')

        # If the schema file already exists, load and return its contents
        if os.path.isfile(temp_file):
            with open(temp_file, "r") as schema_file:
                return json.load(schema_file)

        # If the schema file doesn't exist, run terraform commands
        self.create_folder(temp_dir)
        os.chdir(temp_dir)
        create_version_file(".", "cloudflare",
                            "cloudflare/cloudflare", "~> 4.0")

        logger.info("Initializing Terraform...")
        subprocess.run(["terraform", "init"], check=True)

        logger.info("Loading provider schema...")
        temp_file = os.path.join('terraform_providers_schema.json')
        with open(temp_file, 'w') as output:
            subprocess.run(["terraform", "providers", "schema",
                            "-json"], check=True, stdout=output)

        # Load the schema data from the newly created file
        with open(temp_file, "r") as schema_file:
            schema_data = json.load(schema_file)

        # Return to the original folder
        os.chdir(current_folder)

        return schema_data

    def dns(self):
        instance = DNS(self.progress, self.cf_clients_instance, self.script_dir,
                       self.provider_name, self.schema_data, self.output_dir)
        instance.dns()
        return instance.hcl.unique_ftstacks
