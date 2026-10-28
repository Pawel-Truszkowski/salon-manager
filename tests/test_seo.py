"""Stage 7 SEO quick wins: meta description, llms.txt, sitemap <lastmod>, the price list in JSON-LD."""

import datetime
import re
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.services.models import Service
from apps.services.schema import service_offer
from tests.test_views import home_html, json_ld_blocks


@pytest.mark.django_db
class TestMetaDescription:
    def test_names_the_laser_and_the_hours_within_google_length(self, client):
        description = re.search(r'<meta name="description" content="([^"]*)"', home_html(client)).group(1)
        assert 'depilacja laserowa' in description
        assert 'Codziennie 9–21' in description
        assert len(description) <= 155


@pytest.mark.django_db
class TestLlmsTxt:
    def test_plain_text_with_absolute_links(self, client):
        response = client.get('/llms.txt')
        assert response.status_code == 200
        assert response['Content-Type'].startswith('text/plain')
        body = response.content.decode()
        assert body.startswith('# Royal Beauty Studio Urody')
        assert '(http://testserver/#cennik)' in body
        assert '(http://testserver/regulamin/)' in body

    def test_no_services_that_are_no_longer_offered(self, client):
        assert 'laminacja' not in client.get('/llms.txt').content.decode().lower()


@pytest.mark.django_db
class TestSitemapLastmod:
    def test_home_is_dated_by_the_last_price_list_change(self, client, service):
        Service.objects.filter(pk=service.pk).update(updated_at=datetime.datetime(2026, 11, 3, 12, tzinfo=datetime.UTC))
        xml = client.get('/sitemap.xml').content.decode()
        assert '<loc>http://testserver/</loc><lastmod>2026-11-03</lastmod>' in xml

    def test_legal_pages_are_dated_by_their_effective_date(self, client):
        xml = client.get('/sitemap.xml').content.decode()
        assert '<loc>http://testserver/regulamin/</loc><lastmod>2026-10-21</lastmod>' in xml

    def test_legal_page_shows_the_same_date_in_polish(self, client):
        assert 'Obowiązuje od 21 października 2026 r.' in client.get(reverse('terms')).content.decode()

    def test_editing_a_service_moves_the_date(self, service):
        before = service.updated_at
        service.price = Decimal('90.00')
        service.save()
        assert service.updated_at > before


class TestServiceOffer:
    def make(self, price, price_is_from=False):
        return Service(name='Manicure hybrydowy', price=Decimal(price), price_is_from=price_is_from, duration=60)

    def test_fixed_price(self):
        offer = service_offer(self.make('80.00'))
        assert offer['@type'] == 'Offer'
        assert offer['price'] == '80.00'  # a string: json can't dump Decimal, and a float could print 80.0
        assert offer['priceCurrency'] == 'PLN'
        assert offer['itemOffered'] == {'@type': 'Service', 'name': 'Manicure hybrydowy'}

    def test_from_price_is_a_minimum_not_the_price(self):
        offer = service_offer(self.make('170.00', price_is_from=True))
        assert 'price' not in offer  # "od 170 zł" isn't the price of the service
        assert offer['priceSpecification'] == {
            '@type': 'PriceSpecification',
            'minPrice': '170.00',
            'priceCurrency': 'PLN',
        }

    def test_free_consultation(self):
        assert service_offer(self.make('0.00'))['price'] == '0.00'


@pytest.mark.django_db
class TestOfferCatalog:
    def test_home_has_one_catalog_per_category_merged_into_the_salon(self, client, service, service_short):
        blocks = json_ld_blocks(home_html(client))
        catalog = next(b for b in blocks if 'hasOfferCatalog' in b)
        salon = next(b for b in blocks if b.get('name') == 'Royal Beauty Studio Urody')
        assert catalog['@id'] == salon['@id'] == 'http://testserver/#salon'
        [category] = catalog['hasOfferCatalog']['itemListElement']
        assert category['name'] == 'Zabiegi kosmetyczne'
        assert [o['itemOffered']['name'] for o in category['itemListElement']] == ['Konsultacja', 'Manicure']

    def test_inactive_services_are_left_out(self, client, service, service_short):
        Service.objects.filter(pk=service_short.pk).update(is_active=False)
        catalog = next(b for b in json_ld_blocks(home_html(client)) if 'hasOfferCatalog' in b)
        [category] = catalog['hasOfferCatalog']['itemListElement']
        assert len(category['itemListElement']) == 1

    def test_no_self_serving_rating(self, client, service):
        assert 'aggregateRating' not in home_html(client)  # Google forbids it for LocalBusiness
