# Generated by Django 5.1.3 on 2025-03-11 07:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapi', '0023_alter_withdrawalfromcashupbalance_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transferhistory',
            name='cashup_owing_deposit',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='myapi.cashupowingdeposit'),
        ),
    ]
