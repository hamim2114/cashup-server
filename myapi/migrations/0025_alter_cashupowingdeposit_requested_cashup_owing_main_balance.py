# Generated by Django 5.1.3 on 2025-03-11 18:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapi', '0024_transferhistory_cashup_owing_deposit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashupowingdeposit',
            name='requested_cashup_owing_main_balance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, null=True),
        ),
    ]
