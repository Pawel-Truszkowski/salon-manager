import datetime
import itertools

from django.utils import timezone

from apps.bookings.models import Appointment
from apps.bookings.utils import find_available_specialist, get_available_slots, next_available_date
from apps.services.models import Schedule
from tests.conftest import make_appointment, make_time_block


class TestGetAvailableSlots:
    def test_returns_slots_when_schedule_exists(self, employee, service, schedule, tomorrow):
        slots = get_available_slots(employee, tomorrow, service)
        assert len(slots) > 0

    def test_returns_empty_when_no_schedule(self, employee, service):
        no_schedule_date = datetime.date(2030, 1, 1)
        slots = get_available_slots(employee, no_schedule_date, service)
        assert slots == []

    def test_first_slot_equals_schedule_start(self, employee, service, schedule, tomorrow):
        slots = get_available_slots(employee, tomorrow, service)
        expected_start = timezone.make_aware(datetime.datetime.combine(tomorrow, schedule.start_time))
        assert slots[0] == expected_start

    def test_last_slot_does_not_exceed_end(self, employee, service, schedule, tomorrow):
        slots = get_available_slots(employee, tomorrow, service)
        end_dt = timezone.make_aware(datetime.datetime.combine(tomorrow, schedule.end_time))
        service_duration = datetime.timedelta(minutes=service.duration)
        for slot in slots:
            assert slot + service_duration <= end_dt

    def test_slots_are_15_min_apart(self, employee, service, schedule, tomorrow):
        slots = get_available_slots(employee, tomorrow, service)
        for a, b in itertools.pairwise(slots):
            assert (b - a) == datetime.timedelta(minutes=15)

    def test_booked_slot_is_excluded(self, employee, service, schedule, tomorrow):
        # Book the very first slot (09:00)
        make_appointment(employee, service, tomorrow, hour=9, minute=0)
        slots = get_available_slots(employee, tomorrow, service)
        booked = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(9, 0)))
        assert booked not in slots

    def test_cancelled_appointment_does_not_block_slot(self, employee, service, schedule, tomorrow):
        make_appointment(employee, service, tomorrow, hour=9, minute=0, status=Appointment.Status.CANCELLED)
        slots = get_available_slots(employee, tomorrow, service)
        booked = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(9, 0)))
        assert booked in slots

    def test_overlapping_appointments_block_overlapping_slots(self, employee, service, schedule, tomorrow):
        """A 60-min appointment at 10:00 should block slots 09:15–10:45 that overlap with it."""
        make_appointment(employee, service, tomorrow, hour=10, minute=0)
        slots = get_available_slots(employee, tomorrow, service)
        slot_times = {s.time() for s in slots}
        # 09:15 + 60 min = 10:15 → overlaps with 10:00–11:00 booking
        assert datetime.time(9, 15) not in slot_times
        # 10:00 itself is the booked slot
        assert datetime.time(10, 0) not in slot_times
        # 11:00 should be free (ends exactly when booking ends)
        assert datetime.time(11, 0) in slot_times

    def test_shorter_service_reveals_slots_hidden_for_longer_service(
        self, employee, service, service_short, schedule, tomorrow
    ):
        """A 60-min booking at 10:00 blocks 09:15-09:45 for a 60-min service,
        but a 30-min service only needs to end by 10:00, so those same slots
        are free again."""
        make_appointment(employee, service, tomorrow, hour=10, minute=0)

        slots_60min = {s.time() for s in get_available_slots(employee, tomorrow, service)}
        slots_30min = {s.time() for s in get_available_slots(employee, tomorrow, service_short)}

        # 60-min service: 09:15 (->10:15) and 09:30 (->10:30) both overlap the booking
        assert datetime.time(9, 15) not in slots_60min
        assert datetime.time(9, 30) not in slots_60min

        # 30-min service: 09:15 (->09:45) and 09:30 (->10:00) don't overlap it
        assert datetime.time(9, 15) in slots_30min
        assert datetime.time(9, 30) in slots_30min

        # 09:45 + 30 min = 10:15 -> still overlaps the 10:00-11:00 booking
        assert datetime.time(9, 45) not in slots_30min

    def test_time_block_excludes_overlapping_slots(self, employee, service, schedule, tomorrow):
        """An owner-set block 12:00-14:00 should hide slots overlapping with it."""
        make_time_block(employee, tomorrow, start_hour=12, end_hour=14)
        slots = get_available_slots(employee, tomorrow, service)
        slot_times = {s.time() for s in slots}
        assert datetime.time(12, 0) not in slot_times
        assert datetime.time(13, 0) not in slot_times
        # 11:00 + 60 min service would end exactly at 12:00 -> still free
        assert datetime.time(11, 0) in slot_times
        # 14:00 is free again once the block ends
        assert datetime.time(14, 0) in slot_times

    def test_time_block_for_other_employee_does_not_affect_slots(self, employee, service, schedule, tomorrow):
        other = employee.__class__.objects.create(first_name='Ola', last_name='Nowak', bio='Stylistka.')
        make_time_block(other, tomorrow, start_hour=12, end_hour=14)
        slots = get_available_slots(employee, tomorrow, service)
        slot_times = {s.time() for s in slots}
        assert datetime.time(12, 0) in slot_times


class TestFindAvailableSpecialist:
    def test_finds_specialist_for_free_slot(self, employee, service, schedule, tomorrow):
        dt = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(9, 0)))
        result = find_available_specialist(service, dt)
        assert result == employee

    def test_returns_none_when_slot_is_fully_booked(self, employee, service, schedule, tomorrow):
        make_appointment(employee, service, tomorrow, hour=9, minute=0)
        dt = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(9, 0)))
        result = find_available_specialist(service, dt)
        assert result is None

    def test_returns_none_when_no_schedule(self, employee, service):
        dt = timezone.make_aware(datetime.datetime.combine(datetime.date(2030, 1, 1), datetime.time(9, 0)))
        result = find_available_specialist(service, dt)
        assert result is None

    def test_accepts_naive_datetime(self, employee, service, schedule, tomorrow):
        naive_dt = datetime.datetime.combine(tomorrow, datetime.time(9, 0))
        result = find_available_specialist(service, naive_dt)
        assert result == employee


class TestNextAvailableDate:
    def test_none_without_schedules(self, employee):
        assert next_available_date() is None

    def test_first_day_with_a_free_slot(self, employee, tomorrow):
        assert next_available_date() == tomorrow

    def test_skips_a_fully_booked_day(self, employee, service, tomorrow):
        make_time_block(employee, tomorrow, 9, 17, reason='Urlop')
        later = tomorrow + datetime.timedelta(days=3)
        Schedule.objects.create(employee=employee, date=later, start_time=datetime.time(10), end_time=datetime.time(12))
        assert next_available_date() == later

    def test_shortest_service_decides(self, employee, service, service_short, tomorrow):
        # Only 30 minutes are free: too short for the 60-min manicure, enough for the 30-min consultation
        make_time_block(employee, tomorrow, 9, 16)
        Schedule.objects.filter(employee=employee).update(end_time=datetime.time(16, 30))
        assert next_available_date() is None
        employee.services.add(service_short)
        assert next_available_date() == tomorrow

    def test_ignores_inactive_employees_and_services(self, employee, service, tomorrow):
        service.is_active = False
        service.save()
        assert next_available_date() is None
        service.is_active = True
        service.save()
        employee.is_active = False
        employee.save()
        assert next_available_date() is None

    def test_looks_only_days_ahead(self, employee, tomorrow):
        Schedule.objects.filter(employee=employee).update(date=timezone.localdate() + datetime.timedelta(days=40))
        assert next_available_date(days_ahead=30) is None
        assert next_available_date(days_ahead=45) is not None
