from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from django.http import JsonResponse

from .forms import BookingForm
from .models import Appointment

from .utils import find_available_specialist, get_available_slots


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
    else:
        available_slots = get_available_slots(booking.employee, booking.date_time.date(), booking.service)
        if booking.date_time not in available_slots:
            return JsonResponse({
                'ok': False,
                'error': 'Ten termin właśnie został zajęty. Wybierz inny.'
            }, status=409)

    booking.save()

    return JsonResponse({'ok': True})


@require_http_methods(['GET', 'POST'])
def cancel_booking(request, token):
    appointment = get_object_or_404(Appointment, cancellation_token=token)

    just_cancelled = False
    if request.method == 'POST':
        just_cancelled = appointment.cancel()

    return render(request, 'bookings/cancel_appointment.html', {
        'appointment': appointment,
        'just_cancelled': just_cancelled,
    })