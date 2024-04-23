import os
import boto3
import os
import logging


from ...utils.filesystem import load_provider_schema
from ...providers.aws.vpc import VPC
from ...providers.aws.vpc_endpoint import VPCEndPoint
from ...providers.aws.acm import ACM
from ...providers.aws.cloudfront import CloudFront
from ...providers.aws.s3 import S3
from ...providers.aws.iam_policy import IAM_POLICY
from ...providers.aws.iam_role import IAM
from ...providers.aws.ec2 import EC2
from ...providers.aws.ecr import ECR
from ...providers.aws.ecs import ECS
from ...providers.aws.eks import EKS
from ...providers.aws.autoscaling import AutoScaling
from ...providers.aws.docdb import DocDb
from ...providers.aws.elasticache_redis import ElasticacheRedis
from ...providers.aws.dynamodb import Dynamodb
from ...providers.aws.logs import Logs
from ...providers.aws.cloudmap import Cloudmap
from ...providers.aws.apigateway import Apigateway
from ...providers.aws.wafv2 import Wafv2
from ...providers.aws.sqs import SQS
from ...providers.aws.sns import SNS
from ...providers.aws.rds import RDS
from ...providers.aws.aurora import Aurora
from ...providers.aws.aws_lambda import AwsLambda
from ...providers.aws.kms import KMS
from ...providers.aws.elasticbeanstalk import ElasticBeanstalk
from ...providers.aws.elbv2 import ELBV2
from ...providers.aws.stepfunction import StepFunction
from ...providers.aws.msk import MSK
from ...providers.aws.security_group import SECURITY_GROUP
from ...providers.aws.target_group import TargetGroup
from ...providers.aws.elasticsearch import Elasticsearch
from ...providers.aws.aws_clients import AwsClients
from ...providers.aws.codeartifact import CodeArtifact
from ...providers.aws.launchtemplate import LaunchTemplate
from ...providers.aws.client_vpn import ClientVPN
from ...providers.aws.utils import parse_filters

logger = logging.getLogger('finisterra')


class Aws:
    def __init__(self, progress, script_dir, s3Bucket,
                 dynamoDBTable, state_key, aws_account_id, aws_region, output_dir, filters):
        self.progress = progress
        self.output_dir = output_dir
        self.provider_name = "registry.terraform.io/hashicorp/aws"
        self.provider_version = "~> 5.33.0"
        self.provider_name_short = "aws"
        self.provider_source = "hashicorp/aws"
        self.script_dir = script_dir
        self.schema_data = load_provider_schema(self.script_dir, "aws",
                                                "hashicorp/aws", "~> 5.33.0")
        self.s3Bucket = s3Bucket
        self.dynamoDBTable = dynamoDBTable
        self.state_key = state_key
        self.workspace_id = None
        self.modules = []

        self.region = aws_region
        self.aws_account_id = aws_account_id
        self.session = boto3.Session()
        self.aws_clients = AwsClients(self.session, self.region)
        self.account_name = self.get_account_name()

        if filters:
            self.filters = parse_filters(filters)
            logger.info(f"Filters: {self.filters}")
        else:
            self.filters = None

    def get_account_name(self):
        account_name = self.aws_account_id
        try:
            # Call the list_account_aliases API
            response = self.aws_clients.iam_client.list_account_aliases()

            # Check if any aliases exist and print the first one
            if response['AccountAliases']:
                account_name = response['AccountAliases'][0]
                logger.debug(f"Account Alias: {account_name}")
            else:
                logger.debug("No account alias found.")
        except Exception as e:
            logger.debug(f"Error fetching account alias: {e}")
        return account_name

    def set_boto3_session(self, id_token=None, role_arn=None, session_duration=None, aws_region="us-east-1"):
        if id_token and role_arn and session_duration:
            self.region = aws_region
            sts = boto3.client('sts', region_name=self.region)
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
            os.environ['AWS_REGION'] = self.region

        else:
            aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_session_token = os.getenv("AWS_SESSION_TOKEN")
            self.region = os.getenv("AWS_REGION")

            if aws_access_key_id and aws_secret_access_key and self.region:
                self.session = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_session_token=aws_session_token,
                    region_name=self.region,
                )
            else:
                profile = os.getenv("AWS_PROFILE")
                if profile:
                    self.session = boto3.Session(profile_name=profile)
                    if self.session._session.full_config['profiles'][profile]['mfa_serial']:
                        logger.error(
                            "AWS credentials not found in environment variables using profile with MFA profile.")
                        mfa_serial = self.session._session.full_config['profiles']['ae-dev']['mfa_serial']
                        mfa_token = input(
                            'Please enter your 6 digit MFA code:')
                        sts = self.session.client('sts')
                        MFA_validated_token = sts.get_session_token(
                            SerialNumber=mfa_serial, TokenCode=mfa_token)
                else:
                    logger.error(
                        "AWS credentials not found in environment")
                    return False

        return True

    def vpc(self):
        instance = VPC(self)
        instance.vpc()
        return instance.hcl.unique_ftstacks
        # ec2_client = self.session.client('ec2',
        #                                   aws_session_token=self.MFA_validated_token[
        #                                       'Credentials']['SessionToken'],
        #                                   aws_secret_access_key=self.MFA_validated_token[
        #                                       'Credentials']['SecretAccessKey'],
        #                                   aws_access_key_id=self.MFA_validated_token[
        #                                       'Credentials']['AccessKeyId'],
        #                                   region_name=self.region
        #                                   )

    def vpc_endpoint(self):
        instance = VPCEndPoint(self)
        instance.vpc_endpoint()
        return instance.hcl.unique_ftstacks

    def s3(self):
        instance = S3(self)
        instance.s3()
        return instance.hcl.unique_ftstacks

    def iam(self):
        instance = IAM(self)
        instance.iam()
        return instance.hcl.unique_ftstacks

    def acm(self):
        instance = ACM(self)
        instance.acm()
        return instance.hcl.unique_ftstacks

    def cloudfront(self):
        instance = CloudFront(self)
        instance.cloudfront()
        return instance.hcl.unique_ftstacks

    def ec2(self):
        instance = EC2(self)
        instance.ec2()
        return instance.hcl.unique_ftstacks

    def ecr(self):
        instance = ECR(self)
        instance.ecr()
        return instance.hcl.unique_ftstacks

    def ecs(self):

        instance = ECS(self)
        instance.ecs()
        return instance.hcl.unique_ftstacks

    def eks(self):
        instance = EKS(self)
        instance.eks()
        return instance.hcl.unique_ftstacks

    def autoscaling(self):
        instance = AutoScaling(self)
        instance.autoscaling()
        return instance.hcl.unique_ftstacks

    def docdb(self):
        instance = DocDb(self)
        instance.docdb()
        return instance.hcl.unique_ftstacks

    def elasticache_redis(self):
        instance = ElasticacheRedis(self)
        instance.elasticache_redis()
        return instance.hcl.unique_ftstacks

    def dynamodb(self):
        instance = Dynamodb(self)
        instance.dynamodb()
        return instance.hcl.unique_ftstacks

    def logs(self):
        instance = Logs(self)
        instance.logs()
        return instance.hcl.unique_ftstacks

    def cloudmap(self):
        instance = Cloudmap(self)
        instance.cloudmap()
        return instance.hcl.unique_ftstacks

    def apigateway(self):
        instance = Apigateway(self)
        instance.apigateway()
        return instance.hcl.unique_ftstacks

    def wafv2(self):
        instance = Wafv2(self)
        instance.wafv2()
        return instance.hcl.unique_ftstacks

    def sqs(self):
        instance = SQS(self)
        instance.sqs()
        return instance.hcl.unique_ftstacks

    def sns(self):
        instance = SNS(self)
        instance.sns()
        return instance.hcl.unique_ftstacks

    def rds(self):
        instance = RDS(self)
        instance.rds()
        return instance.hcl.unique_ftstacks

    def aurora(self):
        instance = Aurora(self)
        instance.aurora()
        return instance.hcl.unique_ftstacks

    def aws_lambda(self):
        instance = AwsLambda(self)
        instance.aws_lambda()
        return instance.hcl.unique_ftstacks

    def kms(self):
        instance = KMS(self)
        instance.kms()
        return instance.hcl.unique_ftstacks

    def elasticbeanstalk(self):

        instance = ElasticBeanstalk(self)
        instance.elasticbeanstalk()
        return instance.hcl.unique_ftstacks

    def elbv2(self):
        instance = ELBV2(self)
        instance.elbv2()
        return instance.hcl.unique_ftstacks

    def stepfunction(self):
        instance = StepFunction(self)
        instance.stepfunction()
        return instance.hcl.unique_ftstacks

    def msk(self):
        instance = MSK(self)
        instance.msk()
        return instance.hcl.unique_ftstacks

    def security_group(self):

        instance = SECURITY_GROUP(self)
        instance.security_group()
        return instance.hcl.unique_ftstacks

    def target_group(self):

        instance = TargetGroup(self)
        instance.target_group()
        return instance.hcl.unique_ftstacks

    def elasticsearch(self):
        instance = Elasticsearch(self)
        instance.elasticsearch()
        return instance.hcl.unique_ftstacks

    def codeartifact(self):
        instance = CodeArtifact(self)
        instance.codeartifact()
        return instance.hcl.unique_ftstacks

    def launchtemplate(self):
        instance = LaunchTemplate(self)
        instance.launchtemplate()
        return instance.hcl.unique_ftstacks

    def client_vpn(self):
        instance = ClientVPN(self)
        instance.client_vpn()
        return instance.hcl.unique_ftstacks
