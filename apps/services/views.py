from itertools import groupby

from django.conf import settings
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from apps.bookings.forms import BookingForm
from apps.bookings.utils import next_available_date
from apps.services.category_pages import CATEGORY_PAGES, page_categories
from apps.services.faq import build_faq, faq_jsonld
from apps.services.google_reviews import get_google_reviews
from apps.services.guides import GUIDES, guides_for
from apps.services.models import BooksyRating, Employee, EquipmentRental, Service
from apps.services.schema import category_page_jsonld, guide_jsonld, offer_catalog_jsonld


def next_rentals():
    """{equipment_id: its next rental (or the current one)} for active equipment, in one query."""
    rentals = {}
    for rental in EquipmentRental.objects.upcoming().filter(equipment__is_active=True):
        rentals.setdefault(rental.equipment_id, rental)  # upcoming() is soonest first
    return rentals


def build_price_list(services, rentals=None):
    """Group services by category for the price list: [{category, services, min_price, max_price, ...}, ...].

    `services` must be ordered by category first. Free services (price 0, e.g. a consultation) don't count
    towards the price range. A category whose services need equipment (the laser) also gets `equipment` and
    `next_rental` (None = no upcoming days), taken from `rentals` (see `next_rentals()`).
    """
    rentals = rentals or {}
    price_list = []
    for category, items in groupby(services, key=lambda s: s.category):
        items = list(items)
        paid = [s.price for s in items if s.price > 0]
        equipment = next((s.required_equipment for s in items if s.required_equipment_id), None)
        price_list.append(
            {
                'category': category,
                'services': items,
                'min_price': min(paid, default=None),
                'max_price': max(paid, default=None),
                'equipment': equipment,
                'next_rental': rentals.get(equipment.pk) if equipment else None,
            }
        )
    return price_list


def with_specialties(employees):
    """Attach `specialties`: names of the categories an employee works in, in price-list order."""
    for employee in employees:
        categories = {s.category for s in employee.services.all()}
        employee.specialties = [c.name for c in sorted(categories, key=lambda c: (c.order, c.name))]
    return employees


def category_page_urls():
    """{category_id: URL of its landing page} for the categories that have one (links from the home price list)."""
    return {category.pk: category.get_absolute_url() for category in page_categories()}


def home(request):
    services = list(
        Service.objects.active()
        .select_related('category', 'required_equipment')
        .order_by('category__order', 'category__name', 'name')
    )
    employees = Employee.objects.active().prefetch_related(
        Prefetch('services', queryset=Service.objects.active().select_related('category'))
    )
    form = BookingForm()
    rentals = next_rentals()
    faq = build_faq(services, rentals)
    price_list = build_price_list(services, rentals)
    page_urls = category_page_urls()
    for group in price_list:
        group['page_url'] = page_urls.get(group['category'].pk)
    return render(
        request,
        'home.html',
        {
            'form': form,
            # One active employee: owner profile, no specialist picker. Two or more: team list and picker.
            'employees': with_specialties(list(employees)),
            'services': services,
            'price_list': price_list,
            'offer_catalog_jsonld': offer_catalog_jsonld(price_list, settings.SITE_URL.rstrip('/')),
            'next_date': next_available_date(),
            'faq': faq,
            'faq_jsonld': faq_jsonld(faq),
            'google_reviews': get_google_reviews(),
            'booksy_rating': BooksyRating.objects.first(),
        },
    )


def category_detail(request, slug):
    """/uslugi/<slug>/: a category's landing page (content in `category_pages.py` + its template)."""
    category = get_object_or_404(page_categories(), slug=slug)
    page = CATEGORY_PAGES[slug]
    services = list(
        Service.objects.active()
        .filter(category=category)
        .select_related('category', 'required_equipment')
        .order_by('name')
    )
    rentals = next_rentals()
    [group] = build_price_list(services, rentals)
    faq = page.faq(services, rentals)
    site_url = settings.SITE_URL.rstrip('/')
    return render(
        request,
        'services/category_detail.html',
        {
            'category': category,
            'page': page,
            'group': group,
            'content_template': f'services/categories/{slug}.html',
            'faq': faq,
            'faq_jsonld': faq_jsonld(faq),
            'guides': guides_for(slug),
            'page_jsonld': category_page_jsonld(
                category, services, site_url, f'{site_url}{category.get_absolute_url()}'
            ),
        },
    )


def guide_list(request):
    """/poradniki/: all guides, newest first."""
    guides = sorted(GUIDES.values(), key=lambda g: g.published, reverse=True)
    return render(request, 'guides/list.html', {'guides': guides})


def guide_detail(request, slug):
    """/poradniki/<slug>/: one guide (metadata in `guides.py`, text in `guides/<slug>.html`)."""
    guide = GUIDES.get(slug)
    if guide is None:
        raise Http404
    # The link to the category page only while that page exists (it needs an active service)
    category = page_categories().filter(slug=guide.category_slug).first()
    site_url = settings.SITE_URL.rstrip('/')
    category_url = f'{site_url}{category.get_absolute_url()}' if category else None
    return render(
        request,
        'guides/detail.html',
        {
            'guide': guide,
            'category': category,
            'content_template': f'guides/{slug}.html',
            'page_jsonld': guide_jsonld(
                guide, site_url, f'{site_url}{reverse("guide_detail", args=[slug])}', category_url
            ),
        },
    )


def llms_txt(request):
    """/llms.txt (llmstxt.org): a map of the site for AI answer engines, with the pages that exist right now."""
    return render(
        request,
        'llms.txt',
        {
            'category_pages': [
                (category, CATEGORY_PAGES[category.slug]) for category in page_categories().order_by('order', 'name')
            ],
            'guides': GUIDES.values(),
        },
        content_type='text/plain; charset=utf-8',
    )
