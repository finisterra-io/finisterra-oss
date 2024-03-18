import os
import subprocess
import http.client
import logging
from ..utils.auth import read_token_from_file
import time
import threading
import json
import boto3
from botocore.exceptions import ClientError
from ..providers.aws.aws_clients import AwsClients


logger = logging.getLogger('finisterra')


def get_web_api_conn():
    api_token = os.environ.get('FT_API_TOKEN')
    if not api_token:
        # If not defined, read the token from the file
        api_token = read_token_from_file()
    api_host = os.environ.get('FT_API_HOST_WEB', 'api.finisterra.io')
    api_port = os.environ.get('FT_API_PORT_WEB', 443)

    if api_port == 443:
        conn = http.client.HTTPSConnection(api_host)
    else:
        conn = http.client.HTTPConnection(api_host, api_port)

    headers = {
        'Content-Type': 'application/json',
        "Authorization": "Bearer " + api_token,
        "Connection": "close"
    }

    return conn, headers


def is_valid_github_repo(local_repo_path):
    # Step 1: Check if the directory exists
    if not os.path.isdir(local_repo_path):
        logger.error("Directory does not exist.")
        return False

    # Step 2: Check if the directory is a Git repository with a GitHub remote
    try:
        result = subprocess.run(["git", "-C", local_repo_path, "remote", "-v"],
                                stdout=subprocess.PIPE, check=True, text=True)
        remotes = result.stdout
        if "github.com" in remotes:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        logger.error(
            "Failed to execute Git command. Make sure the directory is a Git repository.")
        return False


def get_github_repo_name(local_repo_path):
    if not is_valid_github_repo(local_repo_path):
        return None, None

    try:
        result = subprocess.run(["git", "-C", local_repo_path, "remote", "-v"],
                                stdout=subprocess.PIPE, check=True, text=True)
        remotes = result.stdout

        for line in remotes.splitlines():
            if "github.com" in line:
                parts = line.split()
                # The URL is typically the second part of the output
                url = parts[1]
                # Removing possible credentials from the URL
                url = url.split('@')[-1]
                # Handling both SSH and HTTPS URLs
                if url.startswith("https://"):
                    repo_name = url.split('/')[-1].replace('.git', '')
                    org_name = url.split('/')[-2]
                elif url.startswith("github.com"):
                    org_name = url.split('/')[-2].split(':')[-1]
                    repo_name = url.split(':')[-1].replace('.git', '')
                    repo_name = repo_name.split('/')[-1]
                else:
                    continue  # Skip non-GitHub URLs

                logger.debug(f"GitHub repository name: {repo_name}")
                return org_name, repo_name

        # If we reach this point, no GitHub remote has been found
        logger.error("No GitHub repository name found.")
        return None, None

    except subprocess.CalledProcessError:
        logger.error("Failed to execute Git command.")
        return None


def is_gh_installed():
    conn, headers = get_web_api_conn()
    api_path = '/api/github/validate-app-install'
    logger.debug("Checking if GitHub app is installed")

    conn.request('GET', api_path, headers=headers)
    response = conn.getresponse()

    if response.status == 200:
        return True


def wait_for_enter(message, url):
    logger.info(f"{message}")
    input()
    subprocess.run(["open", url])


def install_gh():
    if not is_gh_installed():
        GITHUB_APP_NAME = os.environ.get('GITHUB_APP_NAME', 'finisterra-io')
        url = f"https://github.com/apps/{GITHUB_APP_NAME}/installations/new"
        message = f"GitHub app is not installed. \nPlease install it by visiting the following URL, or press ENTER to open it in your browser: {url}"
        threading.Thread(target=wait_for_enter, args=(
            message, url), daemon=True).start()

    else:
        return

    while not is_gh_installed():
        time.sleep(5)


def gh_push_onboarding(local_repo_path, provider, account_id, region):
    conn, headers = get_web_api_conn()

    # Create Githun api key
    payload = {
        "name": "Github",
        "description": "Github API Key",
        "hidden": False,
    }
    api_path = '/api/api-key/api-key'
    payload_json = json.dumps(payload, default=list)
    logger.debug("Creating Github FT secret...")
    conn.request('POST', api_path, body=payload_json, headers=headers)
    response = conn.getresponse()

    if response.status != 200:
        response_body = response.read()
        logger.error(f"Failed to create Github FT secret: {response_body}")
        return False

    response_json = response.read()
    createdApiKey = json.loads(response_json).get("createdApiKey")
    if not createdApiKey:
        logger.error(f"Failed to create Github FT secret: {response_body}")
        return False

    if provider == "aws":
        # push the onboarding
        _, repository_name = get_github_repo_name(local_repo_path)
        if not repository_name:
            logger.error("Failed to get repository name.")
            return False
        api_path = '/api/github/push-onboarding'

        payload = {
            "gitRepo": {"name": repository_name},
            "ftAPIKey": createdApiKey,
            "awsAccountId": account_id,
            "awsRegion": region
        }
        payload_json = json.dumps(payload, default=list)
        logger.info("Pushing to Github ...")
        conn.request('POST', api_path, body=payload_json, headers=headers)
        response = conn.getresponse()

        if response.status == 200:
            return True
        else:
            response_body = response.read()
            logger.error(f"Failed to push Github: {response_body}")
            return False


def check_aws_gh_role():
    role_name = "ft-rw-gha-cicd-role"
    logger.debug(f"Checking if the IAM role '{role_name}' exists...")
    session = boto3.Session()
    aws_clients = AwsClients(session, "us-east-1")
    try:
        response = aws_clients.iam_client.get_role(RoleName=role_name)
        # If the call above doesn't raise an exception, the role exists
        return True
    except aws_clients.iam_client.exceptions.NoSuchEntityException:
        # If a NoSuchEntityException exception is caught, the role does not exist
        return False
    except ClientError as error:
        # Handle other possible exceptions
        logger.error(f"Failed to check the IAM role due to: {error}")
        return False


def create_aws_gh_role(local_repo_path):
    if not check_aws_gh_role():
        org_name, _ = get_github_repo_name(local_repo_path)
        region = "us-east-1"
        templateURL = "https://s3.amazonaws.com/finisterra-aws-connect/ft-rw-gha-cicd-role.yaml"
        stackName = "ft-rw-gha-cicd-role"
        GitRepositoryOwner = org_name

        url = f"https://console.aws.amazon.com/cloudformation/home?region={region}#/stacks/create/review?templateURL={templateURL}&stackName={stackName}&param_GitRepositoryOwner={GitRepositoryOwner}"

        message = f"The IAM role for GitHub Actions does not exist. Please create it by visiting the following link, or press ENTER to open it in your browser: {url}"
        threading.Thread(target=wait_for_enter, args=(
            message, url), daemon=True).start()

    else:
        return

    while not check_aws_gh_role():
        time.sleep(5)
