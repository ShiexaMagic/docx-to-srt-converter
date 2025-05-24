import os
import sys

# Add the src directory to the path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'src'))

# Import Flask app
from web.app import app

# Explicitly set this environment variable to indicate we're on Vercel
os.environ['VERCEL'] = '1'

# This allows Vercel to import our Flask app