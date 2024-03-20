from ..utils.filesystem import create_version_file
from ..utils.auth import read_token_from_file
import subprocess
import os
import re
import shutil
import tempfile
import json
import http.client
import zipfile
import time
import logging

logger = logging.getLogger('finisterra')


class HCL:
    def __init__(self, schema_data):
        self.schema_data = schema_data
        self.script_dir = tempfile.mkdtemp()
        self.terraform_state_file = os.path.join(
            self.script_dir, "terraform.tfstate")
        self.module_data = {}
        self.ftstacks = {}
        self.unique_ftstacks = set()
        self.ftstacks_files = {}
        self.additional_data = {}
        self.id_key_list = ["id", "arn"]
        self.state_data = {
            "version": 4,
            "terraform_version": "1.5.0",
            "serial": 2,
            "lineage": "",
            "outputs": {},
            "resources": []
        }
        self.state_instances = {}

    def search_state_file(self, resource_type, resource_name, resource_id):
        # Search for the resource in the state
        if resource_type in self.state_instances:
            if resource_name in self.state_instances[resource_type]:
                if resource_id in self.state_instances[resource_type][resource_name]:
                    return True
        return False

    def create_state_file(self, resource_type, resource_name, attributes):
        schema_version = int(self.schema_data['provider_schemas'][self.provider_name]
                             ['resource_schemas'][resource_type]['version'])

        key = f"{resource_type}_{resource_name}"
        module = ""
        if key in self.module_data:
            module_instance = self.module_data[key]["module_instance"]
            module = f'module.{module_instance}'

        # create resource
        resource = {
            "mode": "managed",
            "module": module,
            "type": resource_type,
            "name": resource_name,
            "provider": f"provider[\"{self.provider_name}\"]",
            "instances": [
                {
                    "schema_version": schema_version,
                    "attributes": attributes
                }
            ]
        }
        self.state_data['resources'].append(resource)
        if resource_type not in self.state_instances:
            self.state_instances[resource_type] = {}
        if resource_name not in self.state_instances[resource_type]:
            self.state_instances[resource_type][resource_name] = {}
        if attributes["id"] not in self.state_instances[resource_type][resource_name]:
            self.state_instances[resource_type][resource_name][attributes["id"]] = True

    def replace_special_chars(self, input_string):
        # Define a mapping of special characters to their ASCII representations
        ascii_map = {
            ' ': '',
            '.': '-',
        }

        # Function to replace each match
        def replace(match):
            char = match.group(0)
            # Default to hex code representation
            return "_"
            # return ascii_map.get(char, f'_{ord(char):02X}_')

        # Replace using a regular expression and the replace function
        output_string = re.sub(r'\s|[-.]|\W', replace, input_string)
        return output_string

    def add_underscore(self, string):
        if string[0].isdigit():
            return '_' + string
        else:
            return string

    def process_resource(self, resource_type, resource_name, attributes):
        resource_id = attributes["id"]
        resource_name = self.add_underscore(
            self.replace_special_chars(resource_name))
        # search if resource exists in the state
        if not self.search_state_file(resource_type, resource_name, resource_id):
            self.create_state_file(
                resource_type, resource_name, attributes)

    def count_state(self):
        resource_count = {}
        try:
            for resource in self.state_data["resources"]:
                if resource["type"] in resource_count:
                    resource_count[resource["type"]] += 1
                else:
                    resource_count[resource["type"]] = 1
        except:
            pass
        return resource_count

    def count_state_file(self):
        resource_count = {}
        try:
            with open(self.terraform_state_file, "r") as state_file:
                state_data = json.load(state_file)
                for resource in state_data["resources"]:
                    if resource["type"] in resource_count:
                        resource_count[resource["type"]] += 1
                    else:
                        resource_count[resource["type"]] = 1
        except:
            pass
        return resource_count

    def refresh_state(self):
        # count resources in state file
        prev_resources_count = self.count_state()

        if not prev_resources_count:
            logger.debug("No state file found.")
            return 0

        with open(self.terraform_state_file, 'w') as state_file:
            json.dump(self.state_data, state_file, indent=2)

        # Initializing Terraform with a retry mechanism
        logger.debug("Initializing Terraform...")
        try:
            subprocess.run(["terraform", "init", "-no-color"], cwd=self.script_dir,
                           check=True, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            logger.debug("Terraform init failed, retrying in 5 seconds...")
            time.sleep(5)
            try:
                subprocess.run(["terraform", "init"], cwd=self.script_dir,
                               check=True, stdout=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                logger.error("Terraform init failed on retry.")
                return

        logger.debug("Refreshing state...")
        try:
            subprocess.run(["terraform", "refresh", "-no-color"], cwd=self.script_dir,
                           check=True, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            logger.debug("Terraform refresh failed, retrying in 5 seconds...")
            time.sleep(5)
            try:
                subprocess.run(["terraform", "refresh", "-no-color"], cwd=self.script_dir,
                               check=True, stdout=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                logger.error("Terraform refresh failed on retry.")

        # Attempt to remove the backup state file
        try:
            subprocess.run(
                ["rm", self.terraform_state_file + ".backup"], check=True)
        except Exception as e:
            logger.debug(f"Could not remove backup state file: {e}")

        logger.debug("Counting resources in state file...")
        resources_count = self.count_state_file()
        for resource in prev_resources_count:
            if resource not in resources_count:
                logger.error(
                    f'ERROR: {resource} number of resources in state file has changed {prev_resources_count[resource]} -> 0')
            elif prev_resources_count[resource] != resources_count[resource]:
                logger.error(
                    f'ERROR: {resource} number of resources in state file has changed {prev_resources_count[resource]} -> {resources_count[resource]}')
            else:
                logger.debug(
                    f'{resource} State count {prev_resources_count[resource]} -> {resources_count[resource]}')
        # logger.debug(
        #     f"State file refreshed {os.path.join(self.script_dir, 'terraform.tfstate')}")

    def create_folder(self, folder):
        if os.path.exists(folder):
            logger.debug(f"Folder '{folder}' already exists removing it.")
            [shutil.rmtree(os.path.join(folder, f)) if os.path.isdir(os.path.join(
                folder, f)) else os.remove(os.path.join(folder, f)) for f in os.listdir(folder)]
        os.makedirs(folder, exist_ok=True)

    def prepare_folder(self):
        try:
            create_version_file(self.script_dir, self.provider_name_short,
                                self.provider_source, self.provider_version)
        except Exception as e:
            logger.error(e)
            exit()

    def add_stack(self, resource_name, id, ftstack, files=None):
        if ftstack:
            if resource_name not in self.ftstacks:
                self.ftstacks[resource_name] = {}
            if id not in self.ftstacks[resource_name]:
                self.ftstacks[resource_name][id] = {}
            if "ftstack_list" not in self.ftstacks[resource_name][id]:
                self.ftstacks[resource_name][id]["ftstack_list"] = set()
            self.ftstacks[resource_name][id]["ftstack_list"].add(ftstack)
            self.unique_ftstacks.add(ftstack)
            if files:
                if ftstack not in self.ftstacks_files:
                    self.ftstacks_files[ftstack] = []
                self.ftstacks_files[ftstack].append(files)

    def id_resource_processed(self, resource_name, id, ftstack):
        if ftstack:
            if resource_name not in self.ftstacks:
                return False
            if id not in self.ftstacks[resource_name]:
                return False
            if "ftstack_list" not in self.ftstacks[resource_name][id]:
                return False
            if ftstack not in self.ftstacks[resource_name][id]["ftstack_list"]:
                return False
            return True

    def add_additional_data(self, resource_type, id, key, value):
        if resource_type not in self.additional_data:
            self.additional_data[resource_type] = {}
        if id not in self.additional_data[resource_type]:
            self.additional_data[resource_type][id] = {}
        self.additional_data[resource_type][id][key] = value

    def request_tf_code(self):
        tfstate = None
        # Check if self.terraform_state_file is file bigger than 0
        if not os.path.isfile(self.terraform_state_file):
            return
        logger.debug("Requesting Terraform code...")
        logger.debug(f"State file: {self.terraform_state_file}")
        with open(self.terraform_state_file, 'r') as f:
            tfstate = json.load(f)

        # Convert tfstate to JSON string
        tfstate_json = json.dumps(tfstate)

        # Define the API endpoint
        api_token = os.environ.get('FT_API_TOKEN')
        if not api_token:
            # If not defined, read the token from the file
            api_token = read_token_from_file()
        api_host = os.environ.get('FT_API_HOST', 'api.finisterra.io')
        api_port = os.environ.get('FT_API_PORT', 443)
        api_path = '/hcl/'

        # Create a connection to the API server
        if api_port == 443:
            conn = http.client.HTTPSConnection(api_host, api_port)
        else:
            conn = http.client.HTTPConnection(api_host, api_port)

        headers = {'Content-Type': 'application/json',
                   "Authorization": "Bearer " + api_token}

        # Define the request payload
        payload = {
            'tfstate': tfstate_json,
            'provider': self.provider_name_short,
            'provider_name': self.provider_name,
            'provider_name_short': self.provider_name_short,
            'provider_source': self.provider_source,
            'provider_version': self.provider_version,
            'ftstacks': self.ftstacks,
            'additional_data': self.additional_data,
            'id_key_list': self.id_key_list,
            'region': self.region,
            'account_id': self.account_id,
            'account_name': self.account_name,
            'module': self.module,
            'local_modules': os.environ.get('FT_LOCAL_MODULES', False)
        }

        if not tfstate_json:
            logger.debug('No resources found')
            return

        # Convert the payload to JSON string
        payload_json = json.dumps(payload, default=list)

        # Send the POST request
        conn.request('POST', api_path, body=payload_json, headers=headers)

        # Get the response from the server
        response = conn.getresponse()
        # Check if the response is successful
        if response.status == 200:
            # Read the response data
            response_data = response.read()

            try:
                if json.loads(response_data.decode()).get("message") == "No zip file created.":
                    logger.info("No code created.")
                    self.unique_ftstacks = set()
                    return False
            except UnicodeDecodeError as e:
                pass

            zip_file_path = os.path.join(self.script_dir, 'finisterra.zip')
            with open(zip_file_path, 'wb') as zip_file:
                zip_file.write(response_data)

            # clean up folder
            try:
                os.chdir(os.path.join(self.output_dir, "tf_code"))
                for stack in self.unique_ftstacks:
                    shutil.rmtree(stack)
            except:
                pass

            # Unzip the file to the current directory
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(self.output_dir)

            # Save additional files
            for ftstack, zip_files in self.ftstacks_files.items():
                for zip_file in zip_files:
                    filename = zip_file["filename"]
                    target_dir = os.path.join(
                        self.output_dir, "tf_code", ftstack)
                    os.makedirs(os.path.dirname(target_dir), exist_ok=True)
                    target_file = os.path.join(
                        target_dir, os.path.basename(filename))
                    shutil.copyfile(filename, target_file)

            print(self.script_dir)
            # shutil.rmtree(temp_dir)
            # shutil.rmtree(self.script_dir)

        else:
            logger.error(f"{response.status} {response.reason}")
            logger.info("No code created.")
            self.unique_ftstacks = set()
            return False

        conn.close()

        return True
