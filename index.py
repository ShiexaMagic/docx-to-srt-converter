import os
import sys

# Add the project directory to the path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'src'))

# Set Vercel environment flag
os.environ['VERCEL'] = '1'

# Import Flask app
from web.app import app