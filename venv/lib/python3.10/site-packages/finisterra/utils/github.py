import os
import subprocess
import logging
from ..utils.ft_api import read_token_from_file
import time
import threading
import json
import boto3
from botocore.exceptions import ClientError
from ..providers.aws.aws_clients import AwsClients
import requests
import tempfile
import zipfile
import glob

logger = logging.getLogger('finisterra')

class GithubUtils:
    def __init__(self, repository_name):
        self.repository_name = repository_name
        pass

    def wait_for_enter(self, message, url):
        logger.info(f"{message}")
        input()
        subprocess.run(["open", url])

    def get_web_api_conn(self):
        api_token = os.environ.get('FT_API_TOKEN')
        if not api_token:
            api_token = read_token_from_file()
        api_host = os.environ.get('FT_API_HOST', 'https://app.finisterra.io')

        headers = {
            'Content-Type': 'application/json',
            "Authorization": "Bearer " + api_token,
            "Connection": "close"
        }

        return api_host, headers

    def get_github_repo_name(self, local_repo_path):
        if not self.is_valid_github_repo(local_repo_path):
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

    def is_valid_github_repo(self):
        url, headers = self.get_web_api_conn()
        api_path = '/api/github/get-repositories'
        logger.debug("Getting the list of repositories from GitHub...")

        response = requests.get(f"{url}{api_path}", headers=headers)

        if response.status_code == 200:
            response_dict = response.json()
            repositories = response_dict.get('repositories')
            for repository in repositories:
                if repository.get('name') == self.repository_name:
                    self.org_name = repository.get('owner').get('login')
                    return True, None, False

            return False, response_dict, False

        else:
            response_body = response.text
            logger.error(
                f"Failed to get the list of repositories from GitHub: {response_body}")
            return False, None, True

    def validate_github_repo(self):
        valid, response_dict, final = self.is_valid_github_repo()
        if not valid and not final:
            installation_id = response_dict.get('installationId')
            organization = response_dict.get('organization')
            url = f"https://github.com/organizations/{organization}/settings/installations/{installation_id}"
            message = f"{self.repository_name} not in allowed repositories. \nPlease add it by visiting the following URL, or press ENTER to open it in your browser: {url}"
            threading.Thread(target=self.wait_for_enter, args=(
                message, url), daemon=True).start()
        else:
            return

        valid, response_dict, final = self.is_valid_github_repo()
        while not valid and not final:
            time.sleep(5)
            valid, response_dict, final = self.is_valid_github_repo()

    def is_gh_installed(self):
        url, headers = self.get_web_api_conn()
        api_path = '/api/github/validate-app-install'
        logger.debug("Checking if GitHub app is installed")

        response = requests.get(f"{url}{api_path}", headers=headers)

        if response.status_code == 200:
            return True

    def install_gh(self):
        installed = self.is_gh_installed()
        if not installed:
            GITHUB_APP_NAME = os.environ.get(
                'GITHUB_APP_NAME', 'finisterra-io')
            url = f"https://github.com/apps/{GITHUB_APP_NAME}/installations/new"
            message = f"GitHub app is not installed. \nPlease install it by visiting the following URL, or press ENTER to open it in your browser: {url}"
            threading.Thread(target=self.wait_for_enter, args=(
                message, url), daemon=True).start()

        else:
            return

        installed = self.is_gh_installed()
        while not installed:
            time.sleep(5)
            installed = self.is_gh_installed()

    def gh_push_onboarding(self, provider, account_id, region):
        url, headers = self.get_web_api_conn()

        # Create Githun api key
        payload = {
            "name": "Github",
            "description": "Github API Key",
            "hidden": False,
        }
        api_path = '/api/api-key/api-key'
        payload_json = json.dumps(payload, default=list)
        logger.debug("Creating Github FT secret...")
        response = requests.post(f"{url}{api_path}", headers=headers, data=payload_json)

        if response.status_code != 200:
            response_body = response.text
            logger.error(f"Failed to create Github FT secret: {response_body}")
            return False

        response_json = response.json()
        createdApiKey = response_json.get("createdApiKey")
        if not createdApiKey:
            logger.error(f"Failed to create Github FT secret: {response_body}")
            return False

        if provider == "aws":
            # push the onboarding
            if not self.repository_name:
                logger.error("Failed to get repository name.")
                return False
            api_path = '/api/github/push-onboarding'

            payload = {
                "gitRepo": {"name": self.repository_name},
                "ftAPIKey": createdApiKey,
                "awsAccountId": account_id,
                "awsRegion": region
            }
            payload_json = json.dumps(payload, default=list)
            logger.info("Pushing to Github ...")
            response = requests.post(f"{url}{api_path}", headers=headers, data=payload_json)

            if response.status_code == 200:
                return True
            else:
                response_body = response.text
                logger.error(f"Failed to push Github: {response_body}")
                return False

    def check_aws_gh_role(self):
        role_name = "ft-ro-gha-cicd-role"
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

    def create_aws_gh_role(self):
        if not self.check_aws_gh_role():
            region = "us-east-1"
            templateURL = "https://s3.amazonaws.com/finisterra-aws-connect/ft-ro-gha-cicd-role.yaml"
            stackName = "ft-ro-gha-cicd-role"
            GitRepositoryOwner = self.org_name

            url = f"https://console.aws.amazon.com/cloudformation/home?region={region}#/stacks/create/review?templateURL={templateURL}&stackName={stackName}&param_GitRepositoryOwner={GitRepositoryOwner}"

            message = f"The IAM role for GitHub Actions does not exist. Please create it by visiting the following link, or press ENTER to open it in your browser: {url}"
            threading.Thread(target=self.wait_for_enter, args=(
                message, url), daemon=True).start()

        else:
            return

        while not self.check_aws_gh_role():
            time.sleep(5)

    def gh_push_terraform_code(self, generated_path, branch_name, remote_path):
        logger.debug(
            f"Pushing Terraform code to GitHub repository: {self.repository_name} {branch_name}")
        # Create a temporary directory and zip file
        with tempfile.TemporaryDirectory() as tempdir:
            zip_path = os.path.join(tempdir, 'code.zip')

            # Zip the contents of the generated_path and the specified terragrunt files
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # First, add the original contents of the generated_path
                for root, dirs, files in os.walk(generated_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(
                            file_path, os.path.join(generated_path, '..'))
                        zipf.write(file_path, arcname)

                # Now, add the terragrunt* files from the directory above the generated_path
                terragrunt_files = glob.glob(
                    os.path.join(generated_path, '../terragrunt.hcl'))
                for file_path in terragrunt_files:
                    arcname = os.path.relpath(
                        file_path, os.path.join(generated_path, '..'))
                    zipf.write(file_path, arcname)

            # Read API token and set up API call
            api_token = os.environ.get('FT_API_TOKEN')
            if not api_token:
                api_token = read_token_from_file()
            api_host = os.environ.get('FT_API_HOST', 'https://app.finisterra.io')
            route = "api/github/push-code"

            url = f"{api_host}/{route}"

            headers = {
                "Authorization": "Bearer " + api_token,
            }

            logger.debug(f"zip_path: {zip_path}")
            files = {
                'zipFile': ('code.zip', open(zip_path, 'rb'), 'application/zip')
            }

            data = {
                "repositoryName": self.repository_name,
                "branchName": branch_name,
                "remotePath": remote_path
            }

            response = requests.post(
                url, headers=headers, data=data, files=files)

            # Ensure the file is closed after the request
            files['zipFile'][1].close()

            # Log and check the response
            if response.status_code == 200:
                response_dict = response.json()
                pr_url = response_dict.get('html_url')
                if pr_url:
                    logger.info(
                        f"Terraform code successfully pushed to GitHub. Pull request URL: {pr_url}")
                return True
            else:
                logger.error(
                    f"Failed to push Terraform code. Status: {response.status_code}, Response: {response.text}")
                return False
