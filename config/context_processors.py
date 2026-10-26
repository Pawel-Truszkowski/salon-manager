import datetime

from django.conf import settings

# Google Business Profile: the place page (reviews, map; `cid` is the profile's stable id) and the "write a review" form
GOOGLE_MAPS_URL = 'https://maps.google.com/?cid=16009745620444220515'
GOOGLE_REVIEW_URL = 'https://g.page/r/CWOM8YrRCi7eEBM/review'
BOOKSY_URL = 'https://royalbeauty-studiourody.booksy.com/'

# Privacy policy and booking terms are in force from this day: shown on both pages and used as their sitemap <lastmod>
LEGAL_EFFECTIVE_DATE = datetime.date(2026, 10, 21)


def site(request):
    """Absolute base URL for canonical, Open Graph and JSON-LD (same setting as links in e-mails), Google and Booksy links."""
    return {
        'site_url': settings.SITE_URL.rstrip('/'),
        'google_maps_url': GOOGLE_MAPS_URL,
        'google_review_url': GOOGLE_REVIEW_URL,
        'booksy_url': BOOKSY_URL,
        'legal_effective_date': LEGAL_EFFECTIVE_DATE,
    }
