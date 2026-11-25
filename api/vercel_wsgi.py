import os
import sys
from pathlib import Path

# Add project root to PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.core.handlers.wsgi import WSGIHandler

_wsgi_app = WSGIHandler()

def handler(request):
    """Vercel‑Python function wrapper that forwards the request to the Django WSGI app.
    The `request` object comes from Vercel and provides method, path, query, headers, and body.
    """
    # Build WSGI environ dictionary
    environ = {
        'REQUEST_METHOD': request.method,
        'PATH_INFO': request.path,
        'QUERY_STRING': request.query or '',
        'SERVER_NAME': request.headers.get('host', ''),
        'SERVER_PORT': request.headers.get('x-forwarded-port', '80'),
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.input': request.body,
        'wsgi.errors': sys.stderr,
        'wsgi.version': (1, 0),
        'wsgi.run_once': False,
        'wsgi.url_scheme': 'https' if request.headers.get('x-forwarded-proto') == 'https' else 'http',
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
    }
    # Convert incoming HTTP headers to WSGI format
    for k, v in request.headers.items():
        environ['HTTP_' + k.upper().replace('-', '_')] = v

    response_data = {}

    def start_response(status, response_headers, exc_info=None):
        response_data['status'] = status
        response_data['headers'] = dict(response_headers)

    # Call the Django WSGI app
    result = _wsgi_app(environ, start_response)
    body_bytes = b''.join(result)
    try:
        body = body_bytes.decode('utf-8')
    except Exception:
        body = body_bytes.decode('latin1')

    status_code = int(response_data['status'].split()[0])
    return {
        'statusCode': status_code,
        'headers': response_data['headers'],
        'body': body,
    }
