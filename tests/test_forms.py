import datetime
import pytest
from django.utils import timezone

from apps.bookings.forms import BookingForm


def future_date():
    return (timezone.now() + datetime.timedelta(days=1)).date()


def valid_data(service, time='10:00'):
    return {
        'service': service.pk,
        'employee': '',
        'client_name': 'Jan Kowalski',
        'client_phone': '123456789',
        'client_email': 'jan@test.pl',
        'date': future_date().isoformat(),
        'time': time,
        'notes': '',
    }


@pytest.mark.django_db
class TestBookingForm:

    def test_valid_form(self, service):
        form = BookingForm(data=valid_data(service))
        assert form.is_valid(), form.errors

    def test_date_time_combined_correctly(self, service):
        form = BookingForm(data=valid_data(service, time='14:30'))
        assert form.is_valid()
        dt = form.cleaned_data['date_time']
        assert dt.hour == 14
        assert dt.minute == 30

    def test_past_datetime_is_invalid(self, service):
        data = valid_data(service)
        data['date'] = (timezone.now() - datetime.timedelta(days=1)).date().isoformat()
        data['time'] = '10:00'
        form = BookingForm(data=data)
        assert not form.is_valid()

    def test_invalid_time_format_raises_error(self, service):
        data = valid_data(service)
        data['time'] = 'nie-godzina'
        form = BookingForm(data=data)
        assert not form.is_valid()

    def test_missing_client_name_is_invalid(self, service):
        data = valid_data(service)
        data['client_name'] = ''
        form = BookingForm(data=data)
        assert not form.is_valid()
        assert 'client_name' in form.errors

    def test_missing_phone_is_invalid(self, service):
        data = valid_data(service)
        data['client_phone'] = ''
        form = BookingForm(data=data)
        assert not form.is_valid()
        assert 'client_phone' in form.errors

    def test_email_is_required(self, service):
        data = valid_data(service)
        data['client_email'] = ''
        form = BookingForm(data=data)
        assert not form.is_valid()
        assert 'client_email' in form.errors

    def test_employee_is_optional(self, service):
        data = valid_data(service)
        data['employee'] = ''
        form = BookingForm(data=data)
        assert form.is_valid(), form.errors
