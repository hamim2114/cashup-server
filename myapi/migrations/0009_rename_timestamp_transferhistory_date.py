# Generated by Django 5.1.3 on 2025-03-09 17:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapi', '0008_remove_transferhistory_method'),
    ]

    operations = [
        migrations.RenameField(
            model_name='transferhistory',
            old_name='timestamp',
            new_name='date',
        ),
    ]
