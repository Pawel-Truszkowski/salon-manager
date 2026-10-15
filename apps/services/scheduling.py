import datetime
from collections import defaultdict

from .models import Employee, Schedule


def generate_schedules(employee: Employee, date_from: datetime.date, date_to: datetime.date) -> int:
    """Create `Schedule` rows for `employee` from their weekly template, for every day in [date_from, date_to].

    Days that already have at least one `Schedule` row are left untouched — they may contain manual
    exceptions (a longer shift, a swapped day) that the template must not overwrite.

    Returns the number of `Schedule` rows created.
    """
    if date_from > date_to:
        return 0

    # weekday (0 = Monday) -> that day's working blocks
    template = defaultdict(list)
    for entry in employee.weekly_schedule.all():
        template[entry.weekday].append(entry)

    if not template:
        return 0

    # One query instead of one per day; a set makes the `in` check below O(1)
    existing = set(
        Schedule.objects.filter(employee=employee, date__range=(date_from, date_to)).values_list('date', flat=True)
    )

    new_schedules = []
    for day in range((date_to - date_from).days + 1):
        current_date = date_from + datetime.timedelta(days=day)
        if current_date in existing:
            continue

        for entry in template.get(current_date.weekday(), []):
            new_schedules.append(
                Schedule(
                    employee=employee,
                    date=current_date,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                )
            )

    Schedule.objects.bulk_create(new_schedules)
    return len(new_schedules)
