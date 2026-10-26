from itertools import groupby

from django.conf import settings
from django.db.models import Prefetch
from django.shortcuts import render

from apps.bookings.forms import BookingForm
from apps.bookings.utils import next_available_date
from apps.services.faq import build_faq, faq_jsonld
from apps.services.google_reviews import get_google_reviews
from apps.services.models import BooksyRating, Employee, EquipmentRental, Service
from apps.services.schema import offer_catalog_jsonld


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
