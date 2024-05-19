import os
import logging
import json
import requests

logger = logging.getLogger('finisterra')

CREDENTIALS_FILE = os.path.expanduser('~/.finisterra/credentials.json')

def save_token_to_file(token):
    os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
    with open(CREDENTIALS_FILE, 'w') as file:
        json.dump({"credentials": {"app.finisterra.io": {"token": token}}}, file)

def read_token_from_file():
    try:
        with open(CREDENTIALS_FILE, 'r') as file:
            data = json.load(file)
            return data["credentials"]["app.finisterra.io"]["token"]
    except (FileNotFoundError, KeyError):
        return None

def delete_token_from_file():
    try:
        if os.path.exists(CREDENTIALS_FILE):
            os.remove(CREDENTIALS_FILE)  # Directly removing file instead of editing
    except Exception as e:
        logger.error(f"Failed to delete token from file: {e}")

def prompt_for_token(auth_url):
    print("\033[1;96mPlease authenticate by visiting the following URL:\033[0m")
    print(auth_url)
    print("\033[1;96mAfter obtaining the token, please enter it below:\033[0m")
    return input("Token: ")

def get_url(api_part):
    api_host = os.environ.get('FT_API_HOST', 'https://app.finisterra.io')
    return f"{api_host}/{api_part}"

def get_headers():
    api_token = os.environ.get('FT_API_TOKEN')
    if not api_token:
        api_token = read_token_from_file()

    if not api_token:
        auth_url = get_url('organization/apikeys')
        api_token = prompt_for_token(auth_url)
        if api_token:
            os.environ['FT_API_TOKEN'] = api_token
            save_token_to_file(api_token)
        else:
            logger.error("No token provided.")
            exit()

    return {
        'Content-Type': 'application/json',
        "Authorization": "Bearer " + api_token
    }

def auth(payload):
    headers = get_headers()

    # validate if account is active
    url = get_url('api/aws/account-by-id-region')
    logger.debug(f"Validating account... {url} {payload} {headers}")
    response = requests.get(url, headers=headers, params=payload)
    if response.status_code == 200:
        data = response.json()
        if data:
            if data[0].get('enabled') == False:
                logger.info(f"Account {payload.get('account_id')} in {payload.get('region')} is disabled. Visit {get_url('aws/aws-account-list')} to enable it.")
                exit(-1)
    elif response.status_code == 401:
        logger.error(f"{response.status_code} Invalid token provided.")
        delete_token_from_file()
        exit(-1)
    elif response.status_code == 404:
        pass
    else:
        logger.error(f"Error: {response.status_code}")
        exit(-1)

    url = get_url('api/billing/subscription-status')

    logger.debug("Validating plan...")
    response = requests.get(url, headers=headers, params=payload)

    if response.status_code == 200:
        data = response.json()
        hasActiveSubscription = data.get('hasActiveSubscription')
        usage = data.get('usage')
        if usage > 1 and not hasActiveSubscription:
            logger.info(f"Free plan used up. Please visit {get_url('organization/billing')} to upgrade your plan.")
            exit(-1)
    elif response.status_code == 401:
        logger.error(f"{response.status_code} Invalid token provided.")
        delete_token_from_file()
        exit(-1)
    else:
        logger.error(f"Error: {response.status_code}")
        exit(-1)
    return True

def add_aws_account(account_id, name, region, role_arn):
    headers = get_headers()
    url = get_url('api/aws/account-by-id-region')

    payload = {
        "account_id": account_id,
        "name": name,
        "region": region,
        "role_arn": role_arn,
    }
    logger.debug("Adding account...")
    id = None
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        data = response.json()
        if data.get('error'):
            logger.error(data.get('error'))
            return None
        logger.info(f"Account {account_id} in {region} added successfully.")
        id = data.get('id')
    elif response.status_code == 409:
        logger.debug(f"Account {account_id} in {region} already exists.")
        id = response.json().get('id')
    elif response.status_code == 401:
        logger.error(f"{response.status_code} Invalid token provided.")
        delete_token_from_file()
        exit(-1)
    else:
        logger.error(f"Error: {response.status_code}")
        return None
    return id

def add_workspace(name, account_id, provider, provider_group_code, region):
    headers = get_headers()
    url = get_url('api/workspace/by-id-region-group')

    payload = {
        "name": name,
        "account_id": account_id,
        "provider_name": provider,
        "provider_group_code": provider_group_code,
        "region": region
    }
    logger.debug("Adding workspace...")
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        data = response.json()
        logger.info(f"Workspace {name} in {region} added successfully.")
        return data.get('id') 
    elif response.status_code == 409:
        logger.debug(f"Workspace {name} already exists.")
        return response.json().get('id')
    elif response.status_code == 401:
        logger.error(f"{response.status_code} Unauthorized - Invalid token provided.")
        delete_token_from_file()
        exit(-1)
    else:
        logger.error(f"Error adding workspace: {response.status_code} {response.text}")
        return None


    
