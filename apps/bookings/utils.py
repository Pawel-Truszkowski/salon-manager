from datetime import datetime, timedelta

from django.utils import timezone

from apps.services.models import Employee, EquipmentRental, Schedule, TimeBlock

from .models import Appointment


def is_service_available_on(service, date):
    """Whether the salon can do this service on `date` at all: True unless it needs equipment that isn't there.

    Checked inside `get_available_slots`, so booking with and without a chosen specialist
    (`find_available_specialist`), the API, the panel and `next_available_date` all follow it.
    """
    equipment_id = service.required_equipment_id
    if equipment_id is None:
        return True
    return EquipmentRental.objects.covering(date).filter(equipment_id=equipment_id, equipment__is_active=True).exists()


def get_available_slots(employee, date, service, exclude_appointment=None):
    slot_duration = 15
    if not employee.is_active or not service.is_active:
        return []
    if not is_service_available_on(service, date):
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

    Goes through `get_available_slots`, so it follows exactly the same rules as booking. Per employee and day
    it checks the shortest active service that can be done that day: if that one doesn't fit anywhere, no
    service does. A laser service doesn't count outside the laser days, the next shortest one does.
    Only days with a `Schedule` are checked, so a week without schedules costs one query, not seven.
    """
    today = timezone.localdate()
    employees = {e.pk: e for e in Employee.objects.active().prefetch_related('services')}
    services_by_length = {
        pk: sorted((s for s in e.services.all() if s.is_active), key=lambda s: s.duration)
        for pk, e in employees.items()
    }
    working_days = (
        Schedule.objects.filter(employee__in=employees, date__gte=today, date__lt=today + timedelta(days=days_ahead))
        .values_list('date', 'employee')
        .distinct()
        .order_by('date', 'employee')
    )
    for date, employee_pk in working_days:
        # Services without equipment need no query, so usually this stops at the first one
        service = next((s for s in services_by_length[employee_pk] if is_service_available_on(s, date)), None)
        if service and get_available_slots(employees[employee_pk], date, service):
            return date
    return None
