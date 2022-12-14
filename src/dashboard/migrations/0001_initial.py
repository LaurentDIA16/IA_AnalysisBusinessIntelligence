# Generated by Django 3.1.7 on 2022-12-11 10:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('country', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('zone', models.CharField(blank=True, max_length=50, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Datatransfert',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoiceno', models.CharField(max_length=7)),
                ('stockcode', models.CharField(max_length=50)),
                ('description', models.CharField(blank=True, max_length=80, null=True)),
                ('quantity', models.IntegerField()),
                ('invoicedate', models.CharField(max_length=25)),
                ('unitprice', models.DecimalField(decimal_places=2, max_digits=8)),
                ('customerid', models.DecimalField(blank=True, decimal_places=1, max_digits=8, null=True)),
                ('country', models.CharField(max_length=50)),
                ('totalcost', models.DecimalField(blank=True, decimal_places=2, default='0', max_digits=8, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('stockcode', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('description', models.CharField(blank=True, max_length=80, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('invoiceno', models.CharField(max_length=7, primary_key=True, serialize=False)),
                ('invoicedate', models.CharField(blank=True, max_length=25, null=True)),
                ('customerid', models.DecimalField(blank=True, decimal_places=1, max_digits=8, null=True)),
                ('country', models.ForeignKey(db_column='country', on_delete=django.db.models.deletion.DO_NOTHING, to='dashboard.country')),
            ],
        ),
        migrations.CreateModel(
            name='DetailInvoice',
            fields=[
                ('unitprice', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('quantity', models.DecimalField(decimal_places=0, max_digits=8)),
                ('totalcost', models.DecimalField(blank=True, decimal_places=2, default='0', max_digits=8, null=True)),
                ('detailInvoice_id', models.AutoField(primary_key=True, serialize=False)),
                ('invoiceno', models.ForeignKey(blank=True, db_column='invoiceno', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='dashboard.invoice')),
                ('stockcode', models.ForeignKey(blank=True, db_column='stockcode', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='dashboard.product')),
            ],
        ),
    ]
