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

# Serve media/static in development; in production configure cPanel/Apache to serve these
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Production: still serve media (user uploads) via Django if no Apache alias
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)