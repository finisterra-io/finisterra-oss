import os


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
