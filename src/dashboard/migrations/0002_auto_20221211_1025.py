# Generated by Django 3.1.7 on 2022-12-11 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datatransfert',
            name='quantity',
            field=models.DecimalField(decimal_places=0, max_digits=8),
        ),
    ]