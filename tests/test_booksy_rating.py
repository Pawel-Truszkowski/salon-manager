import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.services.models import BooksyRating

URL = reverse('panel:reviews')


def make_rating(rating='4.9', count=90, as_of=datetime.date(2026, 10, 1)):
    return BooksyRating.objects.create(rating=Decimal(rating), count=count, as_of=as_of)


@pytest.mark.django_db
class TestHomeBooksy:
    def test_shows_the_latest_rating_with_its_date(self, client):
        make_rating('4.8', 80, datetime.date(2026, 9, 1))
        make_rating('4.9', 94, datetime.date(2026, 10, 22))

        html = client.get(reverse('home')).content.decode()

        assert '<strong>4,9/5</strong> · 94 opinie na <a href="https://royalbeauty-studiourody.booksy.com/"' in html
        assert '(stan na 22.10.2026)' in html
        assert '80 opinii' not in html

    def test_nothing_about_booksy_without_a_rating(self, client):
        html = client.get(reverse('home')).content.decode()

        assert 'na <a href="https://royalbeauty-studiourody.booksy.com/"' not in html
        assert 'Opinie zbieramy w wizytówce Google' in html  # the links-only fallback

    def test_stays_out_of_the_json_ld(self, client):
        make_rating()

        assert 'aggregateRating' not in client.get(reverse('home')).content.decode()


@pytest.mark.django_db
class TestPanelBooksyRating:
    def test_only_the_owner_gets_in(self, client, employee_user):
        client.force_login(employee_user)

        assert client.get(URL).status_code == 403

    def test_form_starts_from_the_last_numbers(self, client, owner_user):
        make_rating('4.9', 90)
        client.force_login(owner_user)

        form = client.get(URL).context['form']

        assert form.initial['rating'] == Decimal('4.9')
        assert form.initial['count'] == 90

    def test_saving_adds_a_new_snapshot(self, client, owner_user):
        old = make_rating('4.9', 90)
        client.force_login(owner_user)

        response = client.post(URL, {'rating': '4.9', 'count': '94', 'as_of': '2026-10-22'})

        assert response.status_code == 302
        latest = BooksyRating.objects.first()
        assert latest != old
        assert (latest.count, latest.as_of, latest.created_by) == (94, datetime.date(2026, 10, 22), owner_user)
        assert BooksyRating.objects.count() == 2  # the old one stays as history

    def test_the_first_entry_needs_no_history(self, client, owner_user):
        client.force_login(owner_user)

        client.post(URL, {'rating': '4.9', 'count': '94', 'as_of': '2026-10-22'})

        assert BooksyRating.objects.count() == 1

    @pytest.mark.parametrize(
        ('data', 'field'),
        [
            ({'count': '49', 'as_of': '2026-10-22'}, 'count'),  # swapped digits: fewer reviews than last time
            ({'count': '94', 'as_of': '2026-09-01'}, 'as_of'),  # older than the last entry: would never show
            ({'count': '94', 'as_of': '2999-01-01'}, 'as_of'),  # not checked yet
        ],
    )
    def test_likely_typos_are_rejected(self, client, owner_user, data, field):
        make_rating('4.9', 90, datetime.date(2026, 10, 1))
        client.force_login(owner_user)

        response = client.post(URL, {'rating': '4.9', **data})

        assert field in response.context['form'].errors
        assert BooksyRating.objects.count() == 1

    def test_same_day_and_same_count_are_fine(self, client, owner_user):
        make_rating('4.9', 90, datetime.date(2026, 10, 1))
        client.force_login(owner_user)

        client.post(URL, {'rating': '4.8', 'count': '90', 'as_of': '2026-10-01'})

        assert BooksyRating.objects.count() == 2

    @pytest.mark.parametrize('rating', ['0.5', '5.1'])
    def test_rating_must_be_between_1_and_5(self, client, owner_user, rating):
        client.force_login(owner_user)

        response = client.post(URL, {'rating': rating, 'count': '94', 'as_of': '2026-10-22'})

        assert response.status_code == 200
        assert 'rating' in response.context['form'].errors
        assert not BooksyRating.objects.exists()
