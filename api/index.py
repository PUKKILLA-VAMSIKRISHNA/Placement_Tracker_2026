import os
import sys
from serverless_http import handle_one_request

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app
from app import app as application

# Use serverless-http to handle the request
def handler(event, context):
    return handle_one_request(application, event, context)
