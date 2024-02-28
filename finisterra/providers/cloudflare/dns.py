import os
from ...utils.hcl import HCL
import logging

logger = logging.getLogger('finisterra')


class DNS:
    def __init__(self, progress, cf_clients, script_dir, provider_name, provider_name_short,
                 provider_source, provider_version, schema_data, output_dir, hcl=None):
        self.progress = progress

        self.cf_clients = cf_clients

        self.script_dir = script_dir
        self.schema_data = schema_data

        if not hcl:
            self.hcl = HCL(self.schema_data)
        else:
            self.hcl = hcl

        self.hcl.output_dir = output_dir
        self.hcl.region = "global"
        self.hcl.account_id = ""

        self.hcl.provider_name = provider_name
        self.hcl.provider_name_short = provider_name_short
        self.hcl.provider_source = provider_source
        self.hcl.provider_version = provider_version

    def dns(self):
        self.hcl.prepare_folder()
        self.cloudflare_zone()
        if self.hcl.count_state():
            self.progress.update(
                self.task, description=f"[cyan]{self.__class__.__name__} [bold]Refreshing state[/]", total=self.progress.tasks[self.task].total+1)
            self.hcl.refresh_state()
            self.hcl.request_tf_code()
            self.progress.update(
                self.task, advance=1, description=f"[green]{self.__class__.__name__} [bold]Code Generated[/]")
        else:
            self.task = self.progress.add_task(
                f"[orange3]{self.__class__.__name__} [bold]No resources found[/]", total=1)
            self.progress.update(self.task, advance=1)

    def cloudflare_zone(self, zone_id=None, ftstack=None):
        resource_name = "cloudflare_zone"

        if zone_id and ftstack:
            if self.hcl.id_resource_processed(resource_name, zone_id, ftstack):
                logger.debug(
                    f"  Skipping {resource_name}: {zone_id} already processed")
                return
            self.process_single_cloudflare_zone(zone_id, ftstack)
            return

        zones = self.cf_clients.cf.zones.get()
        total = 0
        for zone in zones:
            total += 1

        if total > 0:
            self.task = self.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for zone in zones:
            zone_id = zone['id']
            self.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{zone['name']}[/]")
            self.process_single_cloudflare_zone(zone_id, ftstack)

    def process_single_cloudflare_zone(self, zone_id, ftstack=None):
        resource_name = "cloudflare_zone"

        logger.debug(f"Processing {resource_name}: {zone_id}")
        ftstack = "dns"

        id = zone_id
        attributes = {
            "id": zone_id,
        }

        self.hcl.process_resource(
            resource_name, zone_id.replace("-", "_"), attributes)
        self.hcl.add_stack(resource_name, id, ftstack)
