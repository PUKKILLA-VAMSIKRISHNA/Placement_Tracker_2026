from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Hello from Vercel!')

def handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/plain'
        },
        'body': 'Hello from Vercel!'
    }
