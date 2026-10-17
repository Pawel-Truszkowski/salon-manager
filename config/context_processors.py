from django.conf import settings


def site(request):
    """Absolute base URL for canonical, Open Graph and JSON-LD (same setting as links in e-mails)."""
    return {'site_url': settings.SITE_URL.rstrip('/')}
