# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.conf import settings
from django.contrib.auth.hashers import make_password

def initial_accounts(apps, schema_editor):
    """Exécute la création des utilisateurs admin et Secrétariat s'ils n'existent pas déjà"""
    User = apps.get_model(settings.AUTH_USER_MODEL)

    admin = User.objects.filter(username="admin")
    if not admin.exists():
        admin = User(username="admin", email=settings.EMAIL_ADMIN, last_name="Administrateur",
                password=make_password(settings.DEFAULT_ADMIN_PASSWD))
        admin.save()

    secret = User.objects.filter(username="Secrétariat")
    if not secret.exists():
        secret = User(username="Secrétariat", email=settings.EMAIL_SECRETARIAT, last_name="Secrétariat",
                password=make_password(settings.DEFAULT_SECRETARIAT_PASSWD))
        secret.save()

class Migration(migrations.Migration):

    dependencies = [
        ('accueil', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(initial_accounts),
    ]
