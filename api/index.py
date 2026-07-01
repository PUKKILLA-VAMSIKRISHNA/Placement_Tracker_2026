import sys
import os

# Add the parent directory to the Python path so we can import from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# This is the entry point for Vercel
def handler(request):
    return app(request.environ, lambda status, headers: None)

# For Vercel's WSGI compatibility
app = app
