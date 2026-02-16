# passenger_wsgi.py
import os
import sys

# Add project to Python path
sys.path.insert(0, '/home/pdfserve/pdf_backend')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdf_server.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# WhiteNoise serves /static/ from staticfiles/
from whitenoise import WhiteNoise
application = WhiteNoise(
    application,
    root='/home/pdfserve/pdf_backend/staticfiles',
    prefix='/static/'
)