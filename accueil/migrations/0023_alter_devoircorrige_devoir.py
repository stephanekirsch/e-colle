# Generated by Django 3.2.6 on 2021-08-29 00:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accueil', '0022_auto_20210812_0331'),
    ]

    operations = [
        migrations.AlterField(
            model_name='devoircorrige',
            name='devoir',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='corriges', to='accueil.devoir'),
        ),
    ]
