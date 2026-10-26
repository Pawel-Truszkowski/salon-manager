"""System checks run by every manage.py command (migrate on container start, check --deploy)."""

from urllib.parse import urlsplit

from django.conf import settings
from django.core import checks


@checks.register(checks.Tags.compatibility)
def check_site_url(app_configs, **kwargs):
    """`SITE_URL` must be an absolute http(s) URL: it builds the cancel link in e-mails, canonical and JSON-LD.

    Without a scheme ("royalbeauty-studiourody.pl", the bug of the 21.10.2026 deploy) the links come out
    relative and the cancel link in client e-mails doesn't work.
    """
    url = urlsplit(settings.SITE_URL)
    if url.scheme in ('http', 'https') and url.netloc:
        return []
    # An Error, not a Warning: it stops `migrate`, so the container doesn't start. Deploys are done by hand
    # and watched, so that shows at once, unlike a warning in the logs while e-mails go out with dead links.
    return [
        checks.Error(
            f'SITE_URL must be an absolute http(s) URL, got {settings.SITE_URL!r}.',
            hint='Set it in the env file with the scheme, e.g. SITE_URL=https://royalbeauty-studiourody.pl',
            id='bookings.E001',
        )
    ]
