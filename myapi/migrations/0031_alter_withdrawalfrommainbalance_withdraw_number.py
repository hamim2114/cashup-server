# Generated by Django 5.1.3 on 2025-03-13 10:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapi', '0030_withdrawalfrommainbalance_method_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='withdrawalfrommainbalance',
            name='withdraw_number',
            field=models.CharField(max_length=20),
        ),
    ]
