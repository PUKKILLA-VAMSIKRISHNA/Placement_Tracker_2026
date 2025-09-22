from app import app
from flask import Flask

# This is required for Vercel to recognize the WSGI application
app = app

# Vercel requires a handler function
def handler(request, context):
    # This is a simple WSGI handler that Vercel will use
    from io import BytesIO
    from urllib.parse import parse_qs, urlparse
    import base64
    import json

    # Parse the request
    body = request.get('body', '')
    method = request.get('httpMethod', 'GET')
    path = request.get('path', '/')
    headers = request.get('headers', {})
    query = request.get('queryStringParameters', {})
    
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
        'wsgi.errors': None,
        'wsgi.version': (1, 0),
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
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
    status_code = []
    
    def start_response(status, headers, exc_info=None):
        status_code.append(int(status.split()[0]))
        response_headers.extend(headers)
        return None
    
    # Call the app
    response_body = []
    for chunk in app(environ, start_response):
        response_body.append(chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk)
    
    # Build the response
    response = {
        'statusCode': status_code[0] if status_code else 500,
        'headers': dict(response_headers),
        'body': ''.join(response_body)
    }
    
    return response

# For local development
if __name__ == "__main__":
    app.run(debug=True)
