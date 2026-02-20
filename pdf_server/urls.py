# pdf_server/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import app_ads_txt, privacy_policy

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('pdf_app.urls')),
    path('api/', include('books.urls')),
    path('app-ads.txt', app_ads_txt),
    path('privacy_policy', privacy_policy),
]

# Serve media/static in development only.
# Production (cPanel): Apache must serve /media/ directly (see CPANEL_MEDIA_SETUP.md).
# Do NOT serve media via Django in production so PDFs use direct URLs and caching.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)