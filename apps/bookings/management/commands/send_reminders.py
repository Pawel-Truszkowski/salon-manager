from django.core.management.base import BaseCommand

from apps.bookings.reminders import send_due_reminders


class Command(BaseCommand):
    help = 'Sends e-mail reminders about appointments in the next 24 hours (run hourly from cron).'

    def handle(self, *args, **options):
        sent = send_due_reminders()
        self.stdout.write(f'Sent {sent} reminder(s).')
