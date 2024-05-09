import os
import click
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import logging
from rich.logging import RichHandler
import tempfile


from rich.console import Console
from rich.traceback import Traceback


from .providers.aws.Aws import Aws
from .providers.cloudflare.Cloudflare import Cloudflare
from .providers.pagerduty.PagerDuty import PagerDuty
from .providers.kafka.Kafka import Kafka

from .utils.ft_api import auth
from .utils.tf_plan import execute_terraform_plan, print_tf_plan
from .utils.github import GithubUtils


from rich.progress import Progress
from rich.progress import TimeElapsedColumn
from rich.progress import SpinnerColumn
from rich.progress import MofNCompleteColumn
from rich.progress import BarColumn
from rich.progress import TextColumn
from rich.progress import TaskProgressColumn

console = Console()
ftstacks = set()


def execute_provider_method(provider, method_name):
    try:
        method = getattr(provider, method_name)
        result = method()
        return result
    except Exception as e:
        # Log fail status
        console.log(
            f"[bold red]Error executing {method_name}[/bold red]: {str(e)}", style="bold red")
        console.print(Traceback())
        return set()


@click.command()
@click.option('--provider', '-p', default="aws", help='Provider name')
@click.option('--module', '-m', required=True, help='Module name(s), separated by commas or "all" for all modules')
@click.option('--output_dir', '-o', default=os.getcwd(), help='Output directory')
@click.option('--process_dependencies', '-d', default=True, help='Process dependencies')
@click.option('--run-plan', '-r', default=True, help='Run plan')
@click.option('--token', '-t', default=None, help='Token')
@click.option('--cache-dir', '-c', default=None, help='Cache directory to save the terraform providers schema')
@click.option('--filters', '-f', default=None, help='Filters to apply to the resources')
@click.option('--github-push-repo', '-ghr', default=None, help='Push to GitHub repository')
@click.option('--stack-name', '-s', default=None, help='Stack name')
def main(provider, module, output_dir, process_dependencies, run_plan, token, cache_dir, filters, github_push_repo, stack_name):

    if github_push_repo and output_dir != os.getcwd():
        raise click.UsageError(
            "Cannot specify '--output_dir' when '--github-push-repo' is provided. Please remove the '--output_dir' option.")

    if output_dir:
        output_dir = os.path.abspath(output_dir)

    if not os.environ.get('FT_PROCESS_DEPENDENCIES'):
        os.environ['FT_PROCESS_DEPENDENCIES'] = str(process_dependencies)

    if not os.environ.get('FT_CACHE_DIR') and cache_dir:
        os.environ['FT_CACHE_DIR'] = cache_dir

    setup_logger()
    logger = logging.getLogger('finisterra')

    if token:
        os.environ['FT_API_TOKEN'] = token

    if github_push_repo:
        github_utils = GithubUtils(github_push_repo)
        output_dir = tempfile.mkdtemp()

    progress = Progress(
        SpinnerColumn(spinner_name="dots"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn(
            "[progress.description]{task.description}"),
        console=console
    )

    execute = False

    if provider == "cloudflare":
        account_id = ""
        region = "global"
        auth_payload = {
            "provider": provider,
            "module": module,
            "account_id": account_id,
            "region": region
        }
        auth(auth_payload)
        execute = True

        script_dir = tempfile.mkdtemp()
        provider_instance = Cloudflare(
            progress, script_dir, output_dir, filters)

        # Define all provider methods for execution
        all_provider_methods = [
            'dns',
        ]

    if provider == "pagerduty":
        account_id = ""
        region = "global"
        auth_payload = {
            "provider": provider,
            "module": module,
            "account_id": account_id,
            "region": region
        }
        auth(auth_payload)
        execute = True

        script_dir = tempfile.mkdtemp()
        provider_instance = PagerDuty(
            progress, script_dir, output_dir, filters)

        # Define all provider methods for execution
        all_provider_methods = [
            'user',
        ]

    if provider == "kafka":
        account_id = ""
        region = "global"
        auth_payload = {
            "provider": provider,
            "module": module,
            "account_id": account_id,
            "region": region
        }
        auth(auth_payload)
        execute = True

        script_dir = tempfile.mkdtemp()
        provider_instance = Kafka(
            progress, script_dir, output_dir, filters)

        # Define all provider methods for execution
        all_provider_methods = [
            'kafka',
        ]

    if provider == "aws":
        execute = True
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_session_token = os.getenv('AWS_SESSION_TOKEN')
        aws_profile = os.getenv('AWS_PROFILE')
        region = os.getenv('AWS_REGION')
        if not region:
            logger.error("AWS_REGION environment variable is not defined.")
            exit()

        if aws_profile:
            session = boto3.Session(profile_name=aws_profile)
        else:
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                region_name=region
            )

        sts = session.client('sts')
        account_id = sts.get_caller_identity()['Account']

        auth_payload = {
            "provider": provider,
            "module": module,
            "account_id": account_id,
            "region": region
        }
        auth(auth_payload)

        s3Bucket = f'ft-{account_id}-{region}-tfstate'
        dynamoDBTable = f'ft-{account_id}-{region}-tfstate-lock'
        stateKey = f'finisterra/generated/aws/{account_id}/{region}/{module}'
        script_dir = tempfile.mkdtemp()

        provider_instance = Aws(progress, script_dir, s3Bucket, dynamoDBTable,
                                stateKey, account_id, region, output_dir, filters)

        # Define all provider methods for execution
        all_provider_methods = [
            'vpc',
            'acm',
            'apigateway',
            'autoscaling',
            'cloudmap',
            'cloudfront',
            'logs',
            'docdb',
            'dynamodb',
            'ec2',
            'ecr',
            'ecs',
            'eks',
            'elbv2',
            'elasticache_redis',
            'elasticbeanstalk',
            'iam',
            'kms',
            'aws_lambda',
            'rds',
            's3',
            'sns',
            'sqs',
            'wafv2',
            'stepfunction',
            'msk',
            'aurora',
            'security_group',
            'vpc_endpoint',
            'target_group',
            'elasticsearch',
            'codeartifact',
            'launchtemplate',
            'client_vpn',
        ]

    if github_push_repo:
        # Install the Github App
        github_utils.install_gh()
        # Validate Repository permissions
        github_utils.validate_github_repo()
        github_utils.create_aws_gh_role()

    if execute:
        with progress:
            logger.info(f"Fetching {provider} resources...")

            # Check for invalid modules
            modules_to_execute = set(module.split(','))
            invalid_modules = [mod.strip() for mod in modules_to_execute if mod.strip(
            ).lower() not in all_provider_methods and mod.lower() != 'all']
            if invalid_modules:
                logger.error(
                    f"Error: Invalid module(s) specified: {', '.join(invalid_modules)}")
                exit()

            # Handling for 'all' module
            if module.lower() == "all":
                modules_to_execute = all_provider_methods
            else:
                modules_to_execute = [mod.strip()
                                      for mod in modules_to_execute]

            max_parallel = int(os.getenv('MAX_PARALLEL', 5))
            results = []
            with ThreadPoolExecutor(max_workers=max_parallel) as executor:
                futures = [executor.submit(
                    execute_provider_method, provider_instance, method) for method in modules_to_execute]
                for future in as_completed(futures):
                    results.append(future.result())

            # After collecting all results, update ftstacks once
            global ftstacks
            for result in results:
                ftstacks = ftstacks.union(result)

        stack_code_generated = False
        base_dir = os.path.join(output_dir, "tf_code")
        for ftstack in ftstacks:
            generated_path = os.path.join(base_dir, ftstack)
            if stack_name:
                stack_path = os.path.join(base_dir, stack_name)
                os.makedirs(stack_path, exist_ok=True)
                for item in os.listdir(generated_path):
                    item_path = os.path.join(generated_path, item)
                    destination_path = os.path.join(stack_path, item)
                    try:
                        shutil.move(item_path, destination_path)
                    except shutil.Error:
                        pass
                shutil.rmtree(generated_path)
                generated_path = stack_path
                stack_code_generated = True

        if stack_code_generated:
            ftstacks = [stack_name]

        destroy_count = 0
        if run_plan and ftstacks:
            # check if the output directory exists
            os.chdir(os.path.join(output_dir, "tf_code"))
            shutil.copyfile(os.path.join(base_dir, "terragrunt.hcl"),
                            os.path.join(base_dir, "terragrunt.hcl.remote-state"))
            shutil.copyfile(os.path.join(
                base_dir, "terragrunt.hcl.local-state"), os.path.join(base_dir, "terragrunt.hcl"))

            results = []  # Initialize a list to store results
            with ThreadPoolExecutor(max_workers=max_parallel) as executor:
                future_to_ftstack = {executor.submit(
                    execute_terraform_plan, console, output_dir, ftstack): ftstack for ftstack in ftstacks}
                for future in as_completed(future_to_ftstack):
                    result = future.result()
                    if result:
                        # Collect results for later processing
                        results.append(result)

            # Restore original terragrunt.hcl files after all plans have been executed
            os.chdir(os.path.join(output_dir, "tf_code"))
            shutil.copyfile(os.path.join(base_dir, "terragrunt.hcl"), os.path.join(
                base_dir, "terragrunt.hcl.local-state"))
            shutil.copyfile(os.path.join(base_dir, "terragrunt.hcl.remote-state"),
                            os.path.join(base_dir, "terragrunt.hcl"))

            # Process the results after all plans are done
            for counts, updates, ftstack in results:
                console.print(
                    f"\n[bold]Terraform Plan for {ftstack}[/bold]")
                formated_counts = print_tf_plan(counts, updates, ftstack)
                destroy_count += formated_counts['destroy']
                console.print('-' * 50)
        

        if github_push_repo:
            if not github_utils.gh_push_onboarding(provider, account_id, region):
                exit()

            for ftstack in ftstacks:
                generated_path = os.path.join(base_dir, ftstack)
                # clean the .terraform* directory from the generated path recursively
                for root, dirs, files in os.walk(generated_path):
                    for file in files:
                        if file.startswith('.terraform'):
                            os.remove(os.path.join(root, file))
                    for dir in dirs:
                        if dir.startswith('.terraform'):
                            shutil.rmtree(os.path.join(root, dir))
                branch_name = f"{ftstack}.{provider}.{account_id}.{region}"
                remote_path = f"finisterra/generated/aws/{account_id}/{region}"
                if not github_utils.gh_push_terraform_code(generated_path, branch_name, remote_path):
                    exit()
        else:
            for ftstack in ftstacks:
                generated_path = os.path.join(base_dir, ftstack)
                if not github_push_repo:
                    logger.info(f"Terraform code created at: {generated_path}")

        exit(destroy_count)


def setup_logger():
    # Set the log level for the root logger to NOTSET (this is required to allow handlers to control the logging level)
    logging.root.setLevel(logging.NOTSET)

    # Configure your application's logger
    log_level_name = os.getenv('FT_LOG_LEVEL', 'INFO').upper()
    app_log_level = getattr(logging, log_level_name, logging.INFO)

    # Setup the 'finisterra' logger to use RichHandler with the shared console instance
    logger = logging.getLogger('finisterra')
    logger.setLevel(app_log_level)
    rich_handler = RichHandler(
        console=console, show_time=False, show_level=True, show_path=False)
    rich_handler.setLevel(app_log_level)
    # Replace any default handlers with just the RichHandler
    logger.handlers = [rich_handler]

    # Set higher logging level for noisy libraries
    logging.getLogger('boto3').setLevel(logging.INFO)
    logging.getLogger('botocore').setLevel(logging.INFO)
    logging.getLogger('urllib3').setLevel(logging.INFO)


if __name__ == "__main__":
    main()
