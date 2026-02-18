# passenger_wsgi.py - Use when this file is in domain document root (not in pdf_backend)
# Replace the "It works!" script with this – same file, same folder

import os
import sys

# Log errors to file for debugging (remove after fixing)
LOG_FILE = '/home2/pdfserve/pdf_backend/passenger_error.log'

try:
    # Use the virtualenv Python (has Django installed)
    INTERP = '/home2/pdfserve/virtualenv/pdf_backend/3.12/bin/python'
    if sys.executable != INTERP:
        os.execl(INTERP, INTERP, *sys.argv)

    # Django project location
    APP_ROOT = '/home2/pdfserve/pdf_backend'
    sys.path.insert(0, APP_ROOT)
    os.chdir(APP_ROOT)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdf_server.settings')

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

    from whitenoise import WhiteNoise
    application = WhiteNoise(
        application,
        root=os.path.join(APP_ROOT, 'staticfiles'),
        prefix='/static/'
    )
except Exception as e:
    import traceback
    with open(LOG_FILE, 'a') as f:
        f.write('\n\n--- Error ---\n')
        f.write(str(e) + '\n')
        f.write(traceback.format_exc())
    raise
