import json
import re

import pytest
from django.urls import reverse

from apps.services.category_pages import CATEGORY_PAGES, page_categories
from apps.services.models import Equipment, Service, ServiceCategory

URL = '/uslugi/depilacja-laserowa/'


@pytest.fixture
def laser_category(db):
    # Created by the data migration services/0011, like on production
    return ServiceCategory.objects.get(slug='depilacja-laserowa')


@pytest.fixture
def laser_services(laser_category):
    laser, _ = Equipment.objects.get_or_create(name='LightSheer DUET')
    return [
        Service.objects.create(name=name, category=laser_category, price=price, duration=30, required_equipment=laser)
        for name, price in [('Depilacja laserowa – pachy', '120.00'), ('Depilacja laserowa – całe nogi', '320.00')]
    ]


def json_ld_blocks(html):
    return [
        json.loads(block) for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    ]


@pytest.mark.django_db
class TestPageCategories:
    def test_a_category_with_content_and_active_services(self, laser_services, laser_category):
        assert list(page_categories()) == [laser_category]

    def test_no_page_without_active_services(self, laser_services):
        Service.objects.update(is_active=False)

        assert not page_categories().exists()

    def test_no_page_without_written_content(self, service):
        assert service.category.slug not in CATEGORY_PAGES
        assert not page_categories().exists()

    def test_one_category_even_with_many_services(self, laser_services):
        assert page_categories().count() == 1


@pytest.mark.django_db
class TestCategoryDetail:
    def test_renders_title_h1_and_the_price_table(self, client, laser_services):
        html = client.get(URL).content.decode()

        assert '<title>Depilacja laserowa Wrocław — laser LightSheer DUET | Royal Beauty</title>' in html
        assert html.count('<h1') == 1
        assert 'Depilacja laserowa we Wrocławiu</h1>' in html
        assert '<table class="rb-price-table">' in html
        assert '320 zł' in html
        assert '<th scope="row">Całe nogi</th>' in html  # no repeated "Depilacja laserowa – " on a phone
        assert f'href="/?usluga={laser_services[0].pk}#rezerwacja"' in html
        assert f'<link rel="canonical" href="http://testserver{URL}"' in html

    def test_body_has_at_least_500_words(self, client, laser_services):
        html = client.get(URL).content.decode()
        body = html.split('class="rb-category-body">', 1)[1].split('class="rb-category-prices"', 1)[0]

        assert len(re.sub(r'<[^>]+>', ' ', body).split()) >= 500

    def test_json_ld_service_breadcrumbs_and_faq(self, client, laser_services):
        blocks = json_ld_blocks(client.get(URL).content.decode())
        graph = next(b['@graph'] for b in blocks if '@graph' in b)
        service = next(item for item in graph if item['@type'] == 'Service')
        breadcrumbs = next(item for item in graph if item['@type'] == 'BreadcrumbList')
        faq = next(b for b in blocks if b.get('@type') == 'FAQPage')

        assert service['provider'] == {'@id': 'http://testserver/#salon'}
        assert [o['itemOffered']['name'] for o in service['hasOfferCatalog']['itemListElement']] == [
            'Depilacja laserowa – całe nogi',
            'Depilacja laserowa – pachy',
        ]
        assert breadcrumbs['itemListElement'][-1]['item'] == f'http://testserver{URL}'
        assert 'Czy depilacja laserowa boli?' in [q['name'] for q in faq['mainEntity']]

    def test_404_without_active_services(self, client, laser_services):
        Service.objects.update(is_active=False)

        assert client.get(URL).status_code == 404

    def test_404_for_a_category_without_content(self, client, service):
        assert client.get(f'/uslugi/{service.category.slug}/').status_code == 404

    def test_home_price_list_links_to_the_page(self, client, laser_services, service):
        html = client.get(reverse('home')).content.decode()

        assert f'href="{URL}"' in html
        assert html.count('rb-menu-group-more') == 1  # only the category that has a page


@pytest.mark.django_db
class TestCategorySitemap:
    def test_lists_the_page_with_lastmod(self, client, laser_services, service):
        xml = client.get('/sitemap.xml').content.decode()

        assert f'<loc>http://testserver{URL}</loc>' in xml
        assert '/uslugi/zabiegi-kosmetyczne/' not in xml
        assert xml.count('<lastmod>') == 4  # home, two legal pages, the laser page
