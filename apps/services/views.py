from itertools import groupby

from django.db.models import Prefetch
from django.shortcuts import render

from apps.bookings.forms import BookingForm
from apps.bookings.utils import next_available_date
from apps.services.faq import build_faq, faq_jsonld
from apps.services.models import Employee, Service


def build_price_list(services):
    """Group services by category for the price list: [{category, services, min_price, max_price}, ...].

    `services` must be ordered by category first. Free services (price 0, e.g. a consultation) don't count
    towards the price range.
    """
    price_list = []
    for category, items in groupby(services, key=lambda s: s.category):
        items = list(items)
        paid = [s.price for s in items if s.price > 0]
        price_list.append(
            {
                'category': category,
                'services': items,
                'min_price': min(paid, default=None),
                'max_price': max(paid, default=None),
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
        Service.objects.active().select_related('category').order_by('category__order', 'category__name', 'name')
    )
    employees = Employee.objects.active().prefetch_related(
        Prefetch('services', queryset=Service.objects.active().select_related('category'))
    )
    form = BookingForm()
    faq = build_faq(services)
    return render(
        request,
        'home.html',
        {
            'form': form,
            # One active employee: owner profile, no specialist picker. Two or more: team list and picker.
            'employees': with_specialties(list(employees)),
            'services': services,
            'price_list': build_price_list(services),
            'next_date': next_available_date(),
            'faq': faq,
            'faq_jsonld': faq_jsonld(faq),
        },
    )
