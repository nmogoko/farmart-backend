from config import Config
from datetime import datetime
from flask import request, g
from functools import wraps
from flask_jwt_extended import decode_token
from requests.auth import HTTPBasicAuth

import base64
import requests

config = Config()

def create_access_token():
    mpesa_auth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    data = (requests.get(mpesa_auth_url, auth = HTTPBasicAuth(config.CONSUMER_KEY, config.CONSUMER_SECRET))).json()
    return data['access_token']


# Custom decorator to run middleware before specific routes
def generate_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = create_access_token()

        if not token:
            return {"error": "Token was not obtained successfully"}, 401
        request.token = token
        
        return f(*args, **kwargs)
    
    return decorated_function


def generate_timestamp():
    # Get the current date and time
    now = datetime.now()
    # Format it as a string
    timestamp = now.strftime("%Y%m%d%H%M%S")
    return timestamp


def generate_password():
    # Concatenate the shortcode, passkey, and timestamp
    data_to_encode = config.MPESA_BUSINESS_SHORTCODE + config.MPESA_PASSKEY + generate_timestamp()
    # Encode the concatenated string in Base64
    encoded_password = base64.b64encode(data_to_encode.encode()).decode('utf-8')
    return encoded_password

# Custom decorator to run middleware before specific routes
def with_user_middleware(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')  # Extract token from headers (e.g., Bearer token)
        
        if token:
            token = token.split()[1]  # Remove 'Bearer' and get the actual token
            decoded_token = decode_token(token)  # Extract or decode the token to get user_id
            g.user_id = decoded_token['sub']['id']  # Store the user_id in g (global context for the request)
        else:
            g.user_id = None
        
        return f(*args, **kwargs)
    
    return decorated_function
