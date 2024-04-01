from ...utils.hcl import HCL
import logging
import inspect

logger = logging.getLogger('finisterra')


class User:
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

    def user(self):
        self.hcl.prepare_folder()
        self.hcl.module = inspect.currentframe().f_code.co_name

        self.pagerduty_user()
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

    def pagerduty_user(self):
        resource_name = "pagerduty_user"

        users_list = list(
            self.provider_instance.api_clients.pagerduty_client.iter_all('users'))
        total = len(users_list)

        if total > 0:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)

        # Iterate over the list of users
        for user in users_list:
            name = user['name']
            id = user['id']

            self.provider_instance.progress.update(
                self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{name}[/]")
            logger.debug(f"Processing {resource_name}: {name}")
            ftstack = "pagerduty"

            attributes = {
                "id": id,
            }

            self.hcl.process_resource(
                resource_name, id, attributes)
            self.hcl.add_stack(resource_name, id, ftstack)
