import logging
from botocore.exceptions import ClientError

logger = logging.getLogger('finisterra')


def get_subnet_names(aws_clients, subnet_ids):
    subnet_names = []
    for subnet_id in subnet_ids:
        try:
            response = aws_clients.ec2_client.describe_subnets(SubnetIds=[
                subnet_id])
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidSubnetID.NotFound':
                logger.info(f"The subnet ID '{subnet_id}' does not exist.")
            else:
                logger.error(f"An unexpected error occurred: {e}")
            continue

        # Check if 'Subnets' key exists and it's not empty
        if not response or 'Subnets' not in response or not response['Subnets']:
            logger.debug(
                f"No subnet information found for Subnet ID: {subnet_id}")
            continue

        # Extract the 'Tags' key safely using get
        subnet_tags = response['Subnets'][0].get('Tags', [])

        # Extract the subnet name from the tags
        subnet_name = next(
            (tag['Value'] for tag in subnet_tags if tag['Key'] == 'Name'), None)

        if subnet_name:
            subnet_names.append(subnet_name)
        else:
            logger.debug(f"No 'Name' tag found for Subnet ID: {subnet_id}")

    return subnet_names

def parse_filters(filters_str):
    """
    Parses a filter string formatted as "key=value,key=value" into a list of
    dictionaries suitable for use with Boto3's describe_instances() method.
    """
    filters = []
    if filters_str:
        for filter_part in filters_str.split(','):
            key, value = filter_part.split('=')
            filters.append({
                'Name': f'tag:{key}',  # Format the name as 'tag:key'
                'Values': [value]      # Values must be a list
            })
    return filters
