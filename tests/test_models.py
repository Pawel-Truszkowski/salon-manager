import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bookings.models import Appointment
from apps.services.models import Service
from tests.conftest import make_appointment


@pytest.mark.django_db
class TestAppointmentConfirm:
    def test_confirm_sets_status_to_confirmed(self, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.PENDING)
        result = appt.confirm()
        appt.refresh_from_db()
        assert result is True
        assert appt.status == Appointment.Status.CONFIRMED

    def test_confirm_sends_confirmation_email_to_client(self, employee, service, tomorrow, mailoutbox):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.PENDING)
        mailoutbox.clear()
        appt.confirm()
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [appt.client_email]

    def test_confirm_already_confirmed_is_noop(self, employee, service, tomorrow, mailoutbox):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CONFIRMED)
        mailoutbox.clear()
        result = appt.confirm()
        assert result is False
        assert len(mailoutbox) == 0

    def test_confirm_on_cancelled_appointment_still_confirms(self, employee, service, tomorrow, mailoutbox):
        """confirm() only special-cases the already-confirmed status, so a
        cancelled appointment can still be (re)confirmed."""
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CANCELLED)
        mailoutbox.clear()
        result = appt.confirm()
        appt.refresh_from_db()
        assert result is True
        assert appt.status == Appointment.Status.CONFIRMED
        assert len(mailoutbox) == 1


@pytest.mark.django_db
class TestAppointmentCancel:
    def test_cancel_sets_status_to_cancelled(self, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CONFIRMED)
        result = appt.cancel()
        appt.refresh_from_db()
        assert result is True
        assert appt.status == Appointment.Status.CANCELLED

    def test_cancel_sends_email_to_client_and_salon(self, employee, service, tomorrow, mailoutbox):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.PENDING)
        mailoutbox.clear()
        appt.cancel()
        assert len(mailoutbox) == 2
        recipients = [m.to[0] for m in mailoutbox]
        assert appt.client_email in recipients

    def test_cancel_already_cancelled_is_noop(self, employee, service, tomorrow, mailoutbox):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CANCELLED)
        mailoutbox.clear()
        result = appt.cancel()
        assert result is False
        assert len(mailoutbox) == 0

    def test_cancel_completed_appointment_is_noop(self, employee, service, tomorrow, mailoutbox):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.COMPLETED)
        mailoutbox.clear()
        result = appt.cancel()
        assert result is False
        assert len(mailoutbox) == 0

    def test_cancel_past_appointment_is_noop(self, employee, service, mailoutbox):
        yesterday = (timezone.now() - datetime.timedelta(days=1)).date()
        appt = make_appointment(employee, service, yesterday, hour=10, status=Appointment.Status.CONFIRMED)
        mailoutbox.clear()
        result = appt.cancel()
        assert result is False
        assert len(mailoutbox) == 0

    def test_each_appointment_gets_a_unique_cancellation_token(self, employee, service, tomorrow):
        appt_1 = make_appointment(employee, service, tomorrow, hour=10)
        appt_2 = make_appointment(employee, service, tomorrow, hour=11)
        assert appt_1.cancellation_token != appt_2.cancellation_token

    def test_get_cancel_url_contains_token(self, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, hour=10)
        assert str(appt.cancellation_token) in appt.get_cancel_url()


class TestServicePriceLabel:
    @pytest.mark.parametrize(
        ('price', 'label'),
        [('0', 'bezpłatnie'), ('0.00', 'bezpłatnie'), ('30.00', '30 zł'), ('400', '400 zł'), ('30.50', '30,50 zł')],
    )
    def test_label(self, price, label):
        assert Service(price=Decimal(price)).price_label == label
