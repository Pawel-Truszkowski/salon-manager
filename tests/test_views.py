import datetime
import json
import re

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Appointment
from tests.conftest import make_appointment, make_time_block


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

    def test_returns_409_when_time_is_blocked_by_owner(self, employee, service, schedule, tomorrow):
        make_time_block(employee, tomorrow, start_hour=12, end_hour=14)
        response = post_booking(self.client, service, employee, time='12:00', date=tomorrow)
        assert response.status_code == 409
        data = json.loads(response.content)
        assert data['ok'] is False
        assert Appointment.objects.count() == 0

    def test_allows_booking_outside_blocked_range(self, employee, service, schedule, tomorrow):
        make_time_block(employee, tomorrow, start_hour=12, end_hour=14)
        response = post_booking(self.client, service, employee, time='14:00', date=tomorrow)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['ok'] is True

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
class TestEmployeesAPI:
    def test_does_not_expose_contact_data(self, client, employee):
        [data] = client.get(reverse('api-employees')).json()

        assert data['first_name'] == employee.first_name
        assert 'email' not in data


@pytest.mark.django_db
class TestAvailableSlotsAPI:
    def setup_method(self):
        self.client = Client()

    def test_returns_slots_for_valid_params(self, employee, service, schedule, tomorrow):
        response = self.client.get(
            reverse('api-available-slots'),
            {
                'date': tomorrow.isoformat(),
                'service': service.pk,
                'employee': employee.pk,
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['slots']) > 0

    def test_returns_400_without_required_params(self, service):
        response = self.client.get(reverse('api-available-slots'))
        assert response.status_code == 400

    def test_returns_400_for_past_date(self, service):
        past = (timezone.now() - datetime.timedelta(days=1)).date()
        response = self.client.get(
            reverse('api-available-slots'),
            {
                'date': past.isoformat(),
                'service': service.pk,
            },
        )
        assert response.status_code == 400

    def test_returns_empty_when_no_schedule(self, employee, service):
        # Deliberately no schedule fixture — employee has no working hours on this date
        date_without_schedule = (timezone.now() + datetime.timedelta(days=30)).date()
        response = self.client.get(
            reverse('api-available-slots'),
            {
                'date': date_without_schedule.isoformat(),
                'service': service.pk,
                'employee': employee.pk,
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['slots'] == []

    def test_aggregates_slots_from_all_employees_when_no_employee_param(self, employee, service, schedule, tomorrow):
        response = self.client.get(
            reverse('api-available-slots'),
            {
                'date': tomorrow.isoformat(),
                'service': service.pk,
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['slots']) > 0

    def test_excludes_slots_blocked_by_owner(self, employee, service, schedule, tomorrow):
        make_time_block(employee, tomorrow, start_hour=12, end_hour=14)
        response = self.client.get(
            reverse('api-available-slots'),
            {
                'date': tomorrow.isoformat(),
                'service': service.pk,
                'employee': employee.pk,
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert '12:00' not in data['slots']
        assert '13:00' not in data['slots']
        assert '14:00' in data['slots']


@pytest.mark.django_db
class TestAvailableDatesAPI:
    def setup_method(self):
        self.client = Client()

    def test_returns_date_with_open_schedule(self, employee, service, schedule, tomorrow):
        response = self.client.get(
            reverse('api-available-dates'),
            {
                'service': service.pk,
                'employee': employee.pk,
                'month': f'{tomorrow.year}-{tomorrow.month:02d}',
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert tomorrow.isoformat() in data['dates']

    def test_excludes_date_fully_blocked_by_owner(self, employee, service, schedule, tomorrow):
        # Block the entire working day (09:00-17:00 per the `schedule` fixture)
        make_time_block(employee, tomorrow, start_hour=9, end_hour=17)
        response = self.client.get(
            reverse('api-available-dates'),
            {
                'service': service.pk,
                'employee': employee.pk,
                'month': f'{tomorrow.year}-{tomorrow.month:02d}',
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert tomorrow.isoformat() not in data['dates']

    def test_keeps_date_when_only_partially_blocked(self, employee, service, schedule, tomorrow):
        make_time_block(employee, tomorrow, start_hour=12, end_hour=14)
        response = self.client.get(
            reverse('api-available-dates'),
            {
                'service': service.pk,
                'employee': employee.pk,
                'month': f'{tomorrow.year}-{tomorrow.month:02d}',
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert tomorrow.isoformat() in data['dates']


@pytest.mark.django_db
class TestCancelBookingView:
    def setup_method(self):
        self.client = Client()

    def test_get_shows_confirmation_page_for_cancellable_appointment(self, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CONFIRMED)
        response = self.client.get(reverse('cancel_booking', args=[appt.cancellation_token]))
        assert response.status_code == 200
        assert Appointment.objects.get(pk=appt.pk).status == Appointment.Status.CONFIRMED

    def test_post_cancels_the_appointment(self, employee, service, tomorrow, mailoutbox):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CONFIRMED)
        mailoutbox.clear()
        response = self.client.post(reverse('cancel_booking', args=[appt.cancellation_token]))
        assert response.status_code == 200
        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CANCELLED
        assert len(mailoutbox) == 2

    def test_unknown_token_returns_404(self):
        response = self.client.get(reverse('cancel_booking', args=['00000000-0000-0000-0000-000000000000']))
        assert response.status_code == 404

    def test_post_on_already_cancelled_appointment_does_not_resend_emails(
        self, employee, service, tomorrow, mailoutbox
    ):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CANCELLED)
        mailoutbox.clear()
        response = self.client.post(reverse('cancel_booking', args=[appt.cancellation_token]))
        assert response.status_code == 200
        assert len(mailoutbox) == 0


class TestSelfHostedFonts:
    """Fonts are served from static/ so no visitor IP reaches Google Fonts (GDPR)."""

    @pytest.mark.parametrize('url_name', ['home', 'panel:login'])
    def test_page_uses_local_fonts_only(self, client, db, url_name):
        response = client.get(reverse(url_name))
        assert response.status_code == 200
        assert 'css/fonts.css' in response.content.decode()
        assert 'fonts.googleapis.com' not in response.content.decode()
        assert 'fonts.gstatic.com' not in response.content.decode()

    def test_every_font_face_points_to_an_existing_file(self):
        static_dir = settings.STATICFILES_DIRS[0]
        css = (static_dir / 'css' / 'fonts.css').read_text()
        urls = re.findall(r'url\("\.\./(fonts/[^"]+)"\)', css)
        assert urls
        missing = [u for u in urls if not (static_dir / u).is_file()]
        assert missing == []


class TestHeaderAndHero:
    def test_home_has_exactly_one_h1_with_the_main_phrase(self, client, db):
        html = client.get(reverse('home')).content.decode()
        assert html.count('<h1') == 1
        assert 'Salon kosmetyczny we Wrocławiu' in html

    def test_phone_numbers_are_tel_links(self, client, db):
        html = client.get(reverse('home')).content.decode()
        assert 'href="tel:+48793355756"' in html
        assert 'href="tel:+48792646256"' in html

    def test_hero_does_not_claim_fixed_opening_hours(self, client, db):
        html = client.get(reverse('home')).content.decode()
        assert 'po umówieniu' in html
        assert 'w sercu miasta' not in html

    def test_menu_on_other_pages_links_back_to_home_sections(self, client, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, hour=10)
        html = client.get(reverse('cancel_booking', args=[appt.cancellation_token])).content.decode()
        assert f'href="{reverse("home")}#uslugi"' in html
        assert 'href="#uslugi"' not in html
