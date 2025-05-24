from web.app import app
import os
import tempfile

# This file is needed for Vercel to find our Flask app

def get_temp_dir():
    """Get appropriate temp directory based on environment"""
    if os.environ.get('VERCEL'):
        # On Vercel, use /tmp which is writable in serverless functions
        temp_dir = '/tmp'
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
    else:
        # Locally, use tempfile
        return tempfile.mkdtemp()