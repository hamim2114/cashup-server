# Generated by Django 5.1.3 on 2025-03-10 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapi', '0021_alter_cashupowingprofithistory_change_timestamp_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transferhistory',
            name='verified',
            field=models.BooleanField(default=False),
        ),
    ]
