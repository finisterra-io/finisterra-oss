import os
import click
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

from providers.aws.Aws import Aws
from utils.auth import auth

from rich.progress import Progress
from rich.progress import TimeElapsedColumn
from rich.progress import SpinnerColumn
from rich.progress import MofNCompleteColumn
from rich.progress import BarColumn
from rich.progress import TextColumn
from rich.progress import TaskProgressColumn

# Function to execute provider methods in parallel, with special handling for the IAM module
def execute_provider_method(provider, method_name):
    try:
        if method_name == "iam_role":
            # Special handling for IAM module
            original_region = provider.region
            provider.region = "global"
            method = getattr(provider, method_name)
            method()
            provider.region = original_region
        else:
            # Regular execution for other modules
            method = getattr(provider, method_name)
            method()
        print(f"{method_name} completed successfully.")
    except Exception as e:
        print(f"Error executing {method_name}: {str(e)}")

@click.command()
@click.option('--provider', '-p', default="aws", help='Provider name')
@click.option('--module', '-m', required=True, help='Module name(s), separated by commas or "all" for all modules')
def main(provider, module):  
    if provider == "aws":
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_session_token = os.getenv('AWS_SESSION_TOKEN')
        aws_profile = os.getenv('AWS_PROFILE')
        aws_region = os.getenv('AWS_REGION')
        if not aws_region:
            print("AWS_REGION environment variable is not defined.")
            exit()

        if aws_profile:
            session = boto3.Session(profile_name=aws_profile)
        else:
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                region_name=aws_region
            )

        sts = session.client('sts')
        aws_account_id = sts.get_caller_identity()['Account']

        auth_payload = {
            "provider": provider,
            "module": module,
            "account_id": aws_account_id,
            "region": aws_region
        }
        auth(auth_payload)

        print("Fetching AWS resources...")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        s3Bucket = f'ft-{aws_account_id}-{aws_region}-tfstate'
        dynamoDBTable = f'ft-{aws_account_id}-{aws_region}-tfstate-lock'
        stateKey = f'finisterra/generated/aws/{aws_account_id}/{aws_region}/{module}'

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn()
        )

        provider_instance = Aws(progress, script_dir, s3Bucket, dynamoDBTable, stateKey, aws_account_id, aws_region)

        # Define all provider methods for execution
        all_provider_methods = [
            'vpc', 'acm', 'apigateway', 'autoscaling', 'cloudmap', 'cloudfront', 'logs',
            'docdb', 'dynamodb', 'ec2', 'ecr', 'ecs', 'eks', 'elbv2', 'elasticache_redis',
            'elasticbeanstalk', 'iam_role', 'kms', 'aws_lambda', 'rds', 's3', 'sns', 'sqs',
            'wafv2', 'stepfunction', 'msk', 'aurora', 'security_group', 'vpc_endpoint',
            'target_group', 'elasticsearch', 'codeartifact', 'launchtemplate'
        ]

        # Check for invalid modules
        modules_to_execute = module.split(',')
        invalid_modules = [mod.strip() for mod in modules_to_execute if mod.strip() not in all_provider_methods and mod.lower() != 'all']
        if invalid_modules:
            print(f"Error: Invalid module(s) specified: {', '.join(invalid_modules)}")
            exit()

        # Handling for 'all' module
        if module.lower() == "all":
            modules_to_execute = all_provider_methods
        else:
            modules_to_execute = [mod.strip() for mod in modules_to_execute]

        max_parallel = int(os.getenv('MAX_PARALLEL', 10))
        with progress:
            with ThreadPoolExecutor(max_workers=max_parallel) as executor:
                futures = [executor.submit(execute_provider_method, provider_instance, method) for method in modules_to_execute]
                for future in as_completed(futures):
                    pass

        print("Finished processing AWS resources.")

if __name__ == "__main__":
    main()
