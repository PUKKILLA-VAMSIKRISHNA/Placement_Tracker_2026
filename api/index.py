from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import sys

# Add the parent directory to the path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app
from app import app as application

def handler(event, context):
    # This is a simple WSGI handler for Vercel
    from io import BytesIO
    from urllib.parse import parse_qs
    import base64

    # Parse the event
    body = event.get('body', '')
    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    headers = event.get('headers', {})
    query = event.get('queryStringParameters', {})
    
    # Convert the request to WSGI environ
    environ = {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': '&'.join([f"{k}={v}" for k, v in query.items()]) if query else '',
        'SERVER_NAME': headers.get('host', ''),
        'SERVER_PORT': headers.get('x-forwarded-port', '80'),
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.url_scheme': headers.get('x-forwarded-proto', 'http'),
        'wsgi.input': BytesIO(body.encode('utf-8') if isinstance(body, str) else body or b''),
        'wsgi.errors': sys.stderr,
        'wsgi.version': (1, 0),
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'wsgi.file_wrapper': None,
    }
    
    # Add headers to environ
    for key, value in headers.items():
        key = 'HTTP_' + key.upper().replace('-', '_')
        environ[key] = value
    
    # Handle cookies
    if 'cookie' in headers:
        environ['HTTP_COOKIE'] = headers['cookie']
    
    # Start response
    response_headers = []
    status_code = [200]
    
    def start_response(status, response_headers_list, exc_info=None):
        status_code[0] = int(status.split()[0])
        response_headers.extend(response_headers_list)
        return None
    
    # Call the app
    response_body = []
    try:
        for chunk in application(environ, start_response):
            response_body.append(chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk)
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/plain'},
            'body': f'Server Error: {str(e)}'
        }
    
    # Build the response
    return {
        'statusCode': status_code[0],
        'headers': dict(response_headers),
        'body': ''.join(response_body)
    }
