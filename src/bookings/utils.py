from datetime import datetime, timedelta

from django.utils import timezone
from .models import Appointment
from services.models import Schedule


def get_available_slots(employee, date, service):
    
    slot_duration =  15
    
    # Get the employee's schedule for the given date
    schedule = Schedule.objects.filter(employee=employee, date=date).first()
    if not schedule:
        return []

    # Calculate the available time slots based on the employee's schedule and service duration
    start_datetime = timezone.make_aware(datetime.combine(date, schedule.start_time))
    end_datetime = timezone.make_aware(datetime.combine(date, schedule.end_time))
    service_duration = timedelta(minutes=service.duration)

    slots = []
    current = start_datetime

    while current <= end_datetime - service_duration:
        slots.append(current)
        current += timedelta(minutes=slot_duration)
        
    # Exclude time slots that are already booked
    appointments = Appointment.objects.filter(
        employee=employee,
        date_time__date=date,
        status__in=['pending', 'confirmed']
    )
    
    busy_slots = [
            (appt.date_time, appt.date_time + timedelta(minutes=appt.service.duration)) for appt in appointments
        ]

    available_slots = []
    
    for slot_start in slots:
        slot_end = slot_start +  service_duration
        overlap = any(
            slot_start < busy_end and slot_end > busy_start
            for busy_start, busy_end in busy_slots
        )
        if not overlap:
            available_slots.append(slot_start)
    
    return available_slots


def find_available_specialist(service, date, time_obj):
    candidates = service.employees.all()
    for specialist in candidates:
        slots = get_available_slots(specialist, date, service)
        if time_obj in slots:
            return specialist
    return None
