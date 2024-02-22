import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse
import logging
import time
import http
import json
from pathlib import Path


logger = logging.getLogger('finisterra')

CREDENTIALS_FILE = os.path.expanduser('~/.finisterra/credentials.json')


class AuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to prevent printing access logs to the console.
        pass

    def log_error(self, format, *args):
        pass

    def handle_error(self, request, client_address):
        # Override to prevent printing exceptions to the console.
        pass

    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            # Extract token from the path, for example, /?token=abc123
            url_path = self.path
            query_string = urllib.parse.urlparse(url_path).query
            query_dict = urllib.parse.parse_qs(query_string)
            token = query_dict.get('token', [None])[0]

            # Signal the script to continue with the token
            if token:
                os.environ['FT_API_TOKEN'] = token
                save_token_to_file(token)

            # Serve an HTML page indicating the window can be closed
            self.wfile.write(
                b"<html><body><p>Authentication successful. You can close this window.</p></body></html>")
            self.wfile.flush()

            # Shutdown the HTTP server
            def shutdown_server():
                time.sleep(1)
                httpd.shutdown()

            threading.Thread(target=shutdown_server).start()

        except BrokenPipeError:
            pass


def start_server():
    global httpd
    server_address = ('', 8001)
    httpd = HTTPServer(server_address, AuthHandler)
    httpd.serve_forever()


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


def auth(payload):
    api_token = os.environ.get('FT_API_TOKEN')
    if not api_token:
        # If not defined, read the token from the file
        api_token = read_token_from_file()

    if not api_token:
        # Start local server in a separate thread
        server_thread = threading.Thread(target=start_server)
        server_thread.daemon = True
        server_thread.start()

        api_protocol = os.environ.get('FT_API_PROTOCOL_WEB', 'https')
        api_host = os.environ.get('FT_API_HOST_WEB', 'api.finisterra.io')
        api_port = os.environ.get('FT_API_PORT_WEB', '443')
        api_part = os.environ.get('FT_API_PART_WEB', 'get-cli-token')

        # Create the authentication URL
        auth_url = f"{api_protocol}://{api_host}:{api_port}/{api_part}"

        # Print a message with the URL and instruct the user to click on it
        # Bright cyan color
        print("\033[1;96mPlease authenticate by visiting the following URL:\033[0m")

        print(auth_url)

        # Wait for the server thread to complete (i.e., until authentication is done)
        server_thread.join()

        # Check again for the token
        api_token = os.environ.get('FT_API_TOKEN')
        if not api_token:
            logger.error("Authentication failed or was cancelled.")
            exit()

    api_host = os.environ.get('FT_API_HOST', 'api.finisterra.io')
    api_port = os.environ.get('FT_API_PORT', 443)
    api_path = '/auth/'

    logger.info(f"Authenticating with {api_host}:{api_port}...")

    if api_port == 443:
        conn = http.client.HTTPSConnection(api_host, api_port)
    else:
        conn = http.client.HTTPConnection(api_host, api_port)
    headers = {'Content-Type': 'application/json',
               "Authorization": "Bearer " + api_token}

    payload_json = json.dumps(payload, default=list)
    conn.request('POST', api_path, body=payload_json, headers=headers)
    response = conn.getresponse()
    if response.status == 200:
        return True
    else:
        logger.error(f"Error: {response.status} - {response.reason}")
        exit()
