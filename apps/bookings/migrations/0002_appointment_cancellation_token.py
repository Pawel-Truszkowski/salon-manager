import uuid

from django.db import migrations, models


def generate_cancellation_tokens(apps, schema_editor):
    Appointment = apps.get_model('bookings', 'Appointment')
    for appointment in Appointment.objects.all():
        appointment.cancellation_token = uuid.uuid4()
        appointment.save(update_fields=['cancellation_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        # Added as nullable first: a non-nullable field's callable default
        # (uuid.uuid4) is evaluated only once for the ADD COLUMN statement,
        # which would give every existing row the same token and violate
        # the unique constraint added in the final step below.
        migrations.AddField(
            model_name='appointment',
            name='cancellation_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(generate_cancellation_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='appointment',
            name='cancellation_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
