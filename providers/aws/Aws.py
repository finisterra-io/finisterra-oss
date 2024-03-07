import os
import boto3
import os
import re
import subprocess
import json


from utils.filesystem import create_version_file
from providers.aws.vpc import VPC
from providers.aws.vpc_endpoint import VPCEndPoint
from providers.aws.route53 import Route53
from providers.aws.acm import ACM
from providers.aws.cloudfront import CloudFront
from providers.aws.s3 import S3
from providers.aws.iam_policy import IAM_POLICY
from providers.aws.iam_role import IAM_ROLE
from providers.aws.ec2 import EC2
from providers.aws.ebs import EBS  # no module
from providers.aws.ecr import ECR
from providers.aws.ecr_public import ECR_PUBLIC
from providers.aws.ecs import ECS
from providers.aws.efs import EFS
from providers.aws.eks import EKS
from providers.aws.autoscaling import AutoScaling
from providers.aws.vpn_client import VpnClient
from providers.aws.docdb import DocDb
from providers.aws.opensearch import Opensearch
from providers.aws.elasticache_redis import ElasticacheRedis
from providers.aws.dynamodb import Dynamodb
from providers.aws.cognito_identity import CognitoIdentity
from providers.aws.cognito_idp import CognitoIDP
from providers.aws.logs import Logs
from providers.aws.cloudwatch import Cloudwatch
from providers.aws.cloudtrail import Cloudtrail
from providers.aws.cloudmap import Cloudmap
from providers.aws.backup import Backup
from providers.aws.guardduty import Guardduty
from providers.aws.apigateway import Apigateway
from providers.aws.apigatewayv2 import Apigatewayv2
from providers.aws.wafv2 import Wafv2
from providers.aws.secretsmanager import Secretsmanager
from providers.aws.ssm import SSM
from providers.aws.sqs import SQS
from providers.aws.sns import SNS
from providers.aws.rds import RDS
from providers.aws.aurora import Aurora
from providers.aws.aws_lambda import AwsLambda
from providers.aws.kms import KMS
from providers.aws.elasticbeanstalk import ElasticBeanstalk
from providers.aws.elbv2 import ELBV2
from providers.aws.stepfunction import StepFunction
from providers.aws.msk import MSK
from providers.aws.security_group import SECURITY_GROUP
from providers.aws.target_group import TargetGroup
from providers.aws.elasticsearch import Elasticsearch
from providers.aws.aws_clients import AwsClients
from providers.aws.codeartifact import CodeArtifact
from providers.aws.launchtemplate import LaunchTemplate


class Aws:
    def __init__(self, progress, script_dir, s3Bucket,
                 dynamoDBTable, state_key, aws_account_id, aws_region):
        self.progress = progress
        self.provider_name = "registry.terraform.io/hashicorp/aws"
        self.script_dir = script_dir
        self.schema_data = self.load_provider_schema()
        self.s3Bucket = s3Bucket
        self.dynamoDBTable = dynamoDBTable
        self.state_key = state_key
        self.workspace_id = None
        self.modules = []

        self.aws_region = aws_region
        self.aws_account_id = aws_account_id
        self.session = boto3.Session()
        self.aws_clients_instance = AwsClients(self.session, self.aws_region)

    def set_boto3_session(self, id_token=None, role_arn=None, session_duration=None, aws_region="us-east-1"):
        if id_token and role_arn and session_duration:
            self.aws_region = aws_region
            sts = boto3.client('sts', region_name=self.aws_region)
            response = sts.assume_role_with_web_identity(
                RoleArn=role_arn,
                RoleSessionName="FinisterraSession",
                WebIdentityToken=id_token,
                DurationSeconds=session_duration
            )
            credentials = response['Credentials']

            # Set AWS credentials for boto3
            self.session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=aws_region
            )

            os.environ['AWS_ACCESS_KEY_ID'] = credentials['AccessKeyId']
            os.environ['AWS_SECRET_ACCESS_KEY'] = credentials['SecretAccessKey']
            os.environ['AWS_SESSION_TOKEN'] = credentials['SessionToken']
            os.environ['AWS_REGION'] = self.aws_region

        else:
            aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_session_token = os.getenv("AWS_SESSION_TOKEN")
            self.aws_region = os.getenv("AWS_REGION")

            if aws_access_key_id and aws_secret_access_key and self.aws_region:
                self.session = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_session_token=aws_session_token,
                    region_name=self.aws_region,
                )
            else:
                profile = os.getenv("AWS_PROFILE")
                if profile:
                    self.session = boto3.Session(profile_name=profile)
                    if self.session._session.full_config['profiles'][profile]['mfa_serial']:
                        print(
                            "AWS credentials not found in environment variables using profile with MFA profile.")
                        mfa_serial = self.session._session.full_config['profiles']['ae-dev']['mfa_serial']
                        mfa_token = input(
                            'Please enter your 6 digit MFA code:')
                        sts = self.session.client('sts')
                        MFA_validated_token = sts.get_session_token(
                            SerialNumber=mfa_serial, TokenCode=mfa_token)
                else:
                    print(
                        "AWS credentials not found in environment")
                    return False        
                
        return True

    def upload_file_to_s3(self, local_file_path, state_file_name, target_state_file_name):
        s3_client = self.session.client(
            "s3", region_name=self.aws_region)
        try:
            s3_client.upload_file(
                os.path.join(local_file_path, state_file_name), self.s3Bucket, os.path.join(self.state_key, target_state_file_name))
            print(
                f"File {local_file_path} uploaded to {self.state_key} in bucket {self.s3Bucket}.")
        except Exception as e:
            print(
                f"An error occurred while uploading the file to S3: {str(e)}")

    def extract_arns_from_state_file(self, file_path):
        with open(file_path, 'r') as file:
            state_data = json.load(file)

        id_mapping = {}
        resources = state_data.get('resources', [])

        for resource in resources:
            resource_type = resource.get('type', '')
            instances = resource.get('instances', [])

            for instance in instances:
                attributes = instance.get('attributes', {})
                arn = attributes.get('arn', '')

                if arn:
                    id_mapping[arn] = {'resource_type': resource_type, 'type': 'arn', 'id': instance.get(
                        'attributes').get('id')}

        return id_mapping

    def process_terraform_state_files(self, folder_path):
        id_ro_resource_type = {}

        for root, _, files in os.walk(folder_path):
            for file_name in files:
                if file_name.endswith('.tfstate'):
                    file_path = os.path.join(root, file_name)
                    id_mapping = self.extract_arns_from_state_file(file_path)
                    id_ro_resource_type.update(id_mapping)

        return id_ro_resource_type

    def extract_arns(self, value, resource_type, field, attributes_id, result):
        arn_pattern = re.compile(
            r'^arn:aws[a-zA-Z-]*:([a-zA-Z0-9-_]+):[a-z0-9-]*:[0-9]{12}:[a-zA-Z0-9-_/]+')

        if isinstance(value, list):
            for item in value:
                if arn_pattern.match(str(item)):
                    result.append({
                        "resource_type": resource_type,
                        "field": field,
                        "value": item,
                        "id": attributes_id
                    })
        elif isinstance(value, dict):
            for nested_field, nested_value in value.items():
                self.extract_arns(nested_value, resource_type,
                                  f"{field}.{nested_field}", attributes_id, result)
        elif arn_pattern.match(str(value)):
            result.append({
                "resource_type": resource_type,
                "field": field,
                "value": value,
                "id": attributes_id
            })

    def arns_from_state_file(self, file_path):
        with open(file_path, 'r') as file:
            state_data = json.load(file)

        resources = state_data.get('resources', [])
        result = []

        for resource in resources:
            resource_type = resource.get('type', '')
            instances = resource.get('instances', [])

            for instance in instances:
                attributes = instance.get('attributes', {})
                attributes_id = attributes.get('id', '')

                for field, value in attributes.items():
                    self.extract_arns(value, resource_type,
                                      field, attributes_id, result)

        return result

    def process_and_collect_arns(self, folder_path):
        all_arns = []

        for root, _, files in os.walk(folder_path):
            for file_name in files:
                if file_name.endswith('.tfstate'):
                    file_path = os.path.join(root, file_name)
                    all_arns.extend(self.arns_from_state_file(file_path))

        return all_arns

    def find_children(self, current_arn, collected_arns, id_ro_resource_type, relations, visited):
        if current_arn not in id_ro_resource_type or current_arn in visited:
            return

        visited.add(current_arn)
        parent_resource_type = id_ro_resource_type[current_arn]['resource_type']

        for arn_info in collected_arns:
            value = arn_info['value']
            if value == current_arn and arn_info['resource_type'] != parent_resource_type:
                if current_arn not in relations:
                    relations[current_arn] = {
                        "parent": {
                            "id": id_ro_resource_type[current_arn]['id'],
                            "resource_type": parent_resource_type,
                        },
                        "children": []
                    }

                child = {
                    "id": arn_info['id'],
                    "resource_type": arn_info['resource_type'],
                    "field": arn_info['field'],
                    "value": arn_info['value']
                }

                relations[current_arn]['children'].append(child)

                # Recursively find children of the current child
                self.find_children(
                    child['value'], collected_arns, id_ro_resource_type, relations, visited)

    def compare_arns(self, collected_arns, id_ro_resource_type):
        relations = {}
        visited = set()

        for arn_info in collected_arns:
            value = arn_info['value']
            self.find_children(value, collected_arns,
                               id_ro_resource_type, relations, visited)

        return relations

    def display_relations(self, relations):
        for arn, relation in relations.items():
            print("Parent:")
            print(f"ARN: {arn}")
            print("  ID:", relation['parent']['id'])
            print("  Resource Type:", relation['parent']['resource_type'])
            print("Children:")
            for child in relation['children']:
                print("  ID:", child['id'])
                print("  Resource Type:", child['resource_type'])
                print("  Field:", child['field'])
                print("  Value:", child['value'])
                print()

    def relations(self):
        tffiles_folder = os.path.join(self.script_dir, "generated")
        id_ro_resource_type = self.process_terraform_state_files(
            tffiles_folder)
        # print("ARN to Resource Name mapping:")
        # print(json.dumps(id_ro_resource_type, indent=2))

        collected_arns = self.process_and_collect_arns(tffiles_folder)
        # print("ARN information collected:")
        # print(json.dumps(collected_arns, indent=2))

        relations = self.compare_arns(collected_arns, id_ro_resource_type)
        self.display_relations(relations)

    def create_folder(self, folder):
        if not os.path.exists(folder):
            os.makedirs(folder)

    def load_provider_schema(self):
        os.chdir(self.script_dir)
        temp_dir = os.path.join("tmp")
        temp_file = os.path.join(temp_dir, 'terraform_providers_schema.json')

        # If the schema file already exists, load and return its contents
        if os.path.isfile(temp_file):
            with open(temp_file, "r") as schema_file:
                return json.load(schema_file)

        # If the schema file doesn't exist, run terraform commands
        self.create_folder(temp_dir)
        os.chdir(temp_dir)
        create_version_file()

        print("Initializing Terraform...")
        subprocess.run(["terraform", "init"], check=True)

        print("Loading provider schema...")
        temp_file = os.path.join('terraform_providers_schema.json')
        with open(temp_file, 'w') as output:
            subprocess.run(["terraform", "providers", "schema",
                            "-json"], check=True, stdout=output)

        # Load the schema data from the newly created file
        with open(temp_file, "r") as schema_file:
            schema_data = json.load(schema_file)

        return schema_data

    def route53(self):
        instance = Route53(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                           self.schema_data, self.aws_region, self.s3Bucket,
                           self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.route53()

    def vpc(self):
        instance = VPC(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.vpc()
        # ec2_client = self.session.client('ec2',
        #                                   aws_session_token=self.MFA_validated_token[
        #                                       'Credentials']['SessionToken'],
        #                                   aws_secret_access_key=self.MFA_validated_token[
        #                                       'Credentials']['SecretAccessKey'],
        #                                   aws_access_key_id=self.MFA_validated_token[
        #                                       'Credentials']['AccessKeyId'],
        #                                   region_name=self.aws_region
        #                                   )

    def vpc_endpoint(self):
        instance = VPCEndPoint(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.vpc_endpoint()

    def s3(self):
        instance = S3(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                      self.schema_data, self.aws_region, self.s3Bucket,
                      self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.s3()

    def iam_policy(self):
        instance = IAM_POLICY(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                              self.schema_data, self.aws_region, self.s3Bucket,
                              self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.iam()

    def iam_role(self):
        instance = IAM_ROLE(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                            self.schema_data, self.aws_region, self.s3Bucket,
                            self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.iam()

    def acm(self):
        instance = ACM(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.acm()

    def cloudfront(self):
        instance = CloudFront(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                              self.schema_data, self.aws_region, self.s3Bucket,
                              self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.cloudfront()

    def ec2(self):
        instance = EC2(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.ec2()

    def ebs(self):
        instance = EBS(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.ebs()

    def ecr(self):
        instance = ECR(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.ecr()

    def ecr_public(self):
        instance = ECR_PUBLIC(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                              self.schema_data, self.aws_region, self.s3Bucket,
                              self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.ecr_public()

    def ecs(self):

        instance = ECS(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.ecs()

    def efs(self):
        instance = EFS(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.efs()

    def eks(self):
        instance = EKS(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.eks()

    def autoscaling(self):
        instance = AutoScaling(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                               self.schema_data, self.aws_region, self.s3Bucket,
                               self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.autoscaling()

    def vpn_client(self):
        instance = VpnClient(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                             self.schema_data, self.aws_region, self.s3Bucket,
                             self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.vpn_client()

    def docdb(self):
        instance = DocDb(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                         self.schema_data, self.aws_region, self.s3Bucket,
                         self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.docdb()

    def opensearch(self):
        instance = Opensearch(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                              self.schema_data, self.aws_region, self.s3Bucket,
                              self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.opensearch()

    def elasticache_redis(self):
        instance = ElasticacheRedis(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                                    self.schema_data, self.aws_region, self.s3Bucket,
                                    self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.elasticache_redis()

    def dynamodb(self):
        instance = Dynamodb(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                            self.schema_data, self.aws_region, self.s3Bucket,
                            self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.dynamodb()

    def cognito_identity(self):
        instance = CognitoIdentity(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                                   self.schema_data, self.aws_region, self.s3Bucket,
                                   self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.cognito_identity()

    def cognito_idp(self):
        instance = CognitoIDP(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                              self.schema_data, self.aws_region, self.s3Bucket,
                              self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.cognito_idp()

    def logs(self):
        instance = Logs(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                        self.schema_data, self.aws_region, self.s3Bucket,
                        self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.logs()

    def cloudwatch(self):
        instance = Cloudwatch(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                              self.schema_data, self.aws_region, self.s3Bucket,
                              self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.cloudwatch()

    def cloudtrail(self):
        instance = Cloudtrail(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                              self.schema_data, self.aws_region, self.s3Bucket,
                              self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.cloudtrail()

    def cloudmap(self):
        instance = Cloudmap(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                            self.schema_data, self.aws_region, self.s3Bucket,
                            self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.cloudmap()

    def backup(self):
        instance = Backup(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                          self.schema_data, self.aws_region, self.s3Bucket,
                          self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.backup()

    def guardduty(self):
        instance = Guardduty(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                             self.schema_data, self.aws_region, self.s3Bucket,
                             self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.guardduty()

    def apigateway(self):
        instance = Apigateway( self.aws_clients_instance, self.script_dir, self.provider_name,
                              self.schema_data, self.aws_region, self.s3Bucket,
                              self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.apigateway()

    def apigatewayv2(self):
        instance = Apigatewayv2(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                                self.schema_data, self.aws_region, self.s3Bucket,
                                self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.apigatewayv2()

    def wafv2(self):
        instance = Wafv2(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                         self.schema_data, self.aws_region, self.s3Bucket,
                         self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.wafv2()

    def secretsmanager(self):
        instance = Secretsmanager(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                                  self.schema_data, self.aws_region, self.s3Bucket,
                                  self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.secretsmanager()

    def ssm(self):
        instance = SSM(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.ssm()

    def sqs(self):
        instance = SQS(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.sqs()

    def sns(self):
        instance = SNS(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.sns()

    def rds(self):
        instance = RDS(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.rds()

    def aurora(self):
        instance = Aurora(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                          self.schema_data, self.aws_region, self.s3Bucket,
                          self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.aurora()

    def aws_lambda(self):
        instance = AwsLambda(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                             self.schema_data, self.aws_region, self.s3Bucket,
                             self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.aws_lambda()

    def kms(self):
        instance = KMS(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.kms()

    def elasticbeanstalk(self):

        instance = ElasticBeanstalk(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                                    self.schema_data, self.aws_region, self.s3Bucket,
                                    self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.elasticbeanstalk()

    def elbv2(self):
        instance = ELBV2(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                         self.schema_data, self.aws_region, self.s3Bucket,
                         self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.elbv2()

    def stepfunction(self):
        instance = StepFunction(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                                self.schema_data, self.aws_region, self.s3Bucket,
                                self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.stepfunction()

    def msk(self):
        instance = MSK(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.msk()

    def security_group(self):

        instance = SECURITY_GROUP(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                                  self.schema_data, self.aws_region, self.s3Bucket,
                                  self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.security_group()


    def target_group(self):

        instance = TargetGroup(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.target_group()


    def elasticsearch(self):
        instance = Elasticsearch(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.elasticsearch()


    def codeartifact(self):
        instance = CodeArtifact(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.codeartifact()

    def launchtemplate(self):
        instance = LaunchTemplate(self.progress, self.aws_clients_instance, self.script_dir, self.provider_name,
                       self.schema_data, self.aws_region, self.s3Bucket,
                       self.dynamoDBTable, self.state_key, self.workspace_id, self.modules, self.aws_account_id)
        instance.launchtemplate()
