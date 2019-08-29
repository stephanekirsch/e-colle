from django.core.management.base import BaseCommand
from ecolle.settings import CHEMINVERSECOLLE
import os
import re
from random import choice
from ecolle.config import *
from ecolle.settings import DATABASES, BDD

def texte_aleatoire(taille):
    return "".join(choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+@()!-&") for i in range(taille))

class Command(BaseCommand):
    help = """ré-initialise les données du fichier config.py"""

    def handle(self, *args, **options):
        DB_ENGINE = BDD
        DB_NAME = DATABASES['default']['NAME']
        DB_USER = DATABASES['default']['USER']
        nomfichier = os.path.join(CHEMINVERSECOLLE,"ecolle","config.py")
        self.stdout.write("Ré-initialisation des données:\n\
            pour chaque donnée, appuyez sur entrée\n\
            pour conserver l'ancienne valeur entre parenthèses")
        self.stdout.write("-"*20)
        default_admin_passwd = input("Mot de passe initial de l'utilisateur administrateur ({}): ".format(DEFAULT_ADMIN_PASSWD))
        self.stdout.write("-"*20)
        default_secretariat_passwd = input("Mot de passe initial de l'utilisateur secrétariat ({}): ".format(DEFAULT_SECRETARIAT_PASSWD))
        self.stdout.write("-"*20)
        prog = re.compile("(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")
        loop = True
        while loop:
            email_admin = input("Email de l'utilisateur administrateur, peut être laissé vide en validant un espace({}): ".format(EMAIL_ADMIN))
            if email_admin in " " or prog.match(email_admin):
                loop = False
            else:
                self.stdout.write("email invalide")
        self.stdout.write("-"*20)
        loop = True
        while loop:
            email_secretariat = input("Email de l'utilisateur secrétariat, peut être laissé vide en validant un espace({}): ".format(EMAIL_SECRETARIAT))
            if email_secretariat in " " or prog.match(email_secretariat):
                loop = False
            else:
                self.stdout.write("email invalide")
        self.stdout.write("-"*20)
        loop = True
        while loop:
            ip_filtre_admin = input("restreindre la partie administrateur à certaines adresses IP? O/N ({}): ".format("O" if IP_FILTRE_ADMIN else "N"))
            if ip_filtre_admin in "oOnN":
                loop = False
            else:
                self.stdout.write("réponse invalide")
        self.stdout.write("-"*20)
        if ip_filtre_admin == "o" or ip_filtre_admin == "O" or ip_filtre_admin == "" and IP_FILTRE_ADMIN is True:
            ip_filtre_adresses = input("liste des REGEXP des adresses IP de l'utilisateur administrateur,\n\
                séparer par des virgules, peut être laissé vide en validant un espace (" + ",".join("'" + x + "'" for x in IP_FILTRE_ADRESSES) + "): ").split(",")
        else:
            ip_filtre_adresses = ""
        self.stdout.write("-"*20)
        loop = True
        while loop:
            sgbd_dict = {'1':"postgresql",'2':"mysql",'3':"sqlite3"}
            db_engine = input("SGBD à utiliser, " + ",".join(" {}:{}".format(value,key) for key,value in sgbd_dict.items()) + " ({}): ".format(DB_ENGINE))
            if db_engine in "123":
                loop = False
            else:
                self.stdout.write("réponse invalide")
        self.stdout.write("-"*20)
        db_user = input("nom de l'utilisateur de la base de données ({}): ".format(DB_USER))
        self.stdout.write("-"*20)
        db_name = input("nom de la base de données ({}): ".format(DB_NAME))
        self.stdout.write("-"*20)
        db_password = input("mot de passe pour se connecter à la base de données\n\
            Attention, si le mot de passe est déjà défini il est fortement conseillé\n\
            de le conserver. Tapez 'a' pour générer un mot de passe aléatoire ({}): ".format(DB_PASSWORD))
        self.stdout.write("-"*20)
        db_host = input("adresse locale de la base de données ({}): ".format(DB_HOST))
        self.stdout.write("-"*20)
        db_port = input("port de la base de données, vide par défaut\n\
        peut être laissé vide en validant un espace ({}): ".format(DB_PORT))
        self.stdout.write("-"*20)
        loop = True
        while loop:
            imagemagick = input("Utiliser ImageMagick pour convertir les pdf des programmes en images? O/N ({}): ".format("O" if IMAGEMAGICK else "N"))
            if imagemagick in "oOnN":
                loop = False
            else:
                self.stdout.write("réponse invalide")
        self.stdout.write("-"*20)
        allowed_hosts = input("liste noms de domaine autorisés pour accéder à e-colle,\n\
         séparer par des virgules, peut être laissé vide en validant un espace ({}): ".format(ALLOWED_HOSTS)).split(",")
        self.stdout.write("-"*20)
        loop = True
        pat = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
        while loop:
            internal_ips = input("liste des adresses IP autorisées pour un accès interne à e-colle\n\
                , peut être laissé vide en validant un espace ({}): ".format(INTERNAL_IPS)).split(",")
            if internal_ips == [" "] or internal_ips == [""] or all(pat.match(ip) for ip in internal_ips):
                loop = False
            else:
                self.stdout.write("au moins une des adresses ip est invalide")
        self.stdout.write("-"*20)
        loop = True
        while loop:
            secret_key = input("Générer une nouvelle clé secrète? O/N (N): ")
            if secret_key in "oOnN":
                loop = False
            else:
                self.stdout.write("réponse invalide")
        self.stdout.write("-"*20)
        timezonedict = {'1':'Europe/Paris', '2':'America/Cayenne', '3':'America/Guadeloupe', '4':'America/Martinique', '5':'Indian/Reunion','6':'Pacific/Noumea', '7':'Pacific/Tahiti'}
        time_zone = input("fuseau horaire," + ",".join(" {}:{}".format(value,key) for key,value in timezonedict.items()) + " ({}): ".format(TIME_ZONE))
        self.stdout.write("-"*20)
        loop = True
        while loop:
            heure_debut = input("heure de début des colles en minutes depuis minuit ({}): ".format(HEURE_DEBUT))
            try:
                heure_debut = HEURE_DEBUT if heure_debut == "" else int(heure_debut)
                loop = False
            except Exception:
                self.stdout.write("réponse invalide")
        self.stdout.write("-"*20)
        loop = True
        while loop:
            heure_fin = input("heure de fin des colles en minutes depuis minuit ({}): ".format(HEURE_FIN))
            try:
                heure_fin = HEURE_FIN if heure_fin == "" else int(heure_fin)
                loop = False
            except Exception:
                self.stdout.write("réponse invalide")
        self.stdout.write("-"*20)
        loop = True
        while loop:
            intervalle = input("intervalle entre 2 créneaux en minutes ({}): ".format(INTERVALLE))
            try:
                intervalle = INTERVALLE if intervalle == "" else int(intervalle)
                loop = False
            except Exception:
                self.stdout.write("réponse invalide")
        self.stdout.write("-"*20)
        # fin entrée des données
        # écriture dans le fichier config.py
        try:
            with open(nomfichier,"wt",encoding="utf8") as fichier:
                fichier.write("DEFAULT_ADMIN_PASSWD = '{}' # mot de passe de l'utilisateur administrateur\n"\
                    .format(DEFAULT_ADMIN_PASSWD if default_admin_passwd =="" else default_admin_passwd.strip()))
                fichier.write("DEFAULT_SECRETARIAT_PASSWD = '{}' # mot de passe de l'utilisateur secrétariat\n"\
                    .format(DEFAULT_SECRETARIAT_PASSWD if default_secretariat_passwd =="" else default_secretariat_passwd.strip()))
                fichier.write("EMAIL_ADMIN = '{}' # email de l'utilisateur administateur\n"\
                    .format(EMAIL_ADMIN if email_admin =="" else email_admin))
                fichier.write("EMAIL_SECRETARIAT = '{}' # email de l'utilisateur secrétariat\n"\
                    .format(EMAIL_SECRETARIAT if email_secretariat =="" else email_secretariat))
                fichier.write("IP_FILTRE_ADMIN = {} # filtrage IP pour l'utilisateur administrateur\n"\
                    .format(IP_FILTRE_ADMIN if ip_filtre_admin == "" else ip_filtre_admin.lower() == "o"))
                if ip_filtre_adresses == [""]:
                    ip_filtre_adresses = ",".join("'" + ip + "'" for ip in IP_FILTRE_ADRESSES)
                    if len(IP_FILTRE_ADRESSES) == 1:
                        ip_filtre_adresses += ","
                elif ip_filtre_adresses == [" "]:
                    ip_filtre_adresses = ""
                else:
                    taille = len(ip_filtre_adresses)
                    ip_filtre_adresses = ",".join(ip for ip in ip_filtre_adresses)
                    if taille == 1:
                        ip_filtre_adresses += ","
                fichier.write("IP_FILTRE_ADRESSES = (")
                fichier.write(ip_filtre_adresses)
                fichier.write(") # si IP_FILTER_ADMIN vaut True, liste des IPS autorisées pour l'utilisateur admin (REGEXP)\n")
                fichier.write("DB_ENGINE = '{}' # base de données (mysql ou postgresql ou sqlite3)\n"\
                    .format(DB_ENGINE if db_engine == "" else sgbd_dict[db_engine]))
                fichier.write("DB_USER = '{}' # nom de l'utilisateur qui a les droits sur la base de données\n"\
                    .format(DB_USER if db_user =="" else db_user))
                fichier.write("DB_NAME = '{}' # nom de la base de données (ou du fichier .db pour SQLite)\n"\
                    .format(DB_NAME if db_name =="" else db_name))
                fichier.write("DB_PASSWORD = '{}' # mot de passe pour se connecter à la base de données\n"\
                    .format(DB_PASSWORD if db_password == "" else ( texte_aleatoire(30) if db_password.strip().lower() =="a" else db_password.strip())))
                fichier.write("DB_HOST = '{}' # adresse locale de la base de données\n"\
                    .format(DB_HOST if db_host == "" else ("" if db_host == " " else db_host)))
                fichier.write("DB_PORT = '{}' # port de la BDD, vide par défaut. À renseigner si la BDD se trouve sur un port particulier\n"\
                    .format(DB_PORT if db_port == "" else ("" if db_port == " " else db_port)))
                fichier.write("IMAGEMAGICK = {} # utilisation de ImageMagick pour faire des miniatures de la première page des pdf programmes de colle\n"\
                    .format(IMAGEMAGICK if imagemagick == "" else imagemagick.lower() == "o"))
                fichier.write("ALLOWED_HOSTS = {} # liste des noms de domaine autorisés pour accéder à e-colle\n"\
                    .format(ALLOWED_HOSTS if allowed_hosts == [""] else ("[]" if allowed_hosts == [" "] else [x.strip() for x in allowed_hosts])))
                fichier.write("INTERNAL_IPS = {} # liste des IP autorisées pour accéder en interne à e-colle quand debug est True\n"\
                    .format(INTERNAL_IPS if internal_ips == [""] else ("[]" if internal_ips == [" "] else list(internal_ips))))
                fichier.write("SECRET_KEY = '{}' # clé secrète aléatoire de 50 caractères\n"\
                    .format(SECRET_KEY if secret_key in "nN" else texte_aleatoire(50)))
                fichier.write("TIME_ZONE = '{}' # fuseau horaire\n"\
                    .format(TIME_ZONE if time_zone == "" else timezonedict[time_zone]))
                fichier.write("HEURE_DEBUT = {} # heure de début des colles (en minutes depuis minuit)\n"\
                    .format(HEURE_DEBUT if heure_debut == "" else heure_debut))
                fichier.write("HEURE_FIN = {} # heure de fin des colles (en minutes depuis minuit)\n"\
                    .format(HEURE_FIN if heure_fin == "" else heure_fin))
                fichier.write("INTERVALLE = {} # intervalle entre 2 créneaux (en minutes)"\
                    .format(INTERVALLE if intervalle == "" else intervalle))
        except Exception as e:
            print(e)
            self.stdout.write("erreur lors de la modification du fichier config.py\n\
                Vous devrez le remplir à la main")
        else:
            self.stdout.write("mise à jout du fichier config.py réalisée avec succès")



        