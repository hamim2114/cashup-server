# Generated by Django 5.1.3 on 2025-03-15 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapi', '0040_alter_purchase_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='buyerotp',
            name='expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
