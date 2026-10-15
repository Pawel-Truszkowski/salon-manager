import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.panel.forms import GenerateScheduleForm
from apps.services.models import Schedule, WeeklyScheduleEntry
from tests.conftest import make_time_block

SCHEDULE_URL = reverse('panel:schedule')


def in_days(days):
    return timezone.localdate() + datetime.timedelta(days=days)


def generate_url(employee):
    return reverse('panel:schedule_generate', args=[employee.pk])


def range_data(date_from, date_to):
    return {'date_from': date_from.isoformat(), 'date_to': date_to.isoformat()}


@pytest.fixture
def weekdays_template(employee):
    """Monday-Friday 9-17."""
    for weekday in range(5):
        WeeklyScheduleEntry.objects.create(
            employee=employee, weekday=weekday, start_time=datetime.time(9), end_time=datetime.time(17)
        )


@pytest.fixture
def owner_client(client, owner_user):
    client.force_login(owner_user)
    return client


@pytest.fixture
def employee_client(client, employee_user):
    client.force_login(employee_user)
    return client


class TestGenerateScheduleForm:
    def test_single_day_range_is_valid(self):
        assert GenerateScheduleForm(data=range_data(in_days(0), in_days(0))).is_valid()

    def test_max_days_inclusive_is_valid(self):
        days = GenerateScheduleForm.MAX_DAYS
        assert GenerateScheduleForm(data=range_data(in_days(0), in_days(days - 1))).is_valid()

    def test_one_day_over_max_is_rejected(self):
        days = GenerateScheduleForm.MAX_DAYS
        form = GenerateScheduleForm(data=range_data(in_days(0), in_days(days)))

        assert not form.is_valid()
        assert 'date_to' in form.errors

    def test_reversed_range_is_rejected(self):
        form = GenerateScheduleForm(data=range_data(in_days(5), in_days(1)))

        assert not form.is_valid()
        assert 'date_to' in form.errors

    def test_past_start_is_rejected_together_with_other_errors(self):
        form = GenerateScheduleForm(data=range_data(in_days(-1), in_days(-3)))

        assert not form.is_valid()
        assert set(form.errors) == {'date_from', 'date_to'}

    def test_missing_date_reports_only_the_field_error(self):
        form = GenerateScheduleForm(data={'date_from': in_days(0).isoformat(), 'date_to': 'nie-data'})

        assert not form.is_valid()
        assert list(form.errors) == ['date_to']
        assert len(form.errors['date_to']) == 1


@pytest.mark.django_db
class TestScheduleView:
    def test_employee_sees_her_own_schedule(self, employee_client, employee, weekdays_template):
        Schedule.objects.create(
            employee=employee, date=in_days(1), start_time=datetime.time(9), end_time=datetime.time(17)
        )
        make_time_block(employee, in_days(1), 12, 13)

        response = employee_client.get(SCHEDULE_URL)

        assert response.status_code == 200
        assert response.context['target_employee'] == employee
        assert response.context['has_template']
        tomorrow = response.context['days'][1]
        assert len(tomorrow['schedules']) == 1 and len(tomorrow['blocks']) == 1

    def test_employee_gets_404_for_someone_elses_schedule(self, employee_client, other_employee):
        assert employee_client.get(f'{SCHEDULE_URL}?employee={other_employee.pk}').status_code == 404

    def test_owner_picks_employee(self, owner_client, other_employee):
        response = owner_client.get(f'{SCHEDULE_URL}?employee={other_employee.pk}')

        assert response.context['target_employee'] == other_employee
        # No template -> hint instead of the generate form
        assert not response.context['has_template']
        assert 'Najpierw uzupełnij' in response.content.decode()

    def test_owner_without_employees_sees_empty_state(self, owner_client):
        response = owner_client.get(SCHEDULE_URL)

        assert response.status_code == 200
        assert 'Brak specjalistek' in response.content.decode()


@pytest.mark.django_db
class TestScheduleGenerate:
    def test_generates_from_template_and_reports_count(self, employee_client, employee, weekdays_template):
        monday = in_days(7 - in_days(0).weekday())  # next Monday, so the week is fully in the future

        data = range_data(monday, monday + datetime.timedelta(6))

        response = employee_client.post(generate_url(employee), data, follow=True)

        assert response.redirect_chain == [(f'{SCHEDULE_URL}?employee={employee.pk}', 302)]
        assert Schedule.objects.filter(employee=employee).count() == 5
        assert '5 bloków' in response.content.decode()

    def test_second_generate_reports_nothing_added(self, employee_client, employee, weekdays_template):
        data = range_data(in_days(0), in_days(13))
        employee_client.post(generate_url(employee), data)
        count = Schedule.objects.count()

        response = employee_client.post(generate_url(employee), data, follow=True)

        assert Schedule.objects.count() == count
        assert 'Nic nie dodano' in response.content.decode()

    def test_invalid_range_creates_nothing_and_shows_error(self, employee_client, employee, weekdays_template):
        response = employee_client.post(generate_url(employee), range_data(in_days(5), in_days(1)), follow=True)

        assert not Schedule.objects.exists()
        assert 'nie może być wcześniejsza' in response.content.decode()

    def test_employee_cannot_generate_for_someone_else(self, employee_client, other_employee):
        WeeklyScheduleEntry.objects.create(
            employee=other_employee, weekday=0, start_time=datetime.time(9), end_time=datetime.time(17)
        )

        response = employee_client.post(generate_url(other_employee), range_data(in_days(0), in_days(13)))

        assert response.status_code == 404
        assert not Schedule.objects.exists()

    def test_get_is_not_allowed(self, employee_client, employee):
        assert employee_client.get(generate_url(employee)).status_code == 405
