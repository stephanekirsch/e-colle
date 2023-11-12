# Generated by Django 4.2.4 on 2023-09-24 09:17

import accueil.models.contenttype
import accueil.models.devoir
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accueil', '0028_noteglobaleects'),
    ]

    operations = [
        migrations.AddField(
            model_name='td',
            name='corrige',
            field=accueil.models.contenttype.ContentTypeRestrictedFileField(blank=True, null=True, upload_to=accueil.models.devoir.TD.update_name_corrige, verbose_name='Corrigé(pdf)'),
        ),
    ]