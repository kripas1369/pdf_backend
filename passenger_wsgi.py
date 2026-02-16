# cPanel / Passenger WSGI entry point.
# Place this file in the project root (same folder as manage.py).
# In cPanel Setup Python App, set startup file to: passenger_wsgi.py

import os
import sys

# Add project root to path (required on many cPanel hosts)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdf_server.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
