import os
import os
import subprocess
import json
import logging


from ...utils.filesystem import load_provider_schema
from ...providers.cloudflare.dns import DNS
from ...providers.cloudflare.cf_clients import CFClients

logger = logging.getLogger('finisterra')


class Cloudflare:
    def __init__(self, progress, script_dir, output_dir):
        self.progress = progress
        self.output_dir = output_dir
        self.provider_name = "registry.terraform.io/cloudflare/cloudflare"
        self.provider_version = "~> 4.0"
        self.provider_name_short = "cloudflare"
        self.provider_source = "cloudflare/cloudflare"
        self.script_dir = script_dir
        self.schema_data = load_provider_schema(self.script_dir, self.provider_name_short,
                                                self.provider_source, self.provider_version)

        self.cf_clients_instance = CFClients()
        self.account_name = self.get_account_name()

    def get_account_name(self):
        account_name = "Cloudflare"
        return account_name

    def dns(self):

        instance = DNS(self.progress, self.cf_clients_instance, self.script_dir,
                       self.provider_name, self.provider_name_short,
                       self.provider_source, self.provider_version, self.schema_data, self.output_dir, self.account_name)
        instance.dns()
        return instance.hcl.unique_ftstacks
