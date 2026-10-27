import json
import re
from pathlib import Path

import pytest
from django.urls import reverse

from apps.services.category_pages import CATEGORY_PAGES, page_categories
from apps.services.models import Equipment, Service, ServiceCategory

URL = '/uslugi/depilacja-laserowa/'
CATALOG = json.loads(
    (Path(__file__).parents[1] / 'apps/services/migrations/0013_catalog.json').read_text(encoding='utf-8')
)


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


@pytest.fixture
def catalog(db):
    """The real price list (0013_catalog.json), which a fresh test database doesn't load."""
    laser, _ = Equipment.objects.get_or_create(name='LightSheer DUET')
    categories = {
        c['slug']: ServiceCategory.objects.get_or_create(slug=c['slug'], defaults={'name': c['name']})[0]
        for c in CATALOG['categories']
    }
    return [
        Service.objects.create(
            name=item['name'],
            category=categories[item['category']],
            price=item['price'],
            duration=item['duration'],
            required_equipment=laser if 'equipment' in item else None,
        )
        for item in CATALOG['services']
    ]


@pytest.fixture
def no_page_service(db):
    """An active service in a category without written content."""
    category = ServiceCategory.objects.create(name='Masaże', slug='masaze')
    return Service.objects.create(name='Masaż relaksacyjny', category=category, price='150.00', duration=60)


def body_words(html):
    body = html.split('class="rb-category-body">', 1)[1].split('class="rb-category-prices"', 1)[0]
    return len(re.sub(r'<[^>]+>', ' ', body).split())


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

    def test_no_page_without_written_content(self, no_page_service):
        assert no_page_service.category.slug not in CATEGORY_PAGES
        assert not page_categories().exists()

    def test_every_catalog_category_has_a_page(self, catalog):
        assert {c.slug for c in page_categories()} == {c['slug'] for c in CATALOG['categories']}

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
        assert body_words(client.get(URL).content.decode()) >= 500

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

    def test_404_for_a_category_without_content(self, client, no_page_service):
        assert client.get(f'/uslugi/{no_page_service.category.slug}/').status_code == 404

    def test_home_price_list_links_to_the_page(self, client, laser_services, no_page_service):
        html = client.get(reverse('home')).content.decode()

        assert f'href="{URL}"' in html
        assert html.count('rb-menu-group-more') == 1  # only the category that has a page


@pytest.mark.django_db
class TestCategorySitemap:
    def test_lists_the_page_with_lastmod(self, client, laser_services, no_page_service):
        xml = client.get('/sitemap.xml').content.decode()

        assert re.search(rf'<loc>http://testserver{URL}</loc><lastmod>\d{{4}}-\d{{2}}-\d{{2}}</lastmod>', xml)
        assert '/uslugi/masaze/' not in xml


@pytest.mark.django_db
@pytest.mark.parametrize('slug', list(CATEGORY_PAGES))
class TestEveryCategoryPage:
    """All pages with the real price list: content length, metadata and a FAQ for each."""

    def test_body_title_and_metadata(self, client, catalog, slug):
        page = CATEGORY_PAGES[slug]
        html = client.get(f'/uslugi/{slug}/').content.decode()

        assert body_words(html) >= 500
        assert f'<title>{page.title}</title>' in html
        assert f'{page.h1}</h1>' in html
        assert len(page.meta_description) <= 160
        assert 'Wrocław' in page.title

    def test_faq_from_the_real_price_list(self, client, catalog, slug):
        """3+ questions: a renamed service would silently drop the question that matches it by name."""
        faq = next(
            b for b in json_ld_blocks(client.get(f'/uslugi/{slug}/').content.decode()) if b.get('@type') == 'FAQPage'
        )

        assert len(faq['mainEntity']) >= 4
        for question in faq['mainEntity']:
            assert 25 <= len(question['acceptedAnswer']['text'].split()) <= 60

    def test_linked_from_the_home_price_list(self, client, catalog, slug):
        assert f'href="/uslugi/{slug}/"' in client.get(reverse('home')).content.decode()


@pytest.mark.django_db
def test_no_question_is_on_two_pages(client, catalog):
    """Google: a question marked up as FAQPage on one page only."""
    pages = [reverse('home'), *(f'/uslugi/{slug}/' for slug in CATEGORY_PAGES)]
    questions = [
        q['name']
        for url in pages
        for block in json_ld_blocks(client.get(url).content.decode())
        if block.get('@type') == 'FAQPage'
        for q in block['mainEntity']
    ]

    assert len(questions) == len(set(questions))
