from ...utils.hcl import HCL
import logging
import inspect

logger = logging.getLogger('finisterra')


class DNS:
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
        self.hcl.account_name = self.provider_instance.account_name

    def dns(self):
        self.hcl.prepare_folder()
        self.hcl.module = inspect.currentframe().f_code.co_name

        self.cloudflare_zone()
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

    def cloudflare_zone(self, zone_id=None, ftstack=None):
        resource_name = "cloudflare_zone"

        if zone_id and ftstack:
            if self.hcl.id_resource_processed(resource_name, zone_id, ftstack):
                logger.debug(
                    f"  Skipping {resource_name}: {zone_id} already processed")
                return
            self.process_single_cloudflare_zone(zone_id, ftstack)
            return

        zones = self.provider_instance.cf_clients.cf.zones.get()
        total = 0
        for zone in zones['result']:
            total += 1

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for zone in zones['result']:
            zone_id = zone['id']
            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{zone['name']}[/]")
            self.process_single_cloudflare_zone(zone_id, zone['name'], ftstack)

    def process_single_cloudflare_zone(self, zone_id, zone_name, ftstack=None):
        resource_name = "cloudflare_zone"

        logger.debug(f"Processing {resource_name}: {zone_name}")
        ftstack = "dns"

        id = zone_id
        attributes = {
            "id": zone_id,
        }

        self.hcl.process_resource(
            resource_name, zone_id.replace("-", "_"), attributes)
        self.hcl.add_stack(resource_name, id, ftstack)
        self.cloudflare_record(zone_id, zone_name)

    def cloudflare_record(self, zone_id, zone_name):
        resource_name = "cloudflare_record"
        page_number = 0

        while True:
            page_number += 1
            params = {
                'per_page': 50,
                'page': page_number
            }

            try:
                raw_response = self.provider_instance.cf_clients.cf.zones.dns_records.get(
                    zone_id, params=params)
            except Exception as e:
                logger.error(f'Cloudflare API call failed: {e}')
                break

            records = raw_response['result']
            for record in records:
                logger.debug(
                    f"Processing {resource_name}: {record['name']} {record['type']}")
                id = record['id']
                attributes = {
                    "id": id,
                    "zone_id": zone_id,
                }
                self.hcl.process_resource(
                    resource_name, id.replace("-", "_"), attributes)
                self.hcl.add_additional_data(
                    resource_name, id, "zone_name", zone_name)

            total_pages = raw_response['result_info']['total_pages']
            if page_number >= total_pages:
                break
