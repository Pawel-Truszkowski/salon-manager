from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from .models import Appointment
from .forms import BookingForm

from .utils import find_available_specialist


@require_POST
def submit_booking(request):
    form = BookingForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    booking = form.save(commit=False)

    if not booking.employee:
        specialist = find_available_specialist(booking.service, booking.date_time)
        if specialist is None:
            return JsonResponse({
                'ok': False,
                'error': 'Brak dostępnych specjalistek w tym terminie. Wybierz inny termin.'
            }, status=400)
            
        booking.employee = specialist

    collision = Appointment.objects.filter(
        employee=booking.employee,
        date_time=booking.date_time,
        status__in=['pending', 'confirmed'],
    ).exists()

    if collision:
        return JsonResponse({
            'ok': False,
            'error': 'Ten termin właśnie został zajęty. Wybierz inny.'
        }, status=409)

    booking.save()
    
    return JsonResponse({'ok': True})