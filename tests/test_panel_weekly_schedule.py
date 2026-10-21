import datetime

import pytest
from django.urls import reverse

from apps.services.models import WeeklyScheduleEntry

PREFIX = 'weekly_schedule'
MONDAY, WEDNESDAY = WeeklyScheduleEntry.WeekDay.MONDAY, WeeklyScheduleEntry.WeekDay.WEDNESDAY


def url(employee):
    return reverse('panel:weekly_schedule', args=[employee.pk])


def row(weekday, start, end, **extra):
    return {'weekday': weekday, 'start_time': start, 'end_time': end, **extra}


def existing_row(entry, **extra):
    """POST data for a row that edits an already saved entry."""
    return row(
        entry.weekday,
        f'{entry.start_time:%H:%M}',
        f'{entry.end_time:%H:%M}',
        id=entry.pk,
        employee=entry.employee_id,
        **extra,
    )


def formset_data(*rows, initial=0):
    """Builds the POST payload: management form + `PREFIX-<n>-<field>` keys, as the browser would send it."""
    data = {
        f'{PREFIX}-TOTAL_FORMS': len(rows),
        f'{PREFIX}-INITIAL_FORMS': initial,
        f'{PREFIX}-MIN_NUM_FORMS': 0,
        f'{PREFIX}-MAX_NUM_FORMS': 1000,
    }
    for index, fields in enumerate(rows):
        data.update({f'{PREFIX}-{index}-{name}': value for name, value in fields.items()})
    return data


def saved_template(employee):
    return list(employee.weekly_schedule.values_list('weekday', 'start_time', 'end_time'))


@pytest.fixture
def owner_client(client, owner_user):
    client.force_login(owner_user)
    return client


@pytest.fixture
def employee_client(client, employee_user):
    client.force_login(employee_user)
    return client


@pytest.mark.django_db
class TestWeeklyScheduleAccess:
    def test_employee_opens_her_own_template(self, employee_client, employee):
        response = employee_client.get(url(employee))

        assert response.status_code == 200
        # Empty row template for the "add block" button
        assert f'{PREFIX}-__prefix__-weekday' in response.content.decode()

    def test_employee_gets_404_for_someone_elses_template(self, employee_client, other_employee):
        assert employee_client.get(url(other_employee)).status_code == 404
        response = employee_client.post(url(other_employee), formset_data(row(MONDAY, '09:00', '17:00')))
        assert response.status_code == 404
        assert not WeeklyScheduleEntry.objects.exists()

    def test_owner_edits_any_template(self, owner_client, other_employee):
        response = owner_client.post(url(other_employee), formset_data(row(MONDAY, '09:00', '17:00')))

        assert response.status_code == 302
        assert len(saved_template(other_employee)) == 1


@pytest.mark.django_db
class TestWeeklyScheduleSave:
    def test_saves_split_shift_and_ignores_empty_extra_row(self, employee_client, employee):
        response = employee_client.post(
            url(employee),
            formset_data(
                row(MONDAY, '09:00', '13:00'),
                row(MONDAY, '14:00', '18:00'),
                row('', '', ''),
            ),
        )

        assert response.status_code == 302
        assert len(saved_template(employee)) == 2

    def test_touching_blocks_are_allowed(self, employee_client, employee):
        response = employee_client.post(
            url(employee), formset_data(row(MONDAY, '09:00', '13:00'), row(MONDAY, '13:00', '17:00'))
        )

        assert response.status_code == 302

    def test_same_hours_on_different_days_are_allowed(self, employee_client, employee):
        response = employee_client.post(
            url(employee), formset_data(row(MONDAY, '09:00', '17:00'), row(WEDNESDAY, '09:00', '17:00'))
        )

        assert response.status_code == 302

    def test_deletes_marked_row(self, employee_client, employee):
        keep = WeeklyScheduleEntry.objects.create(
            employee=employee, weekday=MONDAY, start_time=datetime.time(9), end_time=datetime.time(13)
        )
        drop = WeeklyScheduleEntry.objects.create(
            employee=employee, weekday=MONDAY, start_time=datetime.time(14), end_time=datetime.time(18)
        )

        response = employee_client.post(
            url(employee), formset_data(existing_row(keep), existing_row(drop, DELETE='on'), initial=2)
        )

        assert response.status_code == 302
        assert list(employee.weekly_schedule.values_list('pk', flat=True)) == [keep.pk]


@pytest.mark.django_db
class TestWeeklyScheduleValidation:
    def test_end_before_start_is_a_field_error(self, employee_client, employee):
        response = employee_client.post(url(employee), formset_data(row(MONDAY, '12:00', '10:00')))

        assert response.status_code == 200
        assert 'end_time' in response.context['formset'].errors[0]
        assert not WeeklyScheduleEntry.objects.exists()

    def test_overlapping_blocks_on_the_same_day_are_rejected(self, employee_client, employee):
        response = employee_client.post(
            url(employee), formset_data(row(MONDAY, '09:00', '13:00'), row(MONDAY, '12:00', '16:00'))
        )

        assert response.status_code == 200
        errors = response.context['formset'].non_form_errors()
        assert 'poniedziałek' in errors[0] and '09:00–13:00' in errors[0]
        assert not WeeklyScheduleEntry.objects.exists()

    def test_overlap_with_a_row_being_deleted_is_ignored(self, employee_client, employee):
        old = WeeklyScheduleEntry.objects.create(
            employee=employee, weekday=MONDAY, start_time=datetime.time(9), end_time=datetime.time(17)
        )

        # Replace 9-17 with 10-14 in one submit: the deleted row must not count as a conflict
        response = employee_client.post(
            url(employee),
            formset_data(existing_row(old, DELETE='on'), row(MONDAY, '10:00', '14:00'), initial=1),
        )

        assert response.status_code == 302
        assert [(start.hour, end.hour) for _, start, end in saved_template(employee)] == [(10, 14)]

    def test_row_with_missing_time_does_not_crash_overlap_check(self, employee_client, employee):
        response = employee_client.post(
            url(employee), formset_data(row(MONDAY, '09:00', '13:00'), row(MONDAY, '12:00', ''))
        )

        assert response.status_code == 200
        assert 'end_time' in response.context['formset'].errors[1]
