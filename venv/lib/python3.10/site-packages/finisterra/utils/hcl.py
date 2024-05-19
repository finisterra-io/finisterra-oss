from ..utils.filesystem import create_version_file
from ..utils.ft_api import add_aws_account, add_workspace
from ..utils.filesystem import create_tmp_terragrunt, create_root_terragrunt, create_gitignore_file

import subprocess
import os
import re
import shutil
import tempfile
import json
import http.client
import time
import logging
import importlib
import hashlib
import yaml
import glob
import ssl


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
        self.provider_additional_data = ""
        self.global_region = None

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
        logger.debug(f"Script dir: {self.script_dir}")
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
                                self.provider_source, self.provider_version, self.provider_additional_data)
        except Exception as e:
            logger.error(e)
            exit()

    def prepare_terragrunt(self, folder):
        try:
            self.generated_path = os.path.join(self.script_dir, folder)
            self.create_folder(self.generated_path)
            create_tmp_terragrunt(os.path.join(
                self.generated_path), self.provider_name_short, self.provider_source, self.provider_version, self.provider_additional_data)
            logger.debug("Copying Terraform init files...")
            terraform_folder = os.path.join(
                self.generated_path, ".terraform")
            if os.path.exists(terraform_folder):
                shutil.rmtree(terraform_folder)
            temp_dir = os.path.join(self.script_dir, "tmp", ".terraform")
            # Check if temp_dir exists
            if os.path.exists(temp_dir):
                shutil.copytree(temp_dir, terraform_folder)
        except Exception as e:
            logger.error(e)
            exit()

    def get_value_from_tfstate(self, state_data, keys, type=None):
        try:
            # TO_DO handle all cases
            key = keys[0]
            if type == "string":
                value = state_data[key]
            else:
                if isinstance(state_data, list):
                    # Check if the list contains dictionaries
                    if all(isinstance(item, dict) for item in state_data):
                        # Using json.dumps to ensure double quotes
                        value = json.dumps(
                            next((item[key] for item in state_data if key in item), None))
                    else:
                        key = int(key)
                        value = state_data[key]
                else:
                    value = state_data[key]

            if len(keys) == 1:
                return value
            else:
                return self.get_value_from_tfstate(value, keys[1:], type)
        except KeyError:
            if '.'.join(keys):
                logger.warning(
                    f"Warning: field '{'.'.join(keys)}' not found in state file.")
            return None
        
    def string_repr(self, value, field_type=None, field_name=None):
        if field_type == "string" and isinstance(value, str):
            value = value.replace('\n', '')
            value = value.replace('"', '\\"')
            value = value.replace('"', '#PUT_SCAPED_QUOTE_HERE#')
            escaped_value = value.replace('${', '$${')
            return f'"{escaped_value}"'
        elif value is None:
            return json.dumps(value, indent=2)
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (list)):
            if field_type == "map":
                if len(value) == 1:
                    return json.dumps(value[0], indent=2)
            return json.dumps(value, indent=2)
        elif isinstance(value, (dict)):
            return json.dumps(value, indent=2)
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                value = value.replace('\n', '')
                escaped_value = value.replace('${', '$${')
                return f'"{escaped_value}"'

    def find_resource_config(self, config, resource_type):
        resource_config = config.get(resource_type)

        if resource_config is not None:
            return resource_config

        for key, value in config.items():
            if isinstance(value, dict):
                resource_config = self.find_resource_config(
                    value, resource_type)
                if resource_config is not None:
                    return resource_config
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        resource_config = self.find_resource_config(
                            item, resource_type)
                        if resource_config is not None:
                            return resource_config

        return None

    def match_fields(self, parent_attributes, child_attributes, join_field, functions):
        if isinstance(join_field, tuple):
            parent_field, value_dict = join_field
            parent_field = parent_field.split('.')
            # get function name from the value_dict
            join_function = value_dict.get('join_function')
            join_func = self.functions.get(join_function)
            func_name = value_dict.get('function')
            func = self.functions.get(func_name)
            arg = value_dict.get('arg')

            if func is not None:
                child_value = None
                if arg:
                    child_value = func(child_attributes, arg)
                else:
                    child_value = func(child_attributes)
                if self.get_value_from_tfstate(parent_attributes, parent_field) == child_value:
                    return True
            elif not func and func_name:
                func = getattr(self.functions_module, func_name)
                child_value = func(child_attributes, arg, self.additional_data)
                if self.get_value_from_tfstate(parent_attributes, parent_field) == child_value:
                    return True

            elif join_func is not None:
                matches = join_func(parent_attributes, child_attributes)
                return matches
            elif not join_func and join_function:
                join_func = getattr(self.functions_module, join_function)
                matches = join_func(parent_attributes, child_attributes)
                return matches

            else:
                child_field = value_dict.get('field', None)
                if child_field:
                    child_field = child_field.split('.')
                    return self.get_value_from_tfstate(parent_attributes, parent_field) == self.get_value_from_tfstate(
                        child_attributes, child_field)

        return False


    def process_resource_module(self, resource, resources, config):
        root_attributes = set()

        def process_resource(resource, resources, config, parent_root_attribute_key_value=None):

            def are_equivalent(a, b):
                if isinstance(a, list) and isinstance(b, list):
                    return sorted(a) == sorted(b)
                elif isinstance(a, dict) and isinstance(b, dict):
                    return a == b
                elif isinstance(a, set) and isinstance(b, set):
                    return a == b
                else:
                    return a == b

            def deep_update(original, update):
                """
                Recursively update a dictionary.

                :param original: original dictionary
                :param update: updated dictionary
                """
                if not isinstance(update, dict):
                    return update

                for key, value in update.items():
                    if isinstance(value, dict):
                        original[key] = deep_update(
                            original.get(key, {}), value)
                    elif isinstance(value, str) and isinstance(original.get(key), str):
                        try:
                            # Check if the string can be converted to a dictionary
                            original_value_dict = json.loads(original[key])
                            update_value_dict = json.loads(value)

                            # If conversion is successful, merge the dictionaries
                            if isinstance(original_value_dict, list):
                                original_value_dict.extend(update_value_dict)
                                original[key] = json.dumps(
                                    original_value_dict, indent=2)
                            else:
                                original[key] = json.dumps(deep_update(
                                    original_value_dict, update_value_dict), indent=2)

                        except json.JSONDecodeError:
                            # If conversion fails, it's not a 'stringified' dictionary, so just overwrite
                            original[key] = value
                    else:
                        original[key] = value
                return original

            nonlocal root_attributes
            attributes = {}
            deployed_resources = []
            resource_type = resource['type']
            resource_name = resource['name']
            resource_config = self.find_resource_config(config, resource_type)

            if resource_config is None:
                logger.info(
                    f"Warning: Config not found for resource type {resource_type}. Skipping.")
                return attributes, deployed_resources

            resource_attributes = resource['instances'][0]['attributes']
            skip_if = resource_config.get(
                'skip_if', "")

            # Check if skip_if is a dictionary and has a key called 'function'
            if isinstance(skip_if, dict) and 'function' in skip_if:
                func_name = skip_if.get('function')
                func = self.functions.get(func_name)
                arg = skip_if.get('arg', None)

                if func is not None:
                    if arg:
                        skip_if = func(resource_attributes, arg)
                    else:
                        skip_if = func(resource_attributes)

                # look in functions/all.py shared functions file
                elif not func and func_name:
                    func = getattr(self.functions_module, func_name)
                    skip_if = func(resource_attributes, arg,
                                   self.additional_data)

            if skip_if:
                logger.info(
                    f"Warning: condition not met {resource_type}. Skipping.")
                return attributes, deployed_resources

            fields_config = resource_config.get('fields', {})
            target_resource_name = resource_config.get(
                'target_resource_name', "")

            # Check if target_resource_name is a dictionary and has a key called 'function'
            if isinstance(target_resource_name, dict) and 'function' in target_resource_name:
                func_name = target_resource_name.get('function')
                func = self.functions.get(func_name)
                arg = target_resource_name.get('arg')
                if func is not None:
                    if arg:
                        target_resource_name = func(resource_attributes, arg)
                    else:
                        target_resource_name = func(resource_attributes)
                elif not func and func_name:
                    func = getattr(self.functions_module, func_name)
                    target_resource_name = func(
                        resource_attributes, arg, self.additional_data)

            target_submodule = resource_config.get('target_submodule', "")
            root_attribute = resource_config.get('root_attribute', "")
            created = True

            root_attribute_key_value = None
            if parent_root_attribute_key_value:
                root_attribute_key_value = parent_root_attribute_key_value
            root_attribute_key = resource_config.get(
                'root_attribute_key', None)

            if root_attribute != "" and root_attribute not in resource_attributes:
                if not root_attribute_key_value:
                    root_attribute_key_value = self.get_value_from_tfstate(
                        resource_attributes, [root_attribute_key],)

                if root_attribute not in attributes:
                    attributes[root_attribute] = {}
                if root_attribute_key_value not in attributes[root_attribute]:
                    attributes[root_attribute][root_attribute_key_value] = {}

                # add this root_attribute to the list
                root_attributes.add(root_attribute)

            defaults = resource_config.get('defaults', {})
            for default in defaults:
                if root_attribute and root_attribute_key_value:
                    attributes[root_attribute][root_attribute_key_value][default] = self.string_repr(
                        defaults[default])
                else:
                    attributes[default] = self.string_repr(defaults[default])

            for field, field_info in fields_config.items():
                value = None
                unique = field_info.get('unique', "N/A")
                multiline = field_info.get('multiline', False)
                jsonfield = field_info.get('jsonfield', True)
                jsonencode = field_info.get('jsonencode', False)
                default = field_info.get('default', 'N/A')
                module_default = field_info.get('module_default', 'N/A')
                func_name = field_info.get('function')
                field_type = field_info.get('type', None)
                state_field = field_info.get('field', '').split('.')
                if func_name:
                    func = self.functions.get(func_name)
                    arg = field_info.get('arg', '')
                    value = None
                    if func is not None:
                        if arg:
                            value = func(resource_attributes, arg)
                        else:
                            value = func(resource_attributes)

                    elif not func and func_name:
                        func = getattr(self.functions_module, func_name)
                        value = func(resource_attributes, arg,
                                     self.additional_data)

                elif state_field:
                    value = self.get_value_from_tfstate(
                        resource_attributes, state_field, field_type)

                if unique != "N/A":
                    id = resource_attributes.get('id', '')
                    matches = [resource for resource in self.global_deployed_resources if resource['resource_type']
                               == resource_type and resource['id'] == id]
                    if matches:
                        if field_type == "map":
                            value = {}
                        elif field_type == "list":
                            value = []
                        elif field_type == "bool":
                            value = False
                        elif field_type == "string":
                            value = ""
                        else:
                            value = None
                        created = False
                    else:
                        if value:
                            value = value
                        else:
                            value = unique
                        created = True

                defaulted = False
                if value in [None, "", [], {}] and default != 'N/A':
                    value = default
                    defaulted = True

                if module_default != 'N/A':
                    if are_equivalent(value, module_default):
                        value = None

                if value not in [None, "", [], {}, "null"] or defaulted:
                    if multiline and jsonfield:
                        value = "<<EOF\n" + \
                            json.dumps(json.loads(value), indent=2) + "\nEOF\n"
                    elif multiline and not jsonfield:
                        value = "<<EOF\n" + value + "\nEOF\n"
                    if jsonencode:
                        value = "jsonencode(" + \
                            json.dumps(json.loads(value), indent=2) + ")\n"
                    if root_attribute and root_attribute_key_value:
                        if multiline:
                            attributes[root_attribute][root_attribute_key_value][field] = value
                        else:
                            attributes[root_attribute][root_attribute_key_value][field] = self.string_repr(
                                value, field_type, field)
                    else:
                        if multiline or jsonencode:
                            attributes[field] = value
                        else:
                            attributes[field] = self.string_repr(
                                value, field_type, field)

            if created:
                first_index = resource_config.get('first_index', "")
                first_index_value = None
                if first_index:
                    enabled = first_index.get('enabled', True)
                    if not enabled:
                        first_index_value = "disabled"
                    else:
                        func_name = first_index.get('function')
                        func = self.functions.get(func_name)
                        arg = first_index.get('arg')
                        if func is not None:
                            if arg:
                                first_index_value = func(
                                    resource_attributes, arg)
                            else:
                                first_index_value = func(resource_attributes)
                        elif not func and func_name:
                            func = getattr(self.functions_module, func_name)
                            first_index_value = func(
                                resource_attributes, arg, self.additional_data)

                        else:
                            field_name = first_index.get('field')
                            if field_name:
                                first_index_value = self.get_value_from_tfstate(
                                    resource_attributes, field_name.split('.'))

                second_index = resource_config.get('second_index', "")
                second_index_value = None
                if second_index:
                    enabled = second_index.get('enabled', True)
                    if not enabled:
                        second_index_value = "disabled"
                    else:
                        func_name = second_index.get('function')
                        func = self.functions.get(func_name)
                        arg = second_index.get('arg')

                        if func is not None:
                            if arg:
                                second_index_value = func(
                                    resource_attributes, arg)
                            else:
                                second_index_value = func(resource_attributes)
                        elif not func and func_name:
                            func = getattr(self.functions_module, func_name)
                            second_index_value = func(
                                resource_attributes, arg, self.additional_data)

                        else:
                            field_name = second_index.get('field')
                            if field_name:
                                second_index_value = self.get_value_from_tfstate(
                                    resource_attributes, field_name.split('.'))

                import_id = resource_config.get('import_id', "")
                import_id_value = resource_attributes.get('id', '')
                if import_id:
                    func_name = import_id.get('function')
                    func = self.functions.get(func_name)
                    arg = import_id.get('arg')

                    if func is not None:
                        if arg:
                            import_id_value = func(
                                resource_attributes, arg)
                        else:
                            import_id_value = func(resource_attributes)
                    elif not func and func_name:
                        func = getattr(self.functions_module, func_name)
                        import_id_value = func(
                            resource_attributes, arg, self.additional_data)

                    else:
                        field_name = import_id.get('field')
                        if field_name:
                            import_id_value = self.get_value_from_tfstate(
                                resource_attributes, field_name.split('.'))

                output_fields = []
                # self.additional_output_fields = {"aws_kms_alias": [{"id_key": "id", "output": "aliases", "type": "map"}]}
                if resource_type in self.additional_output_fields:
                    additional_output = self.additional_output_fields[resource_type]
                    for item in additional_output:
                        id_key = item["id_key"]
                        key_in_key_val = None
                        if id_key in resource_attributes:
                            if "key_in_key" in item:
                                key_in_key = item["key_in_key"]
                                key_in_key_val = str(
                                    resource_attributes[key_in_key])
                            else:
                                value = resource_attributes[id_key]
                            output_fields.append({"id_key": id_key,
                                                  "output": item["output"],
                                                  "value": str(resource_attributes[id_key]),
                                                  "key_in_key": key_in_key_val,
                                                  "type": item["type"]})
                deployed_resources.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'target_resource_name': target_resource_name,
                    'target_submodule': target_submodule,
                    'id': resource_attributes.get('id', ''),
                    'import_id': import_id_value,
                    'index': root_attribute_key_value if root_attribute_key_value else '',
                    'second_index_value': second_index_value if second_index_value else '',
                    'first_index_value': first_index_value if first_index_value else '',
                    'output_fields': output_fields,
                })
                self.global_deployed_resources.append({
                    'resource_type': resource_type,
                    'resource_name': resource_name,
                    'target_resource_name': target_resource_name,
                    'target_submodule': target_submodule,
                    'id': resource_attributes.get('id', ''),
                    'import_id': import_id_value,
                    'index': root_attribute_key_value if root_attribute_key_value else '',
                    'second_index_value': second_index_value if second_index_value else '',
                    'first_index_value': first_index_value if first_index_value else '',
                    'output_fields': output_fields,
                })

            for child_type, child_config in resource_config.get('childs', {}).items():
                # Check if resource type is defined use it
                child_type = child_config.get('resource_type', child_type)
                for child_instance in [res for res in resources if res['type'] == child_type]:
                    join_fields = [
                        item for item in child_config.get('join', {}).items()]
                    match = all(self.match_fields(
                        resource_attributes, child_instance['instances'][0]['attributes'], join_field, self.functions) for join_field in join_fields)
                    if match:
                        child_attributes, child_resources = process_resource(
                            child_instance, resources, {child_type: child_config}, root_attribute_key_value)

                        if child_attributes:
                            child_attributes_copy = child_attributes.copy()
                            if 'root_attribute' in child_config:
                                root_attribute = child_config['root_attribute']
                                # make a copy of the child_attributes

                                if root_attribute in attributes and root_attribute in child_attributes:
                                    if isinstance(attributes[root_attribute], list):
                                        attributes[root_attribute].append(
                                            child_attributes[root_attribute])
                                        child_attributes_copy.pop(
                                            root_attribute)
                                    else:
                                        attributes[root_attribute] = deep_update(attributes.get(
                                            root_attribute, {}), child_attributes[root_attribute])
                                        child_attributes_copy.pop(
                                            root_attribute)

                            # update the rest of the attributes normally, using the copy
                            attributes = deep_update(
                                attributes, child_attributes_copy)

                        for child_resource in child_resources:
                            if not any(
                                    d['resource_type'] == child_resource['resource_type'] and
                                    d['resource_name'] == child_resource['resource_name']
                                    for d in deployed_resources):
                                deployed_resources.append(child_resource)

            return attributes, deployed_resources

        attributes, deployed_resources = process_resource(
            resource, resources, config)

        if attributes or deployed_resources:
            name_field = config[resource['type']].get("name_field", "name")
            joined_fields = config[resource['type']].get("joined_fields", {})
            add_id_hash_to_name = config[resource['type']].get(
                "add_id_hash_to_name", False)
            id_hash = ""
            for deployed_resource in deployed_resources:
                if deployed_resource["resource_type"] == resource['type']:
                    id_hash = hashlib.sha256(deployed_resource.get(
                        "id", "").encode()).hexdigest()[:10]
                    break

            resoource_name = attributes.get(name_field, None)
            replace_name = True
            if not resoource_name:
                resoource_name = resource['name']
                replace_name = False

            module_instance_name = resoource_name.replace("\n", "")\
                .replace('"', '')\
                .replace(" ", "_")\
                .replace(".", "_")\
                .replace("/", "_")\
                .replace("(", "_")\
                .replace(")", "_")\
                .replace("*", "_")\
                .replace("@", "_")\
                .replace("#", "_")\
                .replace("{", "_")\
                .replace("}", "_")\
                .replace("+", "_")
            output_file_prefix = config[resource['type']].get(
                "output_file_prefix", "")
            if not output_file_prefix:
                output_file_prefix = resource['type']
            module_group = config[resource['type']].get("module_group", False)
            if module_group:
                module_group_name = config[resource['type']].get(
                    "module_group_name", "")
                module_instance_name = f'{output_file_prefix}-{module_group_name}'
            else:
                module_instance_name = f'{output_file_prefix}-{module_instance_name}'
                if add_id_hash_to_name:
                    module_instance_name = f'{module_instance_name}_{id_hash}'

            result = {
                "type": resource['type'],
                "name": resoource_name,
                "replace_name": replace_name,
                "name_field": name_field,
                "attributes": attributes,
                "deployed_resources": deployed_resources,
                "add_id_hash_to_name": add_id_hash_to_name,
                "id_hash": id_hash,
                'module_instance_name': module_instance_name,
                'joined_fields': joined_fields,
            }

            for id_key in self.id_key_list:
                if id_key in resource['instances'][0]['attributes']:
                    result[id_key] = resource['instances'][0]['attributes'][id_key]

            return result
        else:
            return []

    def get_value_from_field_name(self, value, field_name):
        # If field_name is empty or contains only whitespace, return the entire value
        if not field_name.strip():
            return json.loads(value)

        # If value is a string, try to parse it as JSON
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return None  # or you can handle the error as you see fit

        # If the value is not a map, return the value directly
        if not isinstance(value, dict):
            return value

        # If the current level of the map contains the field_name, return its value
        if field_name in value:
            return value[field_name]

        # Recursively search in sub-maps
        for key, sub_value in value.items():
            if isinstance(sub_value, dict):
                result = self.get_value_from_field_name(sub_value, field_name)
                if result is not None:
                    return result

        # Return None if the field_name is not found
        return None

    def collect_json_values(self, value, parent_key=''):
        collected_values = []

        def collect_values(inner_value, current_key):
            if isinstance(inner_value, str):
                collected_values.append({current_key: inner_value})
            elif isinstance(inner_value, dict):
                for key, val in inner_value.items():
                    # Overwrite parent_key with the current key
                    collect_values(val, key)
            elif isinstance(inner_value, list):
                if all(isinstance(item, str) for item in inner_value):
                    for item in inner_value:
                        collected_values.append({current_key: item})
                else:
                    for index, item in enumerate(inner_value):
                        # Pass the same key for list items
                        collect_values(item, current_key)

        collect_values(value, parent_key)
        return collected_values

    def replace_hcl_aws_values(self,  index, value,  aws_account_id, aws_region):
        if not value:
            return value
        try:
            if isinstance(value, bool):
                value = str(value).lower()
            # Split the value into lines
            lines = value.split('\n')

            # Process each line individually
            for i, line in enumerate(lines):
                if 'module.' in line:
                    # Skip replacement for lines containing 'module'
                    continue

                if self.provider_name_short == "aws":
                    if aws_account_id:
                        line = re.sub(r'\b' + aws_account_id + r'\b',
                                      "${local.aws_account_id}", line)
                    if aws_region:
                        line = re.sub(
                            r'\b(' + aws_region + r')(?=[a-z]?\b)', "${local.aws_region}", line)
                        aws_partition = 'aws-us-gov' if 'gov' in aws_region else 'aws'
                        line = re.sub(r'\barn:' + aws_partition +
                                      r':\b', "arn:${local.aws_partition}:", line)

                # Update the processed line back in the list
                lines[i] = line

            # Join the processed lines back into a single string
            value = '\n'.join(lines)

        except Exception as e:
            logger.error(f"Error processing: {e}")
            logger.error(f"{index}, {value}")

        return value

    def replace_hcl_values(self, instance, index, value, name_value, name_field):
        if not value or not name_field or not name_value:
            return value
        try:
            if isinstance(value, bool):
                value = str(value).lower()
            # Split the value into lines
            lines = value.split('\n')

            # Define the replace_value function
            def replace_value(match):
                prefix = match.group(1) or ''
                suffix = match.group(2) if match.group(2) else ''
                if prefix.endswith('$'):
                    if re.search(r'"\w+":\s*"\$$', prefix):
                        key = re.search(r'"\w+"', prefix).group()
                        return f'    {key}: format("$%s{suffix}", local.{name_field})'
                    else:
                        return f'format("{prefix}%s{suffix}", local.{name_field})'
                elif prefix:
                    if '"' in prefix:
                        return f'{prefix}${{local.{name_field}}}{suffix}"'
                    else:
                        return f'"{prefix}${{local.{name_field}}}{suffix}"'
                else:
                    return f'"${{local.{name_field}}}{suffix}"'

            # Process each line individually
            for i, line in enumerate(lines):
                if 'module.' in line:
                    # Skip replacement for lines containing 'module'
                    continue

                if f'"{name_value}": ' in line:
                    continue

                if f': "{name_value}"' in line:
                    line = line.replace(
                        f'"{name_value}"', f'"${{local.{name_field}}}"')

                if instance["replace_name"] and "<<EOF" not in line:
                    line = re.sub(r'\"' + re.escape(name_value) +
                                  r'\"', "local." + name_field, line)

                if instance["replace_name"]:
                    pattern = r'"?(.*\$?)' + \
                        re.escape(name_value) + r'([^"]*)"?'
                    line = re.sub(pattern, replace_value, line)
                    line = line.replace('#PUT_SCAPED_QUOTE_HERE#', '\"')

                # Update the processed line back in the list
                lines[i] = line

            # Join the processed lines back into a single string
            value = '\n'.join(lines)

        except Exception as e:
            logger.debug(f"Error processing: {e}")
            logger.debug(f"{index}, {value}")

        return value


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

    def module_hcl_code(self):

        def hash_structure(structure):
            return hashlib.sha256(json.dumps(structure, sort_keys=True).encode('utf-8')).hexdigest()

        def find_repeated_structures(structure, seen_hashes, id_hash, parent_path=[], key=None):
            # Ignore None (null) structures
            if structure is None:
                return

            # Base condition for recursion: only process if dict or list and not empty
            if (isinstance(structure, dict) and structure) or (isinstance(structure, list) and structure):
                struct_hash = hash_structure(structure)
                path_str = "->".join(parent_path)

                if struct_hash in seen_hashes:
                    seen_hashes[struct_hash]['count'] += 1
                    seen_hashes[struct_hash]['paths'].append(path_str)
                else:
                    key_name = key or 'root'
                    key_name = key_name.replace("\n", "")\
                        .replace('"', '')\
                        .replace(" ", "_")\
                        .replace(".", "_")\
                        .replace("/", "_")\
                        .replace("(", "_")\
                        .replace(")", "_")\
                        .replace("*", "_")\
                        .replace("@", "_")\
                        .replace("#", "_")\
                        .replace("{", "_")\
                        .replace("}", "_")\
                        .replace("+", "_")
                    hash_suffix = struct_hash[-4:]
                    seen_hashes[struct_hash] = {
                        'count': 1,
                        'paths': [path_str],
                        'structure': structure,
                        'local': f"{key_name}_{id_hash}{hash_suffix}",
                        'key': key_name
                    }

                if isinstance(structure, dict):
                    for k, value in structure.items():
                        find_repeated_structures(
                            value, seen_hashes, id_hash, parent_path + [k], key=k)
                elif isinstance(structure, list):
                    for index, item in enumerate(structure):
                        find_repeated_structures(
                            item, seen_hashes, id_hash, parent_path + [str(index)], key=key)

        def filter_parents_with_repeated_children(seen_hashes):
            filtered_hashes = {}
            for hash_val, details in seen_hashes.items():
                if details['count'] > 1:
                    child_detected = False
                    for other_hash, other_details in seen_hashes.items():
                        if other_details['count'] > 1 and other_hash != hash_val:
                            for path in other_details['paths']:
                                if any(path.startswith(p) for p in details['paths']):
                                    child_detected = True
                                    break
                    if not child_detected:
                        filtered_hashes[hash_val] = details
            return filtered_hashes

        def replace_with_hashes(structure, seen_hashes, hash_lookup):
            if isinstance(structure, dict):
                for key in list(structure.keys()):
                    structure_hash = hash_structure(structure[key])
                    if structure_hash in hash_lookup:
                        # Use the 'local' field directly from seen_hashes
                        replacement_key = seen_hashes[structure_hash]['local']
                        structure[key] = f"local.{replacement_key}"
                    else:
                        structure[key] = replace_with_hashes(
                            structure[key], seen_hashes, hash_lookup)
            elif isinstance(structure, list):
                for i in range(len(structure)):
                    item_hash = hash_structure(structure[i])
                    if item_hash in hash_lookup:
                        # Use the 'local' field directly from seen_hashes for list items
                        replacement_key = seen_hashes[item_hash]['local']
                        structure[i] = f"local.{replacement_key}"
                    else:
                        structure[i] = replace_with_hashes(
                            structure[i], seen_hashes, hash_lookup)
            return structure

        self.prepare_terragrunt("tf_code")
        
        root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file_folder = os.path.join(
            root_path, "providers", self.short_provider_name, "config")
        

        config_file_list = glob.glob(config_file_folder + "/*.yaml")
        config = {}
        for config_file in config_file_list:
            with open(config_file, 'r') as f:
                current_config = yaml.safe_load(f)
                config.update(current_config)

        resources = self.tfstate['resources']


        instances = []

        for resource in resources:
            if resource['type'] in config:  # Check if resource is root in the config
                resource_config = config[resource['type']]
                module_group = resource_config.get('module_group', False)
                if module_group:
                    module_group_name = resource_config.get(
                        'module_group_name', "")
                    if module_group_name in self.module_groups:
                        continue
                    else:
                        self.module_groups[module_group_name] = True

                self.additional_output_fields = resource_config.get(
                    'additional_output_fields', {})
                instance = self.process_resource_module(
                    resource, resources, config)
                if not instance:
                    continue
                # For testing locally with no releases
                local_terraform_name = resource_config.get(
                    'local_terraform_name')
                if self.local_modules and local_terraform_name:
                    modules_dir = os.environ.get('MODULES_DIR', None)
                    if modules_dir:
                        instance['module'] = os.path.join(
                            modules_dir, local_terraform_name)
                        instance['version'] = None
                else:
                    terraform_module = resource_config.get('terraform_module')
                    module_version = self.module_versions.get(
                        terraform_module)
                    if not module_version:
                        repo = resource_config.get('terraform_module').split('/')[2]
                        owner = 'finisterra-io'
                        url = f'/repos/{owner}/{repo}/releases/latest'

                        # Create a connection to the GitHub API server
                        context = ssl._create_unverified_context()
                        conn = http.client.HTTPSConnection("api.github.com", context=context)

                        # Get the GitHub API token from the environment variable
                        github_api_token = os.environ.get('GITHUB_API_TOKEN')

                        # Define the headers, including a User-Agent header and the Authorization header with the token
                        headers = {
                            'User-Agent': 'Finisterra',
                            # 'Authorization': f'token {github_api_token}',
                        }

                        # Send a GET request
                        conn.request("GET", url, headers=headers)

                        # Get the response
                        response = conn.getresponse()
                        module_version = None

                        if response.status == 200:
                            # Parse the response body from JSON
                            data = json.loads(response.read())
                            module_version = data['tag_name']

                            url = f'/repos/{owner}/{repo}/git/ref/tags/{module_version}'
                            # Send a GET request
                            conn.request("GET", url, headers=headers)

                            response_hash = conn.getresponse()
                            if response.status == 200:
                                data = json.loads(response_hash.read())
                                module_version = data['object']['sha']
                                self.module_versions[terraform_module] = module_version
                            logger.debug(
                                f"Latest release: {data['ref']} {module_version}")
                        if not module_version:
                            response_data = response.read()
                            logger.debug(
                                f"Failed to fetch the latest release for {url} {response_data}")
                            module_version = resource_config.get(
                                'terraform_module_version')
                            module_version = f'v{module_version}'
                        self.module_versions[terraform_module] = module_version

                    # Close the connection
                    conn.close()

                    instance['module'] = resource_config.get(
                        'terraform_module')+f'?ref={module_version}'

                instance['path'] = resource_config.get('path', "")
                instance['dependencies'] = resource_config.get(
                    'dependencies', [])
                if resource['type'] in self.ftstacks:
                    resource_id = resource["instances"][0]["attributes"]["id"]
                    if resource_id in self.ftstacks[resource['type']]:
                        ftstack_list = self.ftstacks[resource['type']][resource_id].get(
                            "ftstack_list", [""])
                        instance['ftstack_list'] = ftstack_list
                if instance:
                    instances.append(instance)

        ids_name_map = {}
        for instance in instances:
            module_instance_name = instance["module_instance_name"]
            # root resources
            if instance["attributes"]:
                for id_key in self.id_key_list:
                    if id_key in instance:
                        id = instance[id_key]
                        if id not in ids_name_map:
                            ids_name_map[id] = {}
                        ids_name_map[id]['module'] = module_instance_name
                        ids_name_map[id]['key'] = id_key
            if instance["deployed_resources"]:
                for deployed_resource in instance["deployed_resources"]:
                    for output_field in deployed_resource['output_fields']:
                        id_key = output_field["id_key"]
                        key_in_key = output_field["key_in_key"]
                        id = output_field["value"]
                        output = output_field["output"]
                        output_type = output_field["type"]
                        if id not in ids_name_map:
                            ids_name_map[id] = {}
                        ids_name_map[id]['module'] = module_instance_name
                        ids_name_map[id]['output'] = output
                        ids_name_map[id]['key'] = id_key
                        ids_name_map[id]['key_in_key'] = key_in_key
                        ids_name_map[id]['type'] = output_type

        subfolders = {}
        for instance in instances:
            if instance["attributes"]:
                module_instance_name = instance["module_instance_name"]
                name_value = ""
                name_field = ""
                id_hash = instance["id_hash"]

                for ftstack in instance.get("ftstack_list", [""]):
                    base_path = os.path.join(
                        self.generated_path, ftstack, instance["path"])

                    module_file_path = os.path.join(
                        base_path, f'{module_instance_name}.tf')

                    if base_path:
                        os.makedirs(os.path.dirname(
                            module_file_path), exist_ok=True)
                    if base_path not in subfolders:
                        subfolders[base_path] = {
                            'dependencies': instance["dependencies"]}

                    with open(module_file_path, 'w') as file:
                        seen_hashes = {}
                        filtered_hashes = {}
                        for index, value in instance["attributes"].items():
                            # if index == "gateway_responses":
                            try:
                                value_json = json.loads(value)
                            except Exception:
                                continue

                            # uncomment to group repeated code in locals
                            # find_repeated_structures(
                            #     value_json, seen_hashes, id_hash)
                            # filtered_hashes = filter_parents_with_repeated_children(
                            #     seen_hashes)

                        if instance["replace_name"] or filtered_hashes:
                            file.write(f'locals {{\n')
                            # if instance["replace_name"]:
                            name_value = instance["name"].replace('"', '')
                            name_value_replaced = name_value

                            if self.account_id:
                                name_value_replaced = re.sub(r'\b' + self.account_id +
                                                             r'\b', "${local.aws_account_id}", name_value_replaced)
                            if self.region:
                                name_value_replaced = re.sub(
                                    r'\b(' + self.region + r')(?=[a-z]?\b)', "${local.aws_region}", name_value_replaced)
                                aws_partition = 'aws-us-gov' if 'gov' in self.region else 'aws'
                                name_value_replaced = re.sub(
                                    r'\barn:' + aws_partition + r':\b', "arn:${local.aws_partition}:", name_value_replaced)

                            name_field = f'{instance["name_field"]}'

                            if instance["add_id_hash_to_name"]:
                                name_field = f'{instance["name_field"]}_{id_hash}'
                            else:
                                hash_source = name_value+module_instance_name
                                hash_value = hashlib.sha256(
                                    hash_source.encode()).hexdigest()[:10]
                                name_field = f'{instance["name_field"]}_{hash_value}'

                            file.write(
                                f'{name_field} = "{name_value_replaced}"\n')

                            # if filtered_hashes:
                            # repeated structures
                            for hash_val, details in filtered_hashes.items():
                                local = details['local']
                                structure = json.dumps(
                                    details['structure'], indent=2)

                                file.write(
                                    f'{local} = {structure}\n')
                                # print(
                                #     f"Hash: {hash_val}, Key: {details['key']}, Count: {details['count']}, Paths: {details['paths']}, Value: {details['structure']}")

                            file.write(f'}}\n\n')

                        file.write(
                            f'module "{module_instance_name}" {{\n')
                        file.write(f'source  = "{instance["module"]}"\n')
                        # if instance["version"]:
                        #     file.write(f'version = "{instance["version"]}"\n')
                        # Find repeated data structures

                        # Create a lookup for hashes to easily check if a structure should be replaced
                        hash_lookup = {h: True for h in filtered_hashes}
                        pattern = r'"(local\.[a-zA-Z0-9_-]+)"'
                        replacement = r'\1'

                        for index, value in instance["attributes"].items():
                            try:
                                value_json = json.loads(value)
                                if index == "default_cache_behavior":
                                    print(value_json)
                                    print(filtered_hashes)
                                value_modified = replace_with_hashes(
                                    value_json, filtered_hashes, hash_lookup)

                                value = json.dumps(value_modified, indent=2)
                            except Exception:
                                # print(f"Skipping: {index} = {value}")
                                pass
                            try:
                                try:
                                    # joined fields
                                    if index in instance["joined_fields"]:
                                        joined_sub_fields = instance["joined_fields"][index].get(
                                            'sub_fields', [])
                                        value_json = json.loads(value)
                                        value_items = self.collect_json_values(
                                            value_json, index)
                                        for value_item_dict in value_items:
                                            for index_item, value_item in value_item_dict.items():
                                                if index_item in joined_sub_fields or "ALL" in joined_sub_fields:
                                                    if value_item in ids_name_map:
                                                        if module_instance_name != ids_name_map[value_item]["module"]:
                                                            output_type = ids_name_map[value_item].get(
                                                                "type", "")
                                                            if output_type == "map":
                                                                if ids_name_map[value_item]["key_in_key"]:
                                                                    value_module = "module." + \
                                                                        ids_name_map[value_item]["module"]+"."+ids_name_map[value_item]["output"]+"[\"" + \
                                                                        ids_name_map[value_item]["key_in_key"] + \
                                                                        "\"]"+"." + \
                                                                        ids_name_map[value_item]["key"]
                                                                else:
                                                                    value_module = "module." + \
                                                                        ids_name_map[value_item]["module"]+"."+ids_name_map[value_item]["output"] + \
                                                                        "[\""+value_item+"\"]"+"." + \
                                                                        ids_name_map[value_item]["key"]
                                                            else:
                                                                value_module = "module." + \
                                                                    ids_name_map[value_item]["module"] + \
                                                                    "." + \
                                                                    ids_name_map[value_item]["key"]
                                                            value = value.replace(
                                                                '"'+value_item+'"', value_module)
                                except json.JSONDecodeError:
                                    pass

                                value = self.replace_hcl_values(
                                    instance, index, value, name_value, name_field)
                                # Do not replace region in iam module
                                if index not in ["assume_role_policy", "policy_documents", "inline_policies"]:
                                    value = self.replace_hcl_aws_values(
                                        index, value, self.account_id, self.region)

                            except Exception as e:
                                logger.error(
                                    f"Error processing index {index}: {e}")
                                logger.error(value)

                            # remove quotes in the local variables
                            if type(value) == str:
                                value = re.sub(pattern, replacement, value)

                            file.write(f'{index} = {value}\n')
                        file.write('}\n')

        for key, values in subfolders.items():
            terragrunt_path = os.path.join(key, "terragrunt.hcl")

            # If the file doesn't exist, create it
            if not os.path.exists(terragrunt_path):
                with open(terragrunt_path, 'w') as file:
                    file.write('include {\n')
                    file.write('path = find_in_parent_folders()\n')
                    file.write('}\n')

                    # Filter out non-existing folders
                    existing_dependencies = [
                        d for d in values['dependencies'] if os.path.isdir(os.path.join(key, d))]

                    if existing_dependencies:
                        file.write('dependencies  {\n')
                        file.write(
                            f'paths = {json.dumps(existing_dependencies)}\n')
                        file.write('}\n')

        for instance in instances:
            module_instance_name = instance["module_instance_name"]

            for ftstack in instance.get("ftstack_list", [""]):
                base_path = os.path.join(
                    self.generated_path, ftstack, instance["path"])
                import_file_path = os.path.join(
                    base_path, f'import-{module_instance_name}.tf')

                for deployed_resource in instance["deployed_resources"]:

                    first_index_str = ""
                    if deployed_resource["first_index_value"]:
                        if deployed_resource["first_index_value"] == "disabled":
                            first_index_str = ""
                        else:
                            if isinstance(deployed_resource["first_index_value"], int):
                                first_index_str = \
                                    f'[{deployed_resource["first_index_value"]}].'
                            else:
                                first_index_str = '["' + \
                                    deployed_resource["first_index_value"]+'"].'

                    if not first_index_str and deployed_resource["target_submodule"]:
                        deployed_resource["target_submodule"] += "."

                    second_index_str = "[0]"
                    if deployed_resource["second_index_value"]:
                        if deployed_resource["second_index_value"] == "disabled":
                            second_index_str = ""
                        else:
                            if isinstance(deployed_resource["second_index_value"], int):
                                second_index_str = \
                                    f'[{deployed_resource["second_index_value"]}]'
                            else:
                                second_index_str = '["' + \
                                    deployed_resource["second_index_value"]+'"]'

                    resource_import_target = f'module.{module_instance_name}.{deployed_resource["target_submodule"]}{first_index_str}{deployed_resource["resource_type"]}.{deployed_resource["target_resource_name"]}{second_index_str}'
                    # Write to import.tf file
                    with open(import_file_path, 'a') as file:
                        file.write(
                            f'import {{\n  id = "{deployed_resource["import_id"]}"\n  to   = {resource_import_target}\n}}\n\n')

        logger.debug("Checking if terraform code was created...")

        # Check if the file exists
        if not instances:
            logger.debug("No terraform code was generated.")
            return False
        

        logger.debug("Formatting HCL files...")
        # logger.debug(self.generated_path)
        subprocess.run(["terragrunt", "run-all", "hclfmt"],
                   check=True, cwd=self.generated_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["terraform", "fmt", "-recursive"],
                       check=True, cwd=self.generated_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        

        create_gitignore_file(self.generated_path)
        # Create a backup of the terragrunt.hcl file
        shutil.copyfile(os.path.join(self.generated_path, "./terragrunt.hcl"),
                        os.path.join(self.generated_path, "./terragrunt.hcl.local-state"))
        create_root_terragrunt(self.s3Bucket, self.region,
                               self.dynamoDBTable, self.stateKey, self.provider_name_short, self.provider_source, self.provider_version, self.generated_path, self.provider_additional_data)


        unique_ftstacks = set()
        for _,instance in self.ftstacks.items():
            for _, ftstacks in instance.items():
                ftstack_list = ftstacks.get("ftstack_list", [])
                for ftstack in ftstack_list:
                    unique_ftstacks.add(ftstack)

        for ftstack in unique_ftstacks:
            # go into os.path.join(self.generated_path, ftstack), cat everything and create a hash of 10 char and put it in a file called state_hash
            ftstack_path = os.path.join(self.generated_path, ftstack)
            state_hash = hashlib.sha256()
            for root, _, files in os.walk(ftstack_path):
                for file in files:
                    with open(os.path.join(root, file), 'rb') as f:
                        state_hash.update(f.read())
            state_hash = state_hash.hexdigest()[:10]
            state_hash_file = os.path.join(ftstack_path, "state_hash")
            with open(state_hash_file, 'w') as f:
                f.write(state_hash)
        
        return True


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

        if not tfstate_json:
            logger.debug('No resources found')
            return

        self.s3Bucket = f'ft-{self.account_id}-{self.region}-tfstate'
        self.dynamoDBTable = f'ft-{self.account_id}-{self.region}-tfstate-lock'
        self.tfstate = json.loads(tfstate_json)
        self.id_key_list = ["id", "arn"] + self.id_key_list
        self.local_modules = os.environ.get('FT_LOCAL_MODULES', False)
        if self.global_region:
            self.stateKey = f'finisterra/generated/aws/{self.account_id}/{self.global_region}'
        else:
            self.stateKey = f'finisterra/generated/aws/{self.account_id}/{self.region}'
        self.short_provider_name = self.provider_name.split("/")[-1]
        functions_module_name = f'finisterra.providers.{self.short_provider_name}.functions.all'
        self.functions_module = importlib.import_module(functions_module_name)
        self.global_deployed_resources = []
        self.functions = {}
        self.module_versions = {}
        self.module_groups = {}
        self.module_version = None


        if not self.module_hcl_code():
            logger.info("No code created.")
            self.unique_ftstacks = set()
            return False
                
        # clean up folders
        try:
            os.makedirs(os.path.join(self.output_dir, "tf_code"), exist_ok=True)
            for stack in self.unique_ftstacks:
                shutil.rmtree(stack)
        except Exception as e:
            pass

        shutil.copytree(self.script_dir, self.output_dir, dirs_exist_ok=True)

        # Save additional files
        for ftstack, zip_files in self.ftstacks_files.items():
            logger.debug(f"Saving additional files for {ftstack}, {zip_files}")
            for zip_file in zip_files:
                filename = zip_file["filename"]
                target_dir = os.path.join(
                    self.output_dir, "tf_code", ftstack)
                os.makedirs(os.path.dirname(target_dir), exist_ok=True)
                target_file = os.path.join(
                    target_dir, os.path.basename(filename))
                shutil.copyfile(filename, target_file)

        shutil.rmtree(self.script_dir)

        # Add or update AWS account
        if self.provider_name_short == "aws":
            id = add_aws_account(
                account_id=self.account_id,
                name=self.account_name,
                region=self.region,
                role_arn=f"arn:aws:iam::{self.account_id}:role/ft-ro-gha-cicd-role",
            )
            if id:
                if self.global_region:
                    wokspace_region = "global"
                else:
                    wokspace_region = self.region
                workspace_name = f'{self.account_id}-{wokspace_region}-{self.module}'

                add_workspace(
                    name=workspace_name,
                    account_id=id,
                    provider="AWS",
                    provider_group_code=self.module,
                    region=wokspace_region,
                )

            
        return True
