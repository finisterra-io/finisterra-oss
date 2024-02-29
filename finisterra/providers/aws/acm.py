from ...utils.hcl import HCL
import datetime
import logging
import inspect

logger = logging.getLogger('finisterra')


class ACM:
    def __init__(self, progress, aws_clients, script_dir, provider_name, provider_name_short,
                 provider_source, provider_version, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id, output_dir, account_name, hcl=None):
        self.progress = progress

        self.aws_clients = aws_clients
        self.transform_rules = {}
        self.provider_name = provider_name
        self.script_dir = script_dir
        self.schema_data = schema_data
        self.region = region
        self.aws_account_id = aws_account_id

        self.workspace_id = workspace_id
        self.modules = modules
        if not hcl:
            self.hcl = HCL(self.schema_data)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.output_dir = output_dir
        self.hcl.account_id = aws_account_id

        self.hcl.provider_name = provider_name
        self.hcl.provider_name_short = provider_name_short
        self.hcl.provider_source = provider_source
        self.hcl.provider_version = provider_version
        self.hcl.account_name = account_name

    def acm(self):
        self.hcl.prepare_folder()
        self.aws_acm_certificate()
        self.hcl.module = inspect.currentframe().f_code.co_name
        if self.hcl.count_state():
            self.progress.update(
                self.task, description=f"[cyan]{self.__class__.__name__} [bold]Refreshing state[/]", total=self.progress.tasks[self.task].total+1)
            self.hcl.refresh_state()
            if self.hcl.request_tf_code():
                self.progress.update(
                    self.task, advance=1, description=f"[green]{self.__class__.__name__} [bold]Code Generated[/]")
            else:
                self.progress.update(
                    self.task, advance=1, description=f"[orange3]{self.__class__.__name__} [bold]No code generated[/]")
        else:
            self.task = self.progress.add_task(
                f"[orange3]{self.__class__.__name__} [bold]No resources found[/]", total=1)
            self.progress.update(self.task, advance=1)

    def aws_acm_certificate(self, acm_arn=None, ftstack=None):
        resource_name = "aws_acm_certificate"

        if acm_arn and ftstack:
            if self.hcl.id_resource_processed(resource_name, acm_arn, ftstack):
                logger.debug(
                    f"  Skipping ACM Certificate: {acm_arn} already processed")
                return
            self.process_single_acm_certificate(acm_arn, ftstack)
            return

        paginator = self.aws_clients.acm_client.get_paginator(
            "list_certificates")
        total = 0
        for page in paginator.paginate():
            for cert_summary in page["CertificateSummaryList"]:
                total += 1

        if total > 0:
            self.task = self.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)
        for page in paginator.paginate():
            for cert_summary in page["CertificateSummaryList"]:
                self.progress.update(
                    self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{cert_summary['CertificateArn'].split('/')[-1]}[/]")
                cert_arn = cert_summary["CertificateArn"]
                self.process_single_acm_certificate(cert_arn, ftstack)

    def process_single_acm_certificate(self, cert_arn, ftstack=None):
        resource_name = "aws_acm_certificate"
        # Fetch certificate details
        cert_details = self.aws_clients.acm_client.describe_certificate(
            CertificateArn=cert_arn)["Certificate"]
        cert_domain = cert_details["DomainName"]
        certificate_type = cert_details["Type"]
        status = cert_details["Status"]
        expiration_date = cert_details.get("NotAfter")

        # Skip processing based on certain conditions (e.g., certificate type, status, expiration)
        if certificate_type == "IMPORTED" or status != "ISSUED" or (expiration_date and expiration_date < datetime.datetime.now(tz=datetime.timezone.utc)):
            return

        logger.debug(f"Processing ACM Certificate: {cert_arn}")

        # Tag processing and other logic
        if not ftstack:
            ftstack = "acm"
            try:
                response = self.aws_clients.acm_client.list_tags_for_certificate(
                    CertificateArn=cert_arn)
                tags = response.get('Tags', {})
                for tag in tags:
                    if tag['Key'] == 'ftstack':
                        if tag['Value'] != 'acm':
                            ftstack = "stack_" + tag['Value']
                        break
            except Exception as e:
                logger.error("Error occurred: ", e)

        id = cert_arn
        attributes = {
            "id": id,
            "domain_name": cert_domain,
        }

        self.hcl.process_resource(
            resource_name, cert_arn.replace("-", "_"), attributes)
        self.hcl.add_stack(resource_name, id, ftstack)

        # self.aws_acm_certificate_validation(cert_arn, cert_details)

    def aws_acm_certificate_validation(self, cert_arn, cert):
        logger.debug(f"Processing ACM Certificate Validation: {cert_arn}")

        attributes = {
            "id": cert_arn,
            "certificate_arn": cert_arn,
        }

        if "ResourceRecord" in cert["DomainValidationOptions"][0]:
            attributes["validation_record_fqdns"] = [
                cert["DomainValidationOptions"][0]["ResourceRecord"]["Name"]]

        self.hcl.process_resource(
            "aws_acm_certificate_validation", cert_arn.replace("-", "_"), attributes)
