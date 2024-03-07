import os
import subprocess
import json
import logging

logger = logging.getLogger('finisterra')


def create_version_file(path, provider_name, provider_source, provider_version):
    file_name = os.path.join(path, "versions.tf")
    with open(file_name, "w") as version_file:
        version_file.write('terraform {\n')
        version_file.write('  required_providers {\n')
        version_file.write(f'  {provider_name} = {{\n')
        version_file.write(f'  source  = "{provider_source}"\n')
        version_file.write(f'  version = "{provider_version}"\n')
        version_file.write('}\n')
        version_file.write('}\n')
        version_file.write('}\n')


def load_provider_schema(script_dir,  provider_name, provider_source, provider_version):
    cache_dir = script_dir
    if os.environ.get('FT_CACHE_DIR', '') != '':
        cache_dir = os.environ.get('FT_CACHE_DIR')

    # Save current folder
    temp_file = os.path.join(
        cache_dir, f'terraform_providers_schema_{provider_name}.json')

    # If the schema file already exists, load and return its contents
    if not os.path.isfile(temp_file):
        create_version_file(cache_dir,  provider_name,
                            provider_source, provider_version)

        logger.info("Initializing Terraform...")
        subprocess.run(["terraform", "init"], check=True,
                       cwd=cache_dir, stdout=subprocess.PIPE)

        logger.info("Loading provider schema...")
        with open(temp_file, 'w') as output:
            subprocess.run(["terraform", "providers", "schema",
                            "-json"], check=True, stdout=output, cwd=cache_dir)

    # Load the schema data from the newly created file
    with open(temp_file, "r") as schema_file:
        schema_data = json.load(schema_file)

    return schema_data
