import os
from utils.hcl import HCL
import datetime


class ACM:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id, hcl = None):
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
            self.hcl = HCL(self.schema_data, self.provider_name)
        else:
            self.hcl = hcl

        self.hcl.region = region
        self.hcl.account_id = aws_account_id
        self.progress = progress


    def acm(self):
        self.hcl.prepare_folder(os.path.join("generated"))
        self.aws_acm_certificate()
        self.progress.update(self.task, description=f"[cyan]{self.__class__.__name__} [bold]Refreshing state[/]")
        self.hcl.refresh_state()
        self.progress.update(self.task, advance=1)
        self.progress.update(self.task, description=f"[cyan]{self.__class__.__name__} [bold]Generating tf code[/]")
        self.hcl.request_tf_code()
        self.progress.update(self.task, advance=1)


    def aws_acm_certificate(self, acm_arn=None, ftstack=None):
        resource_name = "aws_acm_certificate"
        print("Processing ACM Certificates...")

        if acm_arn and ftstack:
            if self.hcl.id_resource_processed(resource_name, acm_arn, ftstack):
                print(f"  Skipping ACM Certificate: {acm_arn} already processed")
                return
            self.process_single_acm_certificate(acm_arn, ftstack)
            return

        paginator = self.aws_clients.acm_client.get_paginator("list_certificates")
        total = 0        
        for page in paginator.paginate():
            for cert_summary in page["CertificateSummaryList"]:
                total += 1

        self.task = self.progress.add_task(f"[cyan]Processing {self.__class__.__name__}...", total=total+2)
        for page in paginator.paginate():
            for cert_summary in page["CertificateSummaryList"]:
                self.progress.update(self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{cert_summary['CertificateArn'].split('/')[-1]}[/]")
                cert_arn = cert_summary["CertificateArn"]
                self.process_single_acm_certificate(cert_arn, ftstack)

    def process_single_acm_certificate(self, cert_arn, ftstack=None):
        resource_name = "aws_acm_certificate"
        # Fetch certificate details
        cert_details = self.aws_clients.acm_client.describe_certificate(CertificateArn=cert_arn)["Certificate"]
        cert_domain = cert_details["DomainName"]
        certificate_type = cert_details["Type"]
        status = cert_details["Status"]
        expiration_date = cert_details.get("NotAfter")

        # Skip processing based on certain conditions (e.g., certificate type, status, expiration)
        if certificate_type == "IMPORTED" or status != "ISSUED" or (expiration_date and expiration_date < datetime.datetime.now(tz=datetime.timezone.utc)):
            return

        print(f"Processing ACM Certificate: {cert_arn}")

        # Tag processing and other logic
        if not ftstack:
            ftstack = "acm"
            try:
                response = self.aws_clients.acm_client.list_tags_for_certificate(CertificateArn=cert_arn)
                tags = response.get('Tags', {})
                for tag in tags:
                    if tag['Key'] == 'ftstack':
                        if tag['Value'] != 'acm':
                            ftstack = "stack_" + tag['Value']
                        break
            except Exception as e:
                print("Error occurred: ", e)

        id = cert_arn
        attributes = {
            "id": id,
            "domain_name": cert_domain,
        }

        self.hcl.process_resource(resource_name, cert_arn.replace("-", "_"), attributes)
        self.hcl.add_stack(resource_name, id, ftstack)

        # self.aws_acm_certificate_validation(cert_arn, cert_details)

    def aws_acm_certificate_validation(self, cert_arn, cert):
        print(f"Processing ACM Certificate Validation: {cert_arn}")

        attributes = {
            "id": cert_arn,
            "certificate_arn": cert_arn,
        }

        if "ResourceRecord" in cert["DomainValidationOptions"][0]:
            attributes["validation_record_fqdns"] = [
                cert["DomainValidationOptions"][0]["ResourceRecord"]["Name"]]

        self.hcl.process_resource(
            "aws_acm_certificate_validation", cert_arn.replace("-", "_"), attributes)
