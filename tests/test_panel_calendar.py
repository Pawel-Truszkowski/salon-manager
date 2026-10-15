import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Appointment
from apps.services.models import Schedule
from tests.conftest import make_appointment, make_time_block

EVENTS_URL = reverse('panel:calendar_events')


def in_days(days):
    return timezone.localdate() + datetime.timedelta(days=days)


def week_params(**extra):
    """The range FullCalendar asks for: today .. +7 days, ISO datetimes with an offset."""
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return {'start': start.isoformat(), 'end': (start + datetime.timedelta(days=7)).isoformat(), **extra}


@pytest.fixture
def owner_client(client, owner_user):
    client.force_login(owner_user)
    return client


@pytest.fixture
def employee_client(client, employee_user):
    client.force_login(employee_user)
    return client


@pytest.mark.django_db
class TestCalendarEvents:
    def test_returns_appointment_as_event(self, employee_client, employee, service):
        appointment = make_appointment(employee, service, in_days(1), 10)

        response = employee_client.get(EVENTS_URL, week_params())

        assert response.status_code == 200
        [event] = response.json()
        begins = timezone.localtime(appointment.date_time)
        assert event == {
            'id': appointment.pk,
            'title': f'{appointment.client_name} — {service}',
            'start': begins.isoformat(),
            'end': (begins + datetime.timedelta(minutes=service.duration)).isoformat(),
            'url': reverse('panel:appointment_detail', args=[appointment.pk]),
            'color': '#b07d62',
        }

    def test_only_appointments_inside_the_range(self, employee_client, employee, service):
        make_appointment(employee, service, in_days(1), 10)
        make_appointment(employee, service, in_days(10), 10)

        assert len(employee_client.get(EVENTS_URL, week_params()).json()) == 1

    def test_cancelled_appointments_are_skipped(self, employee_client, employee, service):
        make_appointment(employee, service, in_days(1), 10, status=Appointment.Status.CANCELLED)

        assert employee_client.get(EVENTS_URL, week_params()).json() == []

    def test_pending_has_its_own_color(self, employee_client, employee, service):
        make_appointment(employee, service, in_days(1), 10, status=Appointment.Status.PENDING)

        [event] = employee_client.get(EVENTS_URL, week_params()).json()

        assert event['color'] == '#e0a100'

    def test_bare_dates_are_accepted(self, employee_client, employee, service):
        make_appointment(employee, service, in_days(1), 10)

        params = {'start': in_days(0).isoformat(), 'end': in_days(7).isoformat()}
        assert len(employee_client.get(EVENTS_URL, params).json()) == 1

    @pytest.mark.parametrize('params', [{}, {'start': '2026-10-12'}, {'start': 'wczoraj', 'end': 'jutro'}])
    def test_bad_params_are_400(self, employee_client, params):
        assert employee_client.get(EVENTS_URL, params).status_code == 400


@pytest.mark.django_db
class TestCalendarEventsScope:
    def test_employee_sees_only_her_own(self, employee_client, employee, other_employee, service):
        mine = make_appointment(employee, service, in_days(1), 10)
        make_appointment(other_employee, service, in_days(1), 12)

        events = employee_client.get(EVENTS_URL, week_params()).json()

        assert [event['id'] for event in events] == [mine.pk]

    def test_employee_param_is_ignored_for_employees(self, employee_client, employee, other_employee, service):
        make_appointment(other_employee, service, in_days(1), 12)

        assert employee_client.get(EVENTS_URL, week_params(employee=other_employee.pk)).json() == []

    def test_owner_sees_all_with_employee_name(self, owner_client, employee, other_employee, service):
        make_appointment(employee, service, in_days(1), 10)
        make_appointment(other_employee, service, in_days(1), 12)

        events = owner_client.get(EVENTS_URL, week_params()).json()

        assert len(events) == 2
        assert events[1]['title'].endswith(f'({other_employee})')

    def test_owner_filters_by_employee(self, owner_client, employee, other_employee, service):
        make_appointment(employee, service, in_days(1), 10)
        theirs = make_appointment(other_employee, service, in_days(1), 12)

        events = owner_client.get(EVENTS_URL, week_params(employee=other_employee.pk)).json()

        assert [event['id'] for event in events] == [theirs.pk]

    def test_anonymous_is_redirected_to_login(self, client):
        response = client.get(EVENTS_URL, week_params())

        assert response.status_code == 302
        assert reverse('panel:login') in response.url


@pytest.mark.django_db
class TestCalendarBackground:
    @pytest.fixture
    def tomorrow_setup(self, employee):
        Schedule.objects.create(
            employee=employee, date=in_days(1), start_time=datetime.time(9), end_time=datetime.time(17)
        )
        make_time_block(employee, in_days(1), 12, 13, reason='przerwa')

    def background(self, events):
        return [event for event in events if event.get('display') == 'background']

    def test_employee_gets_working_hours_and_blocks(self, employee_client, tomorrow_setup):
        events = self.background(employee_client.get(EVENTS_URL, week_params()).json())

        working, block = events
        assert working['color'] == '#d1e7dd'
        assert (working['start'], working['end']) == (
            timezone.make_aware(datetime.datetime.combine(in_days(1), datetime.time(9))).isoformat(),
            timezone.make_aware(datetime.datetime.combine(in_days(1), datetime.time(17))).isoformat(),
        )
        assert (block['title'], block['color']) == ('przerwa', '#adb5bd')

    def test_background_outside_the_range_is_skipped(self, employee_client, employee):
        make_time_block(employee, in_days(10), 12, 13)

        assert self.background(employee_client.get(EVENTS_URL, week_params()).json()) == []

    def test_owner_gets_background_only_for_one_employee(self, owner_client, employee, tomorrow_setup):
        assert self.background(owner_client.get(EVENTS_URL, week_params()).json()) == []
        assert len(self.background(owner_client.get(EVENTS_URL, week_params(employee=employee.pk)).json())) == 2
