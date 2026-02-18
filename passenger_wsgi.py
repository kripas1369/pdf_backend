# passenger_wsgi.py
import os
import sys

# Application root (same folder as this file) – works on any cPanel path
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdf_server.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# WhiteNoise serves /static/ from staticfiles/
from whitenoise import WhiteNoise
application = WhiteNoise(
    application,
    root=os.path.join(APP_ROOT, 'staticfiles'),
    prefix='/static/'
)