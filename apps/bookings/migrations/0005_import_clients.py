"""Client file from the appointments booked so far: one client per phone number.

The newest appointment gives the name, the newest non-empty e-mail the e-mail (people correct typos over time).
"Client since" is the first booking, not the day of this import.
"""

import re

from django.db import migrations


def normalize_phone(phone):
    # Frozen copy of apps.bookings.models.normalize_phone: migrations must not import code that may change
    digits = re.sub(r'\D', '', phone or '')
    for prefix in ('0048', '48'):
        if digits.startswith(prefix) and len(digits) == len(prefix) + 9:
            return digits[len(prefix) :]
    return digits


def import_clients(apps, schema_editor):
    Appointment = apps.get_model('bookings', 'Appointment')
    Client = apps.get_model('bookings', 'Client')

    by_phone = {}
    for appointment in Appointment.objects.order_by('-date_time'):
        phone = normalize_phone(appointment.client_phone)
        if not phone:
            continue
        if phone not in by_phone:
            by_phone[phone] = Client.objects.create(
                phone=phone, name=appointment.client_name, email=appointment.client_email
            )
        client = by_phone[phone]
        if not client.email and appointment.client_email:
            client.email = appointment.client_email
            client.save(update_fields=['email'])
        Appointment.objects.filter(pk=appointment.pk).update(client=client)
    for client in by_phone.values():
        first = Appointment.objects.filter(client=client).order_by('created_at').first()
        Client.objects.filter(pk=client.pk).update(created_at=first.created_at)


class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0004_client'),
    ]

    operations = [
        migrations.RunPython(import_clients, migrations.RunPython.noop),
    ]
