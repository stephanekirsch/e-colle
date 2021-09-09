from django.core.management.commands.dumpdata import Command as ReinitPasswd
from django.db import DEFAULT_DB_ALIAS
from ecolle.settings import BACKUP_ROOT, MEDIA_ROOT, AUTH_PASSWORD_VALIDATORS
from accueil.models import User
from django.contrib.auth.password_validation import validate_password, ValidationError, get_password_validators
import os
import tarfile
import bz2
import datetime
import getpass
import importlib

class Command(ReinitPasswd):
    help = """réiinitialise les mots de passe admin et / ou secrétariat, en recréant au besoin au préalable 
    les utilisateurs admin et / ou secértariat"""

    def handle(self,*app_labels,**options):
        choix = input("voulez-vous réinitialiser les mot de passe Administrateur (a), Secrétariat (s), les 2 (as) ou quitter (q)?")
        correct = False
        if 'a' in choix:
            while not correct:
                pwd1 = getpass.getpass("Entrez le nouveau mot de passe admin: ")
                pwd2 = getpass.getpass("Entrez de nouveau  le nouveau mot de passe admin: ")
                if pwd1 != pwd2:
                    print("les 2 mots de passe ne coïncident pas, veuillez recommencer")
                else:
                    if not User.objects.filter(username="admin").exists():
                        admin = User(username="admin", email=settings.EMAIL_ADMIN, last_name="Administrateur", 
                    password=make_password(settings.DEFAULT_ADMIN_PASSWD))
                    else:
                        admin = User.objects.get(username="admin")
                    try:
                        validate_password(pwd1, admin, get_password_validators(AUTH_PASSWORD_VALIDATORS))
                    except ValidationError as e:
                        for truc in e:
                            print(truc)
                        print("Veuillez choisir un autre mot de passe")
                    else:
                        correct = True
                        print("Le mot de passe administrateur a bien été mis à jour")
                        admin.set_password(pwd1)
                        admin.save()
        if 's' in choix:
            while not correct:
                pwd1 = getpass.getpass("Entrez le nouveau mot de passe secrétariat: ")
                pwd2 = getpass.getpass("Entrez de nouveau  le nouveau mot de passe secrétariat: ")
                if pwd1 != pwd2:
                    print("les 2 mots de passe ne coïncident pas, veuillez recommencer")
                else:
                    if not User.objects.filter(username="Secrétariat").exists():
                        secret = User(username="Secrétariat", email=settings.EMAIL_SECRETARIAT, last_name="Administrateur", 
                    password=make_password(settings.DEFAULT_SECRETARIAT_PASSWD))
                    else:
                        secret = User.objects.get(username="Secrétariat")
                    try:
                        validate_password(pwd1, secret, get_password_validators(AUTH_PASSWORD_VALIDATORS))
                    except ValidationError as e:
                        for truc in e:
                            print(truc)
                        print("Veuillez choisir un autre mot de passe")
                    else:
                        correct = True
                        print("Le mot de passe secrétariat a bien été mis à jour")
                        secret.set_password(pwd1)
                        secret.save()