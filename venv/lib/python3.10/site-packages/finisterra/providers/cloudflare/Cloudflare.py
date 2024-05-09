import os
import logging


from ...utils.filesystem import load_provider_schema
from ...providers.cloudflare.dns import DNS
from ...providers.cloudflare.cf_clients import CFClients

logger = logging.getLogger('finisterra')


class Cloudflare:
    def __init__(self, progress, script_dir, output_dir, filters):
        self.progress = progress
        self.output_dir = output_dir
        self.provider_name = "registry.terraform.io/cloudflare/cloudflare"
        self.provider_version = "~> 4.0"
        self.provider_name_short = "cloudflare"
        self.provider_source = "cloudflare/cloudflare"
        self.script_dir = script_dir
        self.filters = filters
        self.schema_data = load_provider_schema(self.script_dir, self.provider_name_short,
                                                self.provider_source, self.provider_version)

        self.cf_clients = CFClients()
        self.account_name = self.get_account_name()

    def get_account_name(self):
        account_name = "Cloudflare"
        return account_name

    def dns(self):

        instance = DNS(self)
        instance.dns()
        return instance.hcl.unique_ftstacks
