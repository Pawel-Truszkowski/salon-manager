import json
import re

import pytest
from django.urls import reverse

from apps.services.category_pages import CATEGORY_PAGES
from apps.services.guides import GUIDES, guides_for
from apps.services.models import Service, ServiceCategory


def json_ld_blocks(html):
    return [
        json.loads(block) for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    ]


def article_and_breadcrumbs(html):
    graph = next(b['@graph'] for b in json_ld_blocks(html) if '@graph' in b)
    return (
        next(item for item in graph if item['@type'] == 'BlogPosting'),
        next(item for item in graph if item['@type'] == 'BreadcrumbList'),
    )


@pytest.fixture
def lash_page(db):
    """The lash category with an active service, so /uslugi/rzesy-i-brwi/ exists."""
    category = ServiceCategory.objects.create(name='Rzęsy i brwi', slug='rzesy-i-brwi')
    return Service.objects.create(name='Przedłużanie rzęs 1:1', category=category, price='150.00', duration=105)


class TestGuides:
    @pytest.mark.parametrize('guide', GUIDES.values(), ids=list(GUIDES))
    def test_metadata(self, guide):
        assert guide.category_slug in CATEGORY_PAGES
        assert len(guide.meta_description) <= 160
        assert guide.updated >= guide.published

    def test_guides_for_a_category(self):
        assert [g.slug for g in guides_for('rzesy-i-brwi')] == ['pielegnacja-rzes-po-przedluzaniu']
        assert guides_for('dlonie-i-stopy') == []


@pytest.mark.django_db
class TestGuideDetail:
    @pytest.mark.parametrize('slug', list(GUIDES))
    def test_renders_with_author_and_at_least_500_words(self, client, slug):
        guide = GUIDES[slug]
        html = client.get(f'/poradniki/{slug}/').content.decode()
        body = html.split('class="rb-category-body">', 1)[1].split('class="rb-category-cta"', 1)[0]

        assert f'<title>{guide.title}</title>' in html
        assert html.count('<h1') == 1
        assert 'Paulina Truszkowska</a>, magister kosmetologii' in html
        assert '<meta property="og:type" content="article" />' in html
        assert len(re.sub(r'<[^>]+>', ' ', body).split()) >= 500

    def test_json_ld_article_by_the_founder(self, client):
        article, breadcrumbs = article_and_breadcrumbs(client.get('/poradniki/laser-czy-wosk/').content.decode())
        salon = next(b for b in json_ld_blocks(client.get('/').content.decode()) if b.get('@type') == 'BeautySalon')

        assert article['author']['@id'] == salon['founder']['@id'] == 'http://testserver/#paulina'
        assert article['publisher'] == {'@id': 'http://testserver/#salon'}
        assert article['datePublished'] == '2026-10-27'
        assert [item['name'] for item in breadcrumbs['itemListElement']] == [
            'Royal Beauty',
            'Poradniki',
            'Depilacja laserowa czy woskiem?',
        ]

    def test_links_to_its_category_page_while_it_exists(self, client, lash_page):
        url = '/poradniki/pielegnacja-rzes-po-przedluzaniu/'
        html = client.get(url).content.decode()
        article, _ = article_and_breadcrumbs(html)

        assert 'href="/uslugi/rzesy-i-brwi/">Cennik: rzęsy i brwi</a>' in html
        assert article['about'] == {'@id': 'http://testserver/uslugi/rzesy-i-brwi/#service'}

        Service.objects.update(is_active=False)
        html = client.get(url).content.decode()

        assert 'Cennik: rzęsy i brwi' not in html  # the category page is a 404 now
        assert 'about' not in article_and_breadcrumbs(html)[0]

    def test_date_in_polish_as_on_production(self, client, settings):
        settings.LANGUAGE_CODE = 'pl-pl'  # test.py has en-us

        html = client.get('/poradniki/laser-czy-wosk/').content.decode()

        assert '<time datetime="2026-10-27">27 października 2026</time>' in html

    def test_404_for_an_unknown_guide(self, client):
        assert client.get('/poradniki/nie-ma-takiego/').status_code == 404


@pytest.mark.django_db
class TestGuideLinks:
    def test_list_page_links_every_guide(self, client):
        html = client.get(reverse('guide_list')).content.decode()

        for slug in GUIDES:
            assert f'href="/poradniki/{slug}/"' in html

    def test_category_page_lists_its_guides(self, client, lash_page):
        html = client.get('/uslugi/rzesy-i-brwi/').content.decode()

        assert 'href="/poradniki/pielegnacja-rzes-po-przedluzaniu/"' in html

    def test_footer_links_the_guides(self, client):
        assert 'href="/poradniki/">Poradniki</a>' in client.get('/').content.decode()

    def test_sitemap_lists_the_guides_with_their_dates(self, client):
        xml = client.get('/sitemap.xml').content.decode()

        assert '<loc>http://testserver/poradniki/</loc>' in xml
        for slug, guide in GUIDES.items():
            assert f'<loc>http://testserver/poradniki/{slug}/</loc><lastmod>{guide.updated}</lastmod>' in xml

    def test_llms_txt_lists_category_pages_and_guides(self, client, lash_page):
        text = client.get('/llms.txt').content.decode()

        assert '](http://testserver/uslugi/rzesy-i-brwi/)' in text
        assert '/uslugi/dlonie-i-stopy/' not in text  # no active service, no page
        for slug in GUIDES:
            assert f'](http://testserver/poradniki/{slug}/)' in text
