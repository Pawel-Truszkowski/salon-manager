import io
import json
import urllib.error
from unittest import mock

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.services import google_reviews
from apps.services.google_reviews import get_google_reviews, parse_place, parse_review
from apps.services.templatetags.services_extras import pl_plural, rating


def google_review(name, stars, text, when='tydzień temu'):
    """One review in the exact shape of a real Places API (New) response; made-up people, not real clients."""
    review = {
        'name': f'places/test-place-id/reviews/{name}',
        'relativePublishTimeDescription': when,
        'rating': stars,
        'authorAttribution': {
            'displayName': name,
            'uri': f'https://www.google.com/maps/contrib/{name}/reviews',
            'photoUri': f'https://lh3.googleusercontent.com/a-/{name}=s128',
        },
        'publishTime': '2026-10-13T10:30:57.262843681Z',
        'googleMapsUri': f'https://www.google.com/maps/reviews/{name}',
    }
    if text:
        review['text'] = {'text': text, 'languageCode': 'pl'}
        review['originalText'] = {'text': text, 'languageCode': 'pl'}
    return review


PLACE = {
    'rating': 4.8,
    'userRatingCount': 16,
    'googleMapsUri': 'https://maps.google.com/?cid=123',
    'reviews': [
        google_review('Ola', 5, 'Piękne paznokcie,\npolecam!'),
        google_review('Kasia_92', 5, 'Rzęsy trzymają się trzy tygodnie.', when='rok temu'),
        google_review('Ewa M.', 3, 'Dobrze, ale musiałam poczekać.', when='rok temu'),
        google_review('Basia', 5, '', when='2 lata temu'),  # stars only, no text
        google_review('Natalia', 4, 'Miła atmosfera.', when='2 lata temu'),
    ],
}


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def places_key(settings):
    settings.GOOGLE_PLACES_API_KEY = 'test-key'


def fake_response(data):
    """What urlopen() returns: a context manager with a readable JSON body."""
    return io.BytesIO(json.dumps(data).encode())


class TestParseReview:
    def test_maps_the_fields_the_template_needs(self):
        review = parse_review(PLACE['reviews'][0])

        assert review == {
            'author': 'Ola',
            'author_url': 'https://www.google.com/maps/contrib/Ola/reviews',
            'photo_url': 'https://lh3.googleusercontent.com/a-/Ola=s128',
            'rating': 5,
            'text': 'Piękne paznokcie,\npolecam!',
            'when': 'tydzień temu',
            'url': 'https://www.google.com/maps/reviews/Ola',
        }

    def test_prefers_the_original_text_over_googles_translation(self):
        data = google_review('Anna', 5, 'Super!')
        data['text'] = {'text': 'Great!', 'languageCode': 'en'}

        assert parse_review(data)['text'] == 'Super!'

    def test_a_review_without_text_has_an_empty_text(self):
        assert parse_review(PLACE['reviews'][3])['text'] == ''


class TestParsePlace:
    def test_summary(self):
        place = parse_place(PLACE)

        assert place['rating'] == 4.8
        assert place['count'] == 16
        assert place['maps_url'] == 'https://maps.google.com/?cid=123'

    def test_stars_only_reviews_are_skipped(self):
        authors = [review['author'] for review in parse_place(PLACE)['reviews']]

        assert 'Basia' not in authors

    def test_lower_ratings_stay_and_googles_order_is_kept(self):
        authors = [review['author'] for review in parse_place(PLACE)['reviews']]

        assert authors == ['Ola', 'Kasia_92', 'Ewa M.', 'Natalia']

    def test_a_place_without_reviews_still_has_the_summary(self):
        place = parse_place({'rating': 5, 'userRatingCount': 1})

        assert place['reviews'] == []

    @pytest.mark.parametrize(
        'data',
        [
            {},  # e.g. a field mask without rating
            {'rating': 5, 'userRatingCount': 1, 'reviews': [{'rating': 5}]},  # review without author
            {'rating': 5, 'userRatingCount': 1, 'reviews': 'nope'},
        ],
    )
    def test_an_unexpected_shape_returns_none(self, data):
        assert parse_place(data) is None


class TestFetchPlace:
    def test_sends_the_key_and_field_mask(self, places_key):
        with mock.patch('urllib.request.urlopen', return_value=fake_response(PLACE)) as urlopen:
            assert google_reviews.fetch_place() == PLACE

        request = urlopen.call_args.args[0]
        assert request.full_url == 'https://places.googleapis.com/v1/places/test-place-id?languageCode=pl'
        assert request.get_header('X-goog-api-key') == 'test-key'
        assert request.get_header('X-goog-fieldmask') == 'rating,userRatingCount,googleMapsUri,reviews'
        assert urlopen.call_args.kwargs['timeout'] == google_reviews.TIMEOUT

    @pytest.mark.parametrize(
        'error',
        [
            urllib.error.HTTPError('url', 403, 'IP address restriction', {}, None),
            urllib.error.URLError('no network'),
            TimeoutError(),
        ],
    )
    def test_a_failed_request_returns_none(self, places_key, error):
        with mock.patch('urllib.request.urlopen', side_effect=error):
            assert google_reviews.fetch_place() is None

    def test_a_non_json_body_returns_none(self, places_key):
        with mock.patch('urllib.request.urlopen', return_value=io.BytesIO(b'<html>')):
            assert google_reviews.fetch_place() is None


class TestGetGoogleReviews:
    def test_without_a_key_google_is_never_called(self):
        with mock.patch.object(google_reviews, 'fetch_place') as fetch:
            assert get_google_reviews() is None

        fetch.assert_not_called()

    def test_the_response_is_cached(self, places_key):
        with mock.patch.object(google_reviews, 'fetch_place', return_value=PLACE) as fetch:
            first = get_google_reviews()
            second = get_google_reviews()

        assert first == second
        assert first['count'] == 16
        fetch.assert_called_once()

    def test_a_failure_is_cached_too(self, places_key):
        with mock.patch.object(google_reviews, 'fetch_place', return_value=None) as fetch:
            assert get_google_reviews() is None
            assert get_google_reviews() is None

        fetch.assert_called_once()  # a Google outage doesn't slow down every page view

    def test_an_unusable_response_counts_as_a_failure(self, places_key):
        with mock.patch.object(google_reviews, 'fetch_place', return_value={}) as fetch:
            assert get_google_reviews() is None
            assert get_google_reviews() is None

        fetch.assert_called_once()


@pytest.mark.django_db
class TestHomeReviews:
    def test_shows_the_google_summary_and_reviews(self, client, places_key):
        with mock.patch.object(google_reviews, 'fetch_place', return_value=PLACE):
            html = client.get(reverse('home')).content.decode()

        assert '4,8/5' in html
        assert '16 opinii w Google Maps' in html
        assert 'Piękne paznokcie,<br>polecam!' in html
        # attribution required by Google: author's profile and the review on Google Maps
        assert 'https://www.google.com/maps/contrib/Ola/reviews' in html
        assert 'https://www.google.com/maps/reviews/Ola' in html

    def test_without_google_only_the_links_are_shown(self, client):
        html = client.get(reverse('home')).content.decode()

        assert 'Opinie zbieramy w wizytówce Google' in html
        assert 'rb-review-list' not in html

    def test_ratings_stay_out_of_the_json_ld(self, client, places_key):
        """Google forbids self-serving review markup for a LocalBusiness."""
        with mock.patch.object(google_reviews, 'fetch_place', return_value=PLACE):
            html = client.get(reverse('home')).content.decode()

        assert 'aggregateRating' not in html
        assert '"Review"' not in html


class TestFilters:
    @pytest.mark.parametrize(
        ('count', 'expected'),
        [
            (1, 'opinia'),
            (2, 'opinie'),
            (4, 'opinie'),
            (5, 'opinii'),
            (12, 'opinii'),
            (16, 'opinii'),
            (22, 'opinie'),
            (0, 'opinii'),
        ],
    )
    def test_pl_plural(self, count, expected):
        assert pl_plural(count, 'opinia,opinie,opinii') == expected

    @pytest.mark.parametrize(('value', 'expected'), [(5, '5,0'), (4.9, '4,9'), (4.85, '4,8')])
    def test_rating(self, value, expected):
        assert rating(value) == expected
