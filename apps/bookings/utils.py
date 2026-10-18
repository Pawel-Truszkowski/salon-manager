from datetime import datetime, timedelta

from django.utils import timezone

from apps.services.models import Employee, Schedule, TimeBlock

from .models import Appointment


def get_available_slots(employee, date, service, exclude_appointment=None):
    slot_duration = 15
    if not employee.is_active or not service.is_active:
        return []

    # An employee can have multiple schedule blocks on the same date (e.g. split shifts)
    schedules = Schedule.objects.filter(employee=employee, date=date).order_by('start_time')
    if not schedules:
        return []

    service_duration = timedelta(minutes=service.duration)
    now = timezone.now()

    slots = []
    for schedule in schedules:
        start_datetime = timezone.make_aware(datetime.combine(date, schedule.start_time))
        end_datetime = timezone.make_aware(datetime.combine(date, schedule.end_time))

        current = start_datetime
        while current <= end_datetime - service_duration:
            if current >= now:
                slots.append(current)
            current += timedelta(minutes=slot_duration)

    # Exclude time slots that are already booked
    appointments = Appointment.objects.filter(
        employee=employee, date_time__date=date, status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
    ).select_related('service')
    # When rescheduling, the appointment being moved must not block its own new slot
    if exclude_appointment is not None:
        appointments = appointments.exclude(pk=exclude_appointment.pk)

    busy_slots = [(appt.date_time, appt.date_time + timedelta(minutes=appt.service.duration)) for appt in appointments]

    # Exclude time slots reserved by the employee/owner (breaks, days off, etc.)
    time_blocks = TimeBlock.objects.filter(employee=employee, date=date)
    busy_slots += [
        (
            timezone.make_aware(datetime.combine(date, block.start_time)),
            timezone.make_aware(datetime.combine(date, block.end_time)),
        )
        for block in time_blocks
    ]

    available_slots = []

    for slot_start in slots:
        slot_end = slot_start + service_duration
        overlap = any(slot_start < busy_end and slot_end > busy_start for busy_start, busy_end in busy_slots)
        if not overlap:
            available_slots.append(slot_start)

    return available_slots


def find_available_specialist(service, date_time_obj):
    candidates = service.employees.active()
    if not timezone.is_aware(date_time_obj):
        date_time_obj = timezone.make_aware(date_time_obj)
    date = date_time_obj.date()
    for specialist in candidates:
        slots = get_available_slots(specialist, date, service)
        if date_time_obj in slots:
            return specialist
    return None


def next_available_date(days_ahead=30):
    """The first day from today on which any active employee has a free slot, or None.

    Goes through `get_available_slots`, so it follows exactly the same rules as booking. Per employee it
    checks their shortest active service: if that one doesn't fit anywhere on a day, no service does.
    Only days with a `Schedule` are checked, so a week without schedules costs one query, not seven.
    """
    today = timezone.localdate()
    employees = {e.pk: e for e in Employee.objects.active().prefetch_related('services')}
    shortest_service = {
        pk: min((s for s in e.services.all() if s.is_active), key=lambda s: s.duration, default=None)
        for pk, e in employees.items()
    }
    working_days = (
        Schedule.objects.filter(employee__in=employees, date__gte=today, date__lt=today + timedelta(days=days_ahead))
        .values_list('date', 'employee')
        .distinct()
        .order_by('date', 'employee')
    )
    for date, employee_pk in working_days:
        service = shortest_service[employee_pk]
        if service and get_available_slots(employees[employee_pk], date, service):
            return date
    return None
