"""Category landing pages (/uslugi/<slug>/): one per category that has written content.

The body is a template, `templates/services/categories/<slug>.html`; title, description and FAQ live here,
so the FAQ feeds both the visible section and its `FAQPage` JSON-LD (like the home page's `faq.py`).
A category without an entry here has no page: no thin pages with only a price list.
"""

from collections.abc import Callable
from dataclasses import dataclass

from django.db.models import Exists, OuterRef

from apps.services.faq import face_page_faq, laser_page_faq, lash_brow_page_faq, nails_page_faq, wax_page_faq
from apps.services.models import Service, ServiceCategory


@dataclass(frozen=True)
class CategoryPage:
    title: str  # <title>, with the city: the URL has no keyword, the title does the work
    meta_description: str  # ≤155 characters
    h1: str
    faq: Callable  # (services, rentals) -> [{'question', 'answer'}, ...], like `build_faq`
    price_column: str = 'Zabieg'  # header of the price table's first column


CATEGORY_PAGES = {
    'depilacja-laserowa': CategoryPage(
        title='Depilacja laserowa Wrocław — laser LightSheer DUET | Royal Beauty',
        meta_description=(
            'Depilacja laserowa we Wrocławiu laserem diodowym LightSheer DUET. Ceny partii ciała, terminy '
            'z laserem, przygotowanie i przeciwwskazania. Zarezerwuj online.'
        ),
        h1='Depilacja laserowa we Wrocławiu',
        faq=laser_page_faq,
        price_column='Partia ciała',
    ),
    'rzesy-i-brwi': CategoryPage(
        title='Przedłużanie rzęs i henna brwi Wrocław — Fabryczna | Royal Beauty',
        meta_description=(
            'Przedłużanie rzęs 1:1 i objętościowe, uzupełnianie, henna i regulacja brwi na Fabrycznej '
            'we Wrocławiu. Ceny, metody i pielęgnacja. Zarezerwuj online.'
        ),
        h1='Przedłużanie rzęs i stylizacja brwi we Wrocławiu',
        faq=lash_brow_page_faq,
    ),
    'dlonie-i-stopy': CategoryPage(
        title='Manicure i pedicure hybrydowy Wrocław — Fabryczna | Royal Beauty',
        meta_description=(
            'Manicure hybrydowy, klasyczny i męski, paznokcie żelowe oraz pedicure z kwasami na Fabrycznej '
            'we Wrocławiu. Ceny i czas zabiegów. Zarezerwuj online.'
        ),
        h1='Manicure i pedicure we Wrocławiu',
        faq=nails_page_faq,
    ),
    'zabiegi-kosmetyczne': CategoryPage(
        title='Zabiegi na twarz Wrocław — mezoterapia, oczyszczanie | Royal Beauty',
        meta_description=(
            'Mezoterapia mikroigłowa, oczyszczanie wodorowe i manualne, mikrodermabrazja i peeling kawitacyjny '
            'na Fabrycznej we Wrocławiu. Bezpłatna konsultacja.'
        ),
        h1='Zabiegi kosmetyczne na twarz we Wrocławiu',
        faq=face_page_faq,
    ),
    'depilacja-woskiem': CategoryPage(
        title='Depilacja woskiem Wrocław — Fabryczna | Royal Beauty',
        meta_description=(
            'Depilacja woskiem nóg, pach, rąk, pleców, torsu i twarzy na Fabrycznej we Wrocławiu. Ceny partii '
            'ciała, przygotowanie i pielęgnacja. Zarezerwuj online.'
        ),
        h1='Depilacja woskiem we Wrocławiu',
        faq=wax_page_faq,
        price_column='Partia ciała',
    ),
}


def page_categories():
    """Categories that get a landing page: written content here and at least one active service."""
    # Exists() instead of filter(services__is_active=True): no JOIN, so one row per category (get_object_or_404
    # needs that) and the sitemap's annotate(Max('services__updated_at')) gets its own, unfiltered JOIN
    active = Service.objects.active().filter(category=OuterRef('pk'))
    return ServiceCategory.objects.filter(Exists(active), slug__in=CATEGORY_PAGES)
