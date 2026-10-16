from django.shortcuts import render

from apps.bookings.forms import BookingForm
from apps.services.models import Employee, Service


def home(request):
    services = Service.objects.active().select_related('category')
    employees = Employee.objects.active().prefetch_related('services')
    form = BookingForm()
    return render(
        request,
        'home.html',
        {
            'form': form,
            'employees': employees,
            'services': services,
        },
    )
