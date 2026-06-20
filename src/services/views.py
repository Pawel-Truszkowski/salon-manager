from django.shortcuts import render

from services.models import Employee, Service
from bookings.forms import BookingForm


def home(request):
    services = Service.objects.select_related('category').all()
    employees = Employee.objects.prefetch_related('services').all()
    form = BookingForm()
    return render(request, 'home.html', {
        'form': form,
        'employees': employees,
        'services': services,
    })