import datetime
import json
import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Appointment
from tests.conftest import make_appointment


def future_date():
    return (timezone.now() + datetime.timedelta(days=1)).date()


def post_booking(client, service, employee=None, time='10:00', date=None):
    date = date or future_date()
    data = {
        'service': service.pk,
        'employee': employee.pk if employee else '',
        'client_name': 'Jan Kowalski',
        'client_phone': '123456789',
        'client_email': 'jan@test.pl',
        'date': date.isoformat(),
        'time': time,
        'notes': '',
    }
    return client.post(reverse('submit_booking'), data)


@pytest.mark.django_db
class TestSubmitBookingView:

    def setup_method(self):
        self.client = Client()

    def test_booking_created_successfully(self, employee, service, schedule, tomorrow):
        response = post_booking(self.client, service, employee, time='09:00', date=tomorrow)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['ok'] is True
        assert Appointment.objects.count() == 1

    def test_auto_assigns_specialist_when_none_selected(self, employee, service, schedule, tomorrow):
        response = post_booking(self.client, service, employee=None, time='09:00', date=tomorrow)
        assert response.status_code == 200
        appt = Appointment.objects.get()
        assert appt.employee == employee

    def test_returns_409_on_collision(self, employee, service, schedule, tomorrow):
        make_appointment(employee, service, tomorrow, hour=9, minute=0)
        response = post_booking(self.client, service, employee, time='09:00', date=tomorrow)
        assert response.status_code == 409
        data = json.loads(response.content)
        assert data['ok'] is False

    def test_returns_400_when_no_specialist_available(self, employee, service, schedule, tomorrow):
        # Fill the only available specialist
        make_appointment(employee, service, tomorrow, hour=9, minute=0)
        # Try to book without selecting specialist (auto-assign should fail)
        response = post_booking(self.client, service, employee=None, time='09:00', date=tomorrow)
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['ok'] is False

    def test_get_method_not_allowed(self, service):
        response = self.client.get(reverse('submit_booking'))
        assert response.status_code == 405

    def test_invalid_form_returns_400(self, service):
        response = self.client.post(reverse('submit_booking'), {})
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['ok'] is False
        assert 'errors' in data


@pytest.mark.django_db
class TestAvailableSlotsAPI:

    def setup_method(self):
        self.client = Client()

    def test_returns_slots_for_valid_params(self, employee, service, schedule, tomorrow):
        response = self.client.get(reverse('api-available-slots'), {
            'date': tomorrow.isoformat(),
            'service': service.pk,
            'employee': employee.pk,
        })
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['slots']) > 0

    def test_returns_400_without_required_params(self, service):
        response = self.client.get(reverse('api-available-slots'))
        assert response.status_code == 400

    def test_returns_400_for_past_date(self, service):
        past = (timezone.now() - datetime.timedelta(days=1)).date()
        response = self.client.get(reverse('api-available-slots'), {
            'date': past.isoformat(),
            'service': service.pk,
        })
        assert response.status_code == 400

    def test_returns_empty_when_no_schedule(self, employee, service):
        # Deliberately no schedule fixture — employee has no working hours on this date
        date_without_schedule = (timezone.now() + datetime.timedelta(days=30)).date()
        response = self.client.get(reverse('api-available-slots'), {
            'date': date_without_schedule.isoformat(),
            'service': service.pk,
            'employee': employee.pk,
        })
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['slots'] == []

    def test_aggregates_slots_from_all_employees_when_no_employee_param(
        self, employee, service, schedule, tomorrow
    ):
        response = self.client.get(reverse('api-available-slots'), {
            'date': tomorrow.isoformat(),
            'service': service.pk,
        })
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['slots']) > 0
