import os
import http
import json

def auth(payload):
    api_token = os.environ.get('FT_API_TOKEN')
    if not api_token:
        # Do the redirect here to open an account and get a new token
        print("FT_API_TOKEN environment variable is not defined.")
        exit()
    api_host = os.environ.get('API_HOST', 'api.finisterra.io')
    api_port = os.environ.get('API_PORT', 443)
    api_path = '/auth/'

    if api_port == 443:
        conn = http.client.HTTPSConnection(api_host, api_port)
    else:
        conn = http.client.HTTPConnection(api_host, api_port)
    headers = {'Content-Type': 'application/json', "Authorization": "Bearer " + api_token}

    payload_json = json.dumps(payload, default=list)
    conn.request('POST', api_path, body=payload_json, headers=headers)
    response = conn.getresponse()
    if response.status == 200:
        return True
    else:
        print(f"Error: {response.status} - {response.reason}")
        exit()

