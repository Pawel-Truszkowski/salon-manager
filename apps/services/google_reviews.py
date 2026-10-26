"""Google reviews of the salon for the home page, read live from Places API (New).

Google's terms don't allow storing Places content (only the place ID), so nothing goes to the database:
the response sits in Django's cache for a few hours, purely so that not every page view calls Google.
Any failure (no key, timeout, 403, odd JSON) returns None and the page shows only the links.
"""

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

PLACE_URL = 'https://places.googleapis.com/v1/places/{place_id}?languageCode=pl'
# Only what the page shows; the field mask also decides the price (reviews = Enterprise + Atmosphere SKU)
FIELD_MASK = 'rating,userRatingCount,googleMapsUri,reviews'
TIMEOUT = 3  # seconds; a slow Google must not hold a gunicorn worker

CACHE_KEY = 'google_reviews'
CACHE_TTL = 6 * 60 * 60  # ~4 calls a day per gunicorn worker, far below the free 1000 a month
FAILURE_TTL = 15 * 60  # after a failure don't retry on every page view (each try may cost TIMEOUT seconds)
_FAILED = 'failed'  # cached instead of None, because cache.get() returns None for a missing key too


def fetch_place():
    """Raw Places API JSON for `settings.GOOGLE_PLACE_ID`, or None when the call fails."""
    request = urllib.request.Request(
        PLACE_URL.format(place_id=settings.GOOGLE_PLACE_ID),
        headers={'X-Goog-Api-Key': settings.GOOGLE_PLACES_API_KEY, 'X-Goog-FieldMask': FIELD_MASK},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        # HTTPError (403 from the IP restriction, 429 from the quota) is a URLError too
        logger.warning('Google Places request failed: %s', error)
        return None


def parse_review(review):
    """One review as the template needs it; KeyError/TypeError if Google changed the shape."""
    author = review['authorAttribution']
    # originalText = what the client wrote; text may be Google's translation
    text = (review.get('originalText') or review.get('text') or {}).get('text', '')
    return {
        'author': author['displayName'],
        'author_url': author.get('uri', ''),
        'photo_url': author.get('photoUri', ''),
        'rating': review['rating'],
        'text': text.strip(),
        'when': review.get('relativePublishTimeDescription', ''),  # "tydzień temu", already in Polish
        'url': review.get('googleMapsUri', ''),  # the terms require a link to the review on Google Maps
    }


def pick_reviews(reviews):
    """Which of the (at most 5) parsed reviews the page shows, in display order."""
    # Stars-only reviews would be empty cards; they still count in the average shown above.
    # No filter on stars and no reordering: Google already picked these, and hiding the lower ones
    # next to Google's own average would only look like cherry-picking.
    return [review for review in reviews if review['text']]


def parse_place(data):
    """{rating, count, maps_url, reviews} from the Places API JSON, or None if it isn't usable."""
    try:
        return {
            'rating': data['rating'],
            'count': data['userRatingCount'],
            'maps_url': data.get('googleMapsUri', ''),
            'reviews': pick_reviews([parse_review(review) for review in data.get('reviews', [])]),
        }
    except (KeyError, TypeError) as error:
        logger.warning('Unexpected Google Places response: %r', error)
        return None


def get_google_reviews():
    """Parsed Google reviews (see `parse_place()`), cached; None = show only the links."""
    if not settings.GOOGLE_PLACES_API_KEY or not settings.GOOGLE_PLACE_ID:
        return None
    cached = cache.get(CACHE_KEY)
    if cached == _FAILED:
        return None
    if cached is not None:
        return cached
    data = fetch_place()
    place = parse_place(data) if data is not None else None
    if place is None:
        cache.set(CACHE_KEY, _FAILED, FAILURE_TTL)
    else:
        cache.set(CACHE_KEY, place, CACHE_TTL)
    return place
