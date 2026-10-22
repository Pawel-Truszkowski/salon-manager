import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('services', '0013_catalog'),
    ]

    # Existing services get the migration time: the price list was last changed by 0013_catalog anyway
    operations = [
        migrations.AddField(
            model_name='service',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
