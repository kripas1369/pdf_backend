"""Static pages: app-ads.txt (AdMob verification), privacy policy."""

from django.http import HttpResponse
from django.shortcuts import render


def app_ads_txt(request):
    """
    Serve app-ads.txt for AdMob/Google verification (Bachelor Question Bank).
    Must be at root of developer website: https://your-domain.com/app-ads.txt
    Domain MUST match exactly what's in Google Play Console → App → Store presence → App details → Developer website.
    """
    # IAB format: domain,publisher_id,relationship,certification_authority_id (no spaces per spec)
    content = "google.com,pub-9127715515165521,DIRECT,f08c47fec0942fa0\n"
    return HttpResponse(
        content,
        content_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=3600",  # Allow AdMob crawler to cache
        },
    )


def privacy_policy(request):
    """Serve privacy policy page (required for Play Store)."""
    return render(request, "privacy_policy.html")
