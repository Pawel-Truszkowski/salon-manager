import datetime

import pytest

from apps.services.models import Schedule, WeeklyScheduleEntry
from apps.services.scheduling import generate_schedules

# Fixed dates keep the tests independent of "today": 2026-10-12 is a Monday
MONDAY = datetime.date(2026, 10, 12)
TUESDAY = MONDAY + datetime.timedelta(days=1)
WEDNESDAY = MONDAY + datetime.timedelta(days=2)
SUNDAY = MONDAY + datetime.timedelta(days=6)


def t(hour, minute=0):
    return datetime.time(hour, minute)


@pytest.fixture
def template(employee):
    """Monday 9-17, Wednesday split shift 9-13 + 14-18, every other day off."""
    Day = WeeklyScheduleEntry.WeekDay
    for weekday, start, end in [
        (Day.MONDAY, t(9), t(17)),
        (Day.WEDNESDAY, t(9), t(13)),
        (Day.WEDNESDAY, t(14), t(18)),
    ]:
        WeeklyScheduleEntry.objects.create(employee=employee, weekday=weekday, start_time=start, end_time=end)


def schedule_rows(employee):
    """Generated schedule as comparable tuples, sorted."""
    return sorted(Schedule.objects.filter(employee=employee).values_list('date', 'start_time', 'end_time'))


@pytest.mark.django_db
class TestGenerateSchedules:
    def test_creates_rows_for_working_days_of_the_template(self, employee, template):
        created = generate_schedules(employee, MONDAY, SUNDAY)

        assert created == 3
        assert schedule_rows(employee) == [
            (MONDAY, t(9), t(17)),
            (WEDNESDAY, t(9), t(13)),
            (WEDNESDAY, t(14), t(18)),
        ]

    def test_skips_days_that_already_have_a_schedule(self, employee, template):
        # Manual exception: a longer Monday that the template must not overwrite
        Schedule.objects.create(employee=employee, date=MONDAY, start_time=t(8), end_time=t(20))

        created = generate_schedules(employee, MONDAY, SUNDAY)

        assert created == 2
        assert (MONDAY, t(8), t(20)) in schedule_rows(employee)
        assert (MONDAY, t(9), t(17)) not in schedule_rows(employee)

    def test_returns_zero_if_date_from_is_after_date_to(self, employee, template):
        created = generate_schedules(employee, SUNDAY, MONDAY)

        assert created == 0
        assert schedule_rows(employee) == []

    def test_returns_zero_if_template_is_empty(self, employee):
        created = generate_schedules(employee, MONDAY, SUNDAY)

        assert created == 0
        assert schedule_rows(employee) == []

    def test_returns_zero_if_no_days_in_range_match_template(self, employee, template):
        created = generate_schedules(employee, TUESDAY, TUESDAY)

        assert created == 0
        assert schedule_rows(employee) == []

    def test_idempotency(self, employee, template):
        created1 = generate_schedules(employee, MONDAY, SUNDAY)
        created2 = generate_schedules(employee, MONDAY, SUNDAY)

        assert created1 == 3
        assert created2 == 0
        assert schedule_rows(employee) == [
            (MONDAY, t(9), t(17)),
            (WEDNESDAY, t(9), t(13)),
            (WEDNESDAY, t(14), t(18)),
        ]
