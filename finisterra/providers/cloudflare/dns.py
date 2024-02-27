import os
from ...utils.hcl import HCL
import datetime
import logging

logger = logging.getLogger('finisterra')


class DNS:
    def __init__(self, progress, cf_clients, script_dir, provider_name, schema_data, output_dir, hcl=None):
        self.progress = progress

        self.cf_clients = cf_clients
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data

        if not hcl:
            self.hcl = HCL(self.schema_data, self.provider_name)
        else:
            self.hcl = hcl

        self.hcl.output_dir = output_dir

    def dns(self):
        self.hcl.prepare_folder("cloudflare",
                                "cloudflare/cloudflare", "~> 4.0")
        self.cloudflare_zone()
        if self.hcl.count_state():
            self.progress.update(
                self.task, description=f"[cyan]{self.__class__.__name__} [bold]Refreshing state[/]", total=self.progress.tasks[self.task].total+1)
            self.hcl.refresh_state()
            # self.hcl.request_tf_code()
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
        for zone in zones:
            total += 1

        if total > 0:
            self.task = self.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for zone in zones:
            print(zone)
            self.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{zone['name']}[/]")
            self.process_single_cloudflare_zone(zone_id, ftstack)

    def process_single_cloudflare_zone(self, zone_id, ftstack=None):
        resource_name = "cloudflare_zone"

        logger.debug(f"Processing {resource_name}: {zone_id}")

        # Tag processing and other logic
        # if not ftstack:
        #     ftstack = "acm"
        #     try:
        #         response = self.aws_clients.acm_client.list_tags_for_certificate(
        #             CertificateArn=cert_arn)
        #         tags = response.get('Tags', {})
        #         for tag in tags:
        #             if tag['Key'] == 'ftstack':
        #                 if tag['Value'] != 'acm':
        #                     ftstack = "stack_" + tag['Value']
        #                 break
        #     except Exception as e:
        #         logger.error("Error occurred: ", e)

        id = zone_id
        attributes = {
            "id": zone_id,
        }

        self.hcl.process_resource(
            resource_name, zone_id.replace("-", "_"), attributes)
        self.hcl.add_stack(resource_name, id, ftstack)
