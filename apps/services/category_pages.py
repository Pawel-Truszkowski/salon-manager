"""Category landing pages (/uslugi/<slug>/): one per category that has written content.

The body is a template, `templates/services/categories/<slug>.html`; title, description and FAQ live here,
so the FAQ feeds both the visible section and its `FAQPage` JSON-LD (like the home page's `faq.py`).
A category without an entry here has no page: no thin pages with only a price list.
"""

from collections.abc import Callable
from dataclasses import dataclass

from django.db.models import Exists, OuterRef

from apps.services.faq import laser_page_faq
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
}


def page_categories():
    """Categories that get a landing page: written content here and at least one active service."""
    # Exists() instead of filter(services__is_active=True): no JOIN, so one row per category (get_object_or_404
    # needs that) and the sitemap's annotate(Max('services__updated_at')) gets its own, unfiltered JOIN
    active = Service.objects.active().filter(category=OuterRef('pk'))
    return ServiceCategory.objects.filter(Exists(active), slug__in=CATEGORY_PAGES)
