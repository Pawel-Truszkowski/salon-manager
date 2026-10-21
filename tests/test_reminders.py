import datetime

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from apps.bookings.models import Appointment
from apps.bookings.reminders import send_due_reminders

from .conftest import make_appointment


def at(hours_from_now, employee, service, booked_days_ago=3, **kwargs):
    """Appointment `hours_from_now` from now, booked `booked_days_ago` days ago."""
    when = timezone.now() + datetime.timedelta(hours=hours_from_now)
    appointment = make_appointment(employee, service, timezone.localdate(when), 0, **kwargs)
    Appointment.objects.filter(pk=appointment.pk).update(
        date_time=when, created_at=timezone.now() - datetime.timedelta(days=booked_days_ago)
    )
    appointment.refresh_from_db()
    mail.outbox.clear()  # drop the "booking received" e-mails sent on create
    return appointment


@pytest.fixture
def outbox(mailoutbox):
    return mailoutbox


class TestSendDueReminders:
    def test_confirmed_appointment_within_24h_gets_a_reminder(self, employee, service, outbox):
        appointment = at(20, employee, service)
        assert send_due_reminders() == 1
        assert outbox[0].to == ['klient@test.pl']
        assert 'Przypomnienie o wizycie' in outbox[0].subject
        assert appointment.get_cancel_url() in outbox[0].alternatives[0][0]
        appointment.refresh_from_db()
        assert appointment.reminder_sent_at is not None

    def test_appointment_more_than_24h_away_waits(self, employee, service, outbox):
        at(30, employee, service)
        assert send_due_reminders() == 0
        assert outbox == []

    def test_past_appointment_gets_nothing(self, employee, service, outbox):
        at(-1, employee, service)
        assert send_due_reminders() == 0

    @pytest.mark.parametrize(
        'status', [Appointment.Status.PENDING, Appointment.Status.CANCELLED, Appointment.Status.COMPLETED]
    )
    def test_only_confirmed_appointments(self, employee, service, outbox, status):
        at(20, employee, service, status=status)
        assert send_due_reminders() == 0

    def test_booked_less_than_24h_before_gets_no_reminder(self, employee, service, outbox):
        at(20, employee, service, booked_days_ago=0)  # booked just now: the confirmation e-mail is enough
        assert send_due_reminders() == 0

    def test_reminder_is_sent_once(self, employee, service, outbox):
        at(20, employee, service)
        send_due_reminders()
        assert send_due_reminders() == 0
        assert len(outbox) == 1

    def test_client_without_email_is_skipped(self, employee, service, outbox):
        appointment = at(20, employee, service)
        Appointment.objects.filter(pk=appointment.pk).update(client_email='')
        assert send_due_reminders() == 0

    def test_failed_send_is_retried_next_run(self, employee, service, outbox, monkeypatch):
        appointment = at(20, employee, service)
        monkeypatch.setattr('apps.bookings.reminders.send_reminder_email', lambda appointment: False)
        send_due_reminders()
        appointment.refresh_from_db()
        assert appointment.reminder_sent_at is None

    def test_reschedule_clears_the_reminder(self, employee, service, outbox):
        appointment = at(20, employee, service)
        send_due_reminders()
        appointment.refresh_from_db()
        appointment.reschedule(appointment.date_time + datetime.timedelta(days=2))
        assert appointment.reminder_sent_at is None


def test_command_reports_how_many_were_sent(employee, service, outbox, capsys):
    at(20, employee, service)
    call_command('send_reminders')
    assert 'Sent 1 reminder(s).' in capsys.readouterr().out
