import os
import logging


from ...utils.filesystem import load_provider_schema
from .user import User
from ..pagerduty.pagerduty_clients import PagerDutyClients

logger = logging.getLogger('finisterra')


class PagerDuty:
    def __init__(self, progress, script_dir, output_dir, filters):
        self.progress = progress
        self.output_dir = output_dir
        self.provider_name = "registry.terraform.io/pagerduty/pagerduty"
        self.provider_version = "~> 3.10.1"
        self.provider_name_short = "pagerduty"
        self.provider_source = "pagerduty/pagerduty"
        self.script_dir = script_dir
        self.filters = filters
        self.schema_data = load_provider_schema(self.script_dir, self.provider_name_short,
                                                self.provider_source, self.provider_version)

        self.api_clients = PagerDutyClients()
        self.account_name = self.get_account_name()

    def get_account_name(self):
        account_name = "PagerDuty"
        return account_name

    def user(self):
        instance = User(self)
        instance.user()
        return instance.hcl.unique_ftstacks
