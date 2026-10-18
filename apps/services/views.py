from itertools import groupby

from django.shortcuts import render

from apps.bookings.forms import BookingForm
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


def home(request):
    services = Service.objects.active().select_related('category').order_by('category__order', 'category__name', 'name')
    employees = Employee.objects.active().prefetch_related('services')
    form = BookingForm()
    return render(
        request,
        'home.html',
        {
            'form': form,
            'employees': employees,
            'services': services,
            'price_list': build_price_list(services),
        },
    )
