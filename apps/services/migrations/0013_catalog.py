"""Price list as of October 2026, the same on every server.

Source: production (descriptions written there) + Booksy (laser hair removal, current durations). Lash lamination is no longer
offered. Names are tidied ("( twarz)" -> "(twarz)"); a service is found by its current or any old name, so the
migration fits both production and the older staging/local data. Only the catalog changes: accounts, schedules
and appointments stay as they are.
"""

import json
from pathlib import Path

from django.db import migrations

CATALOG = json.loads((Path(__file__).parent / '0013_catalog.json').read_text(encoding='utf-8'))


def apply_catalog(apps, schema_editor):
    Service = apps.get_model('services', 'Service')
    ServiceCategory = apps.get_model('services', 'ServiceCategory')
    Equipment = apps.get_model('services', 'Equipment')
    Employee = apps.get_model('services', 'Employee')
    Appointment = apps.get_model('bookings', 'Appointment')

    # A fresh database (tests, a new install) starts with an empty price list, as before
    if not Service.objects.exists():
        return

    for name in CATALOG['removed']:
        for service in Service.objects.filter(name=name):
            # Appointments PROTECT their service: a booked one is only hidden
            if Appointment.objects.filter(service=service).exists():
                Service.objects.filter(pk=service.pk).update(is_active=False)
            else:
                service.employees.clear()
                service.delete()

    categories = {
        c['slug']: ServiceCategory.objects.get_or_create(slug=c['slug'], defaults={'name': c['name']})[0]
        for c in CATALOG['categories']
    }
    # New services go to the specialists who already work; on production that's Paulina
    staff = list(Employee.objects.filter(is_active=True))
    for item in CATALOG['services']:
        fields = {
            'name': item['name'],
            'category': categories[item['category']],
            'description': item['description'],
            'price': item['price'],
            'price_is_from': item.get('price_is_from', False),
            'duration': item['duration'],
            'is_active': True,
        }
        if 'equipment' in item:
            fields['required_equipment'] = Equipment.objects.get(name=item['equipment'])
        names = [item['name'], *item.get('old_names', [])]
        service = Service.objects.filter(name__in=names).first()
        if service is None:
            service = Service.objects.create(**fields)
            service.employees.add(*staff)
        else:
            Service.objects.filter(pk=service.pk).update(**fields)


class Migration(migrations.Migration):
    dependencies = [
        ('services', '0012_service_price_is_from'),
        ('bookings', '0001_initial'),
    ]

    # Reverse is a no-op: the old price list isn't worth restoring over what the salon has edited since
    operations = [
        migrations.RunPython(apply_catalog, migrations.RunPython.noop),
    ]
