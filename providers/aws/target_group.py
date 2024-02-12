import os
from utils.hcl import HCL
from providers.aws.acm import ACM
from providers.aws.elbv2 import ELBV2

class TargetGroup:
    def __init__(self, progress, aws_clients, script_dir, provider_name, schema_data, region, s3Bucket,
                 dynamoDBTable, state_key, workspace_id, modules, aws_account_id,hcl = None):
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
        if hcl:
            self.hcl = hcl
        else:
            self.hcl = HCL(self.schema_data, self.provider_name)

        self.hcl.region = region
        self.hcl.account_id = aws_account_id


        self.acm_instance = ACM(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)
        self.elbv2_instance = ELBV2(self.aws_clients, script_dir, provider_name, schema_data, region, s3Bucket, dynamoDBTable, state_key, workspace_id, modules, aws_account_id, self.hcl)

        self.load_balancers = None
        self.listeners = {}


    def get_vpc_name(self, vpc_id):
        try:
            response = self.aws_clients.ec2_client.describe_vpcs(VpcIds=[vpc_id])
            if not response or 'Vpcs' not in response or not response['Vpcs']:
                # Handle this case as required, for example:
                print(f"No VPC information found for VPC ID: {vpc_id}")
                return None

            vpc_tags = response['Vpcs'][0].get('Tags', [])
            vpc_name = next((tag['Value']
                            for tag in vpc_tags if tag['Key'] == 'Name'), None)
            return vpc_name
        except Exception as e:
            print(f"Error in get_vpc_name: {e}")
            return None

    def target_group(self):
        self.hcl.prepare_folder(os.path.join("generated"))

        self.aws_lb_target_group()

        self.hcl.refresh_state()


        self.hcl.request_tf_code()



    def aws_lb_target_group(self, target_group_arn=None, ftstack=None):
        print("Processing Load Balancer Target Groups")
        resource_type = "aws_lb_target_group"

        paginator = self.aws_clients.elbv2_client.get_paginator('describe_target_groups')
        response_iterator = paginator.paginate()

        for response in response_iterator:
            for target_group in response["TargetGroups"]:
                tg_arn = target_group["TargetGroupArn"]
                tg_name = target_group["TargetGroupName"]
                
                if target_group_arn and tg_arn != target_group_arn:
                    continue

                # if tg_name != "platform-int":
                #     continue
                
                print(f"Processing Load Balancer Target Group: {tg_name}")

                id = tg_arn
                attributes = {
                    "id": tg_arn,
                    "arn": tg_arn,
                    "name": tg_name,
                }
                
                if not ftstack:
                    ftstack="target_group"
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

                # Call the aws_lb_listener_rule function with the target_group_arn
                self.aws_lb_listener_rule(tg_arn, ftstack)

                #Check if the target group is used in any loadbalancer default actions
                if not self.load_balancers:     
                    self.load_balancers = self.aws_clients.elbv2_client.describe_load_balancers()[
                    "LoadBalancers"]
                for lb in self.load_balancers:
                    lb_arn = lb["LoadBalancerArn"]
                    # print(f"Processing Load Balancer: {lb_arn}")

                    if lb_arn not in self.listeners:
                        self.listeners[lb_arn] = self.aws_clients.elbv2_client.describe_listeners(
                            LoadBalancerArn=lb_arn)["Listeners"]

                    for listener in self.listeners[lb_arn]:
                        default_actions = listener.get('DefaultActions', [])
                        for default_action in default_actions:
                            if default_action.get('TargetGroupArn') == tg_arn:
                                self.elbv2_instance.aws_lb(lb_arn, ftstack)
                                break


    def aws_lb_listener_rule(self, target_group_arn, ftstack):
        print("Processing Load Balancer Listener Rules")

        if not self.load_balancers:     
            self.load_balancers = self.aws_clients.elbv2_client.describe_load_balancers()[
                "LoadBalancers"]

        for lb in self.load_balancers:
            lb_arn = lb["LoadBalancerArn"]
            # print(f"Processing Load Balancer: {lb_arn}")

            if lb_arn not in self.listeners:
                self.listeners[lb_arn] = self.aws_clients.elbv2_client.describe_listeners(
                    LoadBalancerArn=lb_arn)["Listeners"]

            for listener in self.listeners[lb_arn]:
                listener_arn = listener["ListenerArn"]
                # print(f"Processing Load Balancer Listener: {listener_arn}")

                rules = self.aws_clients.elbv2_client.describe_rules(
                    ListenerArn=listener_arn)["Rules"]

                for rule in rules:
                    # Skip rules that don't match the target group ARN
                    if not any(action.get('TargetGroupArn') == target_group_arn for action in rule['Actions']):
                        continue

                    rule_arn = rule["RuleArn"]
                    rule_id = rule_arn.split("/")[-1]
                    if len(rule["Conditions"]) == 0:
                        continue
                    print(
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
        print(f"Processing Load Balancer Listener: {listener_arn}")

        attributes = {
            "id": listener_arn,
        }

        self.hcl.process_resource(
            "aws_lb_listener", listener_arn.split("/")[-1], attributes)
        
        #describe the listener and get me the list of all the acm arns used in the listener
        listener = self.aws_clients.elbv2_client.describe_listeners(
            ListenerArns=[listener_arn])
        if listener:
            certificates = listener['Listeners'][0]['Certificates']
            for certificate in certificates:
                self.acm_instance.aws_acm_certificate(certificate['CertificateArn'], ftstack)

            # call self.elbv2_instance.aws_lb(target_arn, ftstack) for the load balancer arn
            load_balancer_arn = listener['Listeners'][0]['LoadBalancerArn']
            if load_balancer_arn:
                self.elbv2_instance.aws_lb(load_balancer_arn, ftstack)