# Generated by Django 4.1.4 on 2022-12-15 05:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_demo', '0002_pooldemomodel_remark_alter_pooldemomodel_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pooldemomodel',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]