# -*- coding: utf-8 -*-
from django.db import migrations
from django.conf import settings
from django.contrib.auth.hashers import make_password

def initial_accounts(apps, schema_editor):
    """met à jour l'Attribut css de l'Admin et du secrétariat
    (il n'existe pas encore dans la migration à la création de
    ces utilisateurs)"""
    User = apps.get_model("accueil", "User")

    User.objects.filter(username="admin").update(css=settings.DEFAULT_CSS)
    User.objects.filter(username="Secrétariat").update(css=settings.DEFAULT_CSS)

class Migration(migrations.Migration):

    dependencies = [
        ('accueil', '0009_auto_20181220_1147'),
    ]

    operations = [
        migrations.RunPython(initial_accounts),
    ]
