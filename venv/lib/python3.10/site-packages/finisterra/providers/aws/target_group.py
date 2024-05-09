from ...utils.hcl import HCL
from ...providers.aws.acm import ACM
# from ...providers.aws.elbv2 import ELBV2
import logging
import inspect

logger = logging.getLogger('finisterra')


class TargetGroup:
    def __init__(self, provider_instance, hcl=None):
        self.provider_instance=provider_instance
        if not hcl:
            self.hcl = HCL(self.provider_instance.schema_data)
        else:
            self.hcl = hcl

        self.hcl.region = self.provider_instance.region
        self.hcl.output_dir = self.provider_instance.output_dir
        self.hcl.account_id = self.provider_instance.aws_account_id

        self.hcl.provider_name = self.provider_instance.provider_name
        self.hcl.provider_name_short = self.provider_instance.provider_name_short
        self.hcl.provider_source = self.provider_instance.provider_source
        self.hcl.provider_version = self.provider_instance.provider_version
        self.hcl.account_name = self.provider_instance.account_name

        self.acm_instance = ACM(self.provider_instance, self.hcl)
        # self.elbv2_instance = ELBV2(self.provider_instance.progress,  self.provider_instance.aws_clients, script_dir, provider_name, provider_name_short, provider_source, provider_version, schema_data,
        #                             region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, output_dir, account_name, self.hcl)

        self.load_balancers = None
        self.listeners = {}

    def get_vpc_name(self, vpc_id):
        try:
            response = self.provider_instance.aws_clients.ec2_client.describe_vpcs(VpcIds=[
                                                                 vpc_id])
            if not response or 'Vpcs' not in response or not response['Vpcs']:
                # Handle this case as required, for example:
                logger.debug(f"No VPC information found for VPC ID: {vpc_id}")
                return None

            vpc_tags = response['Vpcs'][0].get('Tags', [])
            vpc_name = next((tag['Value']
                            for tag in vpc_tags if tag['Key'] == 'Name'), None)
            return vpc_name
        except Exception as e:
            logger.error(f"Error in get_vpc_name: {e}")
            return None

    def target_group(self):
        self.hcl.prepare_folder()

        self.aws_lb_target_group()
        self.hcl.module = inspect.currentframe().f_code.co_name
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

    def aws_lb_target_group(self, target_group_arn=None, ftstack=None):
        logger.debug("Processing Load Balancer Target Groups")
        resource_type = "aws_lb_target_group"

        paginator = self.provider_instance.aws_clients.elbv2_client.get_paginator(
            'describe_target_groups')
        response_iterator = paginator.paginate()
        total = 0
        for response in response_iterator:
            total += len(response.get("TargetGroups", []))

        if total > 0 and not target_group_arn:
            self.task = self.provider_instance.progress.add_task(
                f"[cyan]Processing {self.__class__.__name__}...", total=total)

        for response in response_iterator:
            for target_group in response["TargetGroups"]:
                tg_arn = target_group["TargetGroupArn"]
                tg_name = target_group["TargetGroupName"]

                if target_group_arn and tg_arn != target_group_arn:
                    continue

                if not target_group_arn:
                    self.provider_instance.progress.update(
                        self.task, advance=1, description=f"[cyan]{self.__class__.__name__} [bold]{tg_name}[/]")

                # if tg_name != "xxxx":
                #     continue

                logger.debug(
                    f"Processing Load Balancer Target Group: {tg_name}")

                id = tg_arn
                attributes = {
                    "id": tg_arn,
                    "arn": tg_arn,
                    "name": tg_name,
                }

                if not ftstack:
                    ftstack = "target_group"
                    # Check if the target group has a tag called "ftstack"
                    if "Tags" in target_group:
                        for tag in target_group["Tags"]:
                            if tag["Key"] == "ftstack":
                                ftstack = tag["Value"]
                                break
                self.hcl.process_resource(
                    resource_type, id, attributes)

                self.hcl.add_stack(resource_type, id, ftstack)

                vpc_id = target_group["VpcId"]
                if vpc_id:
                    vpc_name = self.get_vpc_name(vpc_id)
                    if vpc_name:
                        self.hcl.add_additional_data(
                            resource_type, id, "vpc_name", vpc_name)

                # # Call the aws_lb_listener_rule function with the target_group_arn
                # self.aws_lb_listener_rule(tg_arn, ftstack)

                # # Check if the target group is used in any loadbalancer default actions
                # if not self.load_balancers:
                #     self.load_balancers = self.provider_instance.aws_clients.elbv2_client.describe_load_balancers()[
                #         "LoadBalancers"]
                # for lb in self.load_balancers:
                #     lb_arn = lb["LoadBalancerArn"]
                #     # logger.debug(f"Processing Load Balancer: {lb_arn}")

                #     if lb_arn not in self.listeners:
                #         self.listeners[lb_arn] = self.provider_instance.aws_clients.elbv2_client.describe_listeners(
                #             LoadBalancerArn=lb_arn)["Listeners"]

                #     for listener in self.listeners[lb_arn]:
                #         default_actions = listener.get('DefaultActions', [])
                #         for default_action in default_actions:
                #             if default_action.get('TargetGroupArn') == tg_arn:
                #                 self.elbv2_instance.aws_lb(lb_arn, ftstack)
                #                 break

    def aws_lb_listener_rule(self, target_group_arn, ftstack):
        logger.debug("Processing Load Balancer Listener Rules")

        if not self.load_balancers:
            self.load_balancers = self.provider_instance.aws_clients.elbv2_client.describe_load_balancers()[
                "LoadBalancers"]

        for lb in self.load_balancers:
            lb_arn = lb["LoadBalancerArn"]
            # logger.debug(f"Processing Load Balancer: {lb_arn}")

            if lb_arn not in self.listeners:
                self.listeners[lb_arn] = self.provider_instance.aws_clients.elbv2_client.describe_listeners(
                    LoadBalancerArn=lb_arn)["Listeners"]

            for listener in self.listeners[lb_arn]:
                listener_arn = listener["ListenerArn"]
                # logger.debug(f"Processing Load Balancer Listener: {listener_arn}")

                rules = self.provider_instance.aws_clients.elbv2_client.describe_rules(
                    ListenerArn=listener_arn)["Rules"]

                for rule in rules:
                    # Skip rules that don't match the target group ARN
                    if not any(action.get('TargetGroupArn') == target_group_arn for action in rule['Actions']):
                        continue

                    rule_arn = rule["RuleArn"]
                    rule_id = rule_arn.split("/")[-1]
                    if len(rule["Conditions"]) == 0:
                        continue
                    logger.debug(
                        f"    Processing Load Balancer Listener Rule: {rule_id}")

                    attributes = {
                        "id": rule_arn,
                        "condition": rule["Conditions"],
                    }

                    self.hcl.process_resource(
                        "aws_lb_listener_rule", rule_id, attributes)

                    # get the load balancer arn from the listener arn
                    load_balancer_arn = listener['LoadBalancerArn']
                    if load_balancer_arn:
                        self.elbv2_instance.aws_lb(load_balancer_arn, ftstack)

                    # self.aws_lb_listener(listener_arn, ftstack)

    def aws_lb_listener(self, listener_arn, ftstack):
        logger.debug(f"Processing Load Balancer Listener: {listener_arn}")

        attributes = {
            "id": listener_arn,
        }

        self.hcl.process_resource(
            "aws_lb_listener", listener_arn.split("/")[-1], attributes)

        # describe the listener and get me the list of all the acm arns used in the listener
        listener = self.provider_instance.aws_clients.elbv2_client.describe_listeners(
            ListenerArns=[listener_arn])
        if listener:
            certificates = listener['Listeners'][0]['Certificates']
            for certificate in certificates:
                self.acm_instance.aws_acm_certificate(
                    certificate['CertificateArn'], ftstack)

            # call self.elbv2_instance.aws_lb(target_arn, ftstack) for the load balancer arn
            load_balancer_arn = listener['Listeners'][0]['LoadBalancerArn']
            if load_balancer_arn:
                self.elbv2_instance.aws_lb(load_balancer_arn, ftstack)
