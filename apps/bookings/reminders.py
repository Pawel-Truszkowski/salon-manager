"""E-mail reminders about appointments, sent about 24 h before by the hourly send_reminders command."""

import datetime

from django.db.models import F
from django.utils import timezone

from .emails import send_reminder_email
from .models import Appointment

REMIND_BEFORE = datetime.timedelta(hours=24)


def due_reminders(now):
    """Appointments that should get their reminder at `now`."""
    return (
        Appointment.objects.filter(
            status=Appointment.Status.CONFIRMED,  # a pending one isn't certain yet: no "see you tomorrow"
            reminder_sent_at__isnull=True,
            date_time__gt=now,
            date_time__lte=now + REMIND_BEFORE,
            # Booked less than 24 h ahead: the confirmation e-mail has just told her everything
            created_at__lte=F('date_time') - REMIND_BEFORE,
        )
        # Phone bookings without an e-mail would be picked up (and skipped) every hour
        .exclude(client_email='')
    )


def send_due_reminders(now=None):
    """Sends the due reminders and returns how many went out."""
    now = now or timezone.now()
    sent = 0
    for appointment in due_reminders(now).select_related('service', 'employee'):
        # Marked only after a successful send: a Resend outage means another try in an hour, not a lost reminder
        if send_reminder_email(appointment):
            Appointment.objects.filter(pk=appointment.pk).update(reminder_sent_at=now)
            sent += 1
    return sent
