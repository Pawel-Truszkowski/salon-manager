from django.db import migrations

LASER = {
    'name': 'LightSheer DUET',
    'description': 'Laser diodowy LightSheer DUET firmy Lumenis do trwałej redukcji owłosienia.',
}
# Last in the price list (after waxing, see 0009); the price list hides it until it has services
CATEGORY = {'slug': 'depilacja-laserowa', 'name': 'Depilacja laserowa', 'order': 50}


def add_laser(apps, schema_editor):
    Equipment = apps.get_model('services', 'Equipment')
    ServiceCategory = apps.get_model('services', 'ServiceCategory')
    Equipment.objects.get_or_create(name=LASER['name'], defaults={'description': LASER['description']})
    # Name and slug are both unique: an existing category with either one (e.g. added by hand) is kept as is
    if not ServiceCategory.objects.filter(slug=CATEGORY['slug']).exists() and not (
        ServiceCategory.objects.filter(name=CATEGORY['name']).exists()
    ):
        ServiceCategory.objects.create(**CATEGORY)


class Migration(migrations.Migration):
    dependencies = [
        ('services', '0010_equipment'),
    ]

    # Reverse is a no-op: by then the laser may have rentals and services that must not vanish with a rollback
    operations = [
        migrations.RunPython(add_laser, migrations.RunPython.noop),
    ]
