import os
import json
import logging
import traceback
from google.oauth2 import service_account

# Add __all__ to export both functions
__all__ = ['get_google_credentials_direct', 'get_google_credentials']

def get_google_credentials_direct():
    """Create credentials directly from environment variables"""
    try:
        # Get environment variables
        project_id = os.environ.get('GOOGLE_PROJECT_ID')
        client_email = os.environ.get('GOOGLE_CLIENT_EMAIL')
        private_key = os.environ.get('GOOGLE_PRIVATE_KEY')
        
        logging.info(f"Project ID present: {bool(project_id)}")
        logging.info(f"Client email present: {bool(client_email)}")
        logging.info(f"Private key present: {bool(private_key)}")
        
        # Check if all required variables are present
        if not all([project_id, client_email, private_key]):
            logging.error("Missing required Google credentials variables")
            return None
        
        # Fix private key formatting if needed
        if '\\n' in private_key and '\n' not in private_key:
            logging.info("Converting \\n to newlines in private key")
            private_key = private_key.replace('\\n', '\n')
        
        # Verify key format
        if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
            logging.error("Private key does not start with correct header")
            return None
            
        if not private_key.strip().endswith('-----END PRIVATE KEY-----'):
            logging.error("Private key does not end with correct footer")
            
        # Create credentials info dictionary
        credentials_info = {
            "type": "service_account",
            "project_id": project_id,
            "private_key": private_key,
            "client_email": client_email,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email.replace('@', '%40')}"
        }
        
        logging.info("Creating credentials from service account info")
        
        # Create credentials object directly (no file needed)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        logging.info("Successfully created direct credentials")
        return credentials
    
    except Exception as e:
        logging.error(f"Error creating direct credentials: {str(e)}")
        logging.error(traceback.format_exc())
        return None

def get_google_credentials():
    """Get Google credentials from environment variables or file"""
    try:
        # Check if running with environment variables
        if os.environ.get('GOOGLE_PRIVATE_KEY') and os.environ.get('GOOGLE_CLIENT_EMAIL'):
            # Get private key and fix formatting issues
            private_key = os.environ.get('GOOGLE_PRIVATE_KEY')
            
            # Ensure proper newlines in the private key
            if '\\n' in private_key and '\n' not in private_key:
                private_key = private_key.replace('\\n', '\n')
                
            # Create credentials from environment variables
            credentials_dict = {
                "type": "service_account",
                "project_id": os.environ.get('GOOGLE_PROJECT_ID', ''),
                "private_key": private_key,
                "client_email": os.environ.get('GOOGLE_CLIENT_EMAIL'),
                "client_id": os.environ.get('GOOGLE_CLIENT_ID', ''),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ.get('GOOGLE_CLIENT_EMAIL', '').replace('@', '%40')}",
                "universe_domain": "googleapis.com"
            }
            
            # Create temp credentials file for library to use
            try:
                if os.environ.get('VERCEL'):
                    credentials_path = '/tmp/google_credentials_temp.json'
                else:
                    credentials_path = 'google_credentials_temp.json'
                
                with open(credentials_path, 'w') as f:
                    json.dump(credentials_dict, f)
                
                return credentials_path
            except Exception as e:
                logging.error(f"Error creating credentials file: {str(e)}")
                return None
        
        # Check for credentials file
        elif os.path.exists('google_credentials.json'):
            return 'google_credentials.json'
        
        return None
    except Exception as e:
        logging.error(f"Error in get_google_credentials: {str(e)}")
        return None