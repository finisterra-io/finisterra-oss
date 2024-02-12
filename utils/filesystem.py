import os 

def create_version_file(path):
    file_name = os.path.join(path, "versions.tf")
    with open(file_name, "w") as version_file:
        version_file.write('terraform {\n')
        version_file.write('  required_providers {\n')
        version_file.write('  aws = {\n')
        version_file.write('  source  = "hashicorp/aws"\n')
        version_file.write('  version = "~> 5.0"\n')
        version_file.write('}\n')
        version_file.write('}\n')
        version_file.write('}\n')
