import pytest

from apps.bookings.models import Appointment
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
