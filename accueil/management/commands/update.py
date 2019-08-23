from django.core.management.base import BaseCommand, CommandError
from .backup import Command as Backup
from ecolle.settings import CHEMINVERSECOLLE
import os
from urllib.request import urlopen
from urllib.error import HTTPError
import tarfile
import subprocess
from shutil import rmtree, copy as filecopy

class Command(BaseCommand):
    help = """mise à jour de e-colle"""

    def clean(self):
        """nettoie dans le cas d'un échec"""
        directory = os.path.join("..","e-colle-new")
        if os.path.isdir(directory):
            rmtree(directory, True)
        reps = [f for f in os.listdir("..") if os.path.isdir(f) and f.startswith("stephanekirsch-e-colle")]
        if len(reps) > 0:
            for rep in reps:
                rmtree(os.path.join("..",rep))
        if os.path.isfile(os.path.join("..","e-colle.tar.gz")):
            os.remove(os.path.join("..","e-colle.tar.gz"))

    def add_arguments(self, parser):
        parser.add_argument('version', nargs=1 , type=str)

    def handle(self, *args, **options):
        try:
            version = options.pop('version')[0]
            url = "https://github.com/stephanekirsch/e-colle/tarball/" + version
            try:
                with urlopen(url) as fichier, open(os.path.join("..","e-colle.tar.gz"),"wb") as fichier_zip:
                    self.stdout.write("téléchargement de la version {} de e-colle".format(version))
                    self.stdout.write("progression: 0.0%",ending="\r")
                    taille = fichier.getheader('Content-Length')
                    taille = int(taille) if taille is not None else 3000000
                    taille = int(taille)
                    CHUNK = 32*1024
                    progress = 0
                    efface = 4
                    while True:
                        chunk = fichier.read(CHUNK)
                        if not chunk:
                            break
                        else:
                            progress += CHUNK
                            progress = min(taille,progress)
                            pourcent = "progression: {:.2f}%".format(100*progress/taille)
                            self.stdout.write(pourcent, ending="\r")
                            fichier_zip.write(chunk)
                    self.stdout.write("\ntéléchargement terminé")
            except HTTPError:
                raise CommandError("la version précisée: {} n'existe pas".format(version))
            # décompression du fichier zip
            archive_zip = tarfile.open(os.path.join("..","e-colle.tar.gz"),"r:gz")
            archive_zip.extractall("..")
            # on renomme le nouveau e-colle
            reps = [f for f in os.listdir("..") if not os.path.isfile(f) and f.startswith("stephanekirsch-e-colle")]
            os.rename(os.path.join("..",reps[0]),os.path.join("..","e-colle-new"))
            # on récupère les données de config de l'ancien e-colle pour les passer au nouveau.
            self.stdout.write("copie des données de configuration")
            from ecolle.settings import DEFAULT_ADMIN_PASSWD, DEFAULT_SECRETARIAT_PASSWD, EMAIL_ADMIN, EMAIL_SECRETARIAT, IP_FILTRE_ADMIN,\
            IP_FILTRE_ADRESSES, DATABASES, BDD, IMAGEMAGICK, ALLOWED_HOSTS, INTERNAL_IPS, SECRET_KEY, TIME_ZONE, HEURE_DEBUT, HEURE_FIN, INTERVALLE
            db = DATABASES["default"]
            with open(os.path.join("..","e-colle-new","ecolle","config.py"),"wt",encoding="utf8") as fichier:
                    fichier.write("DEFAULT_ADMIN_PASSWD = '{}' # mot de passe de l'utilisateur administrateur\n".format(DEFAULT_ADMIN_PASSWD))
                    fichier.write("DEFAULT_SECRETARIAT_PASSWD = '{}' # mot de passe de l'utilisateur secrétariat\n".format(DEFAULT_SECRETARIAT_PASSWD))
                    fichier.write("EMAIL_ADMIN = '{}' # email de l'utilisateur administateur\n".format(EMAIL_ADMIN))
                    fichier.write("EMAIL_SECRETARIAT = '{}' # email de l'utilisateur secrétariat\n".format(EMAIL_SECRETARIAT))
                    fichier.write("IP_FILTRE_ADMIN = {} # filtrage IP pour l'utilisateur administrateur\n".format(IP_FILTRE_ADMIN))
                    fichier.write("IP_FILTRE_ADRESSES = (")
                    taille = len(IP_FILTRE_ADRESSES)
                    ip_filtre_adresses = ",".join("'" + ip + "'" for ip in IP_FILTRE_ADRESSES)
                    if taille == 1:
                        ip_filtre_adresses += ","
                    fichier.write(ip_filtre_adresses)
                    fichier.write(") # si IP_FILTER_ADMIN vaut True, liste des IPS autorisées pour l'utilisateur admin (REGEXP)\n")
                    fichier.write("DB_ENGINE = '{}' # base de données (mysql ou postgresql ou sqlite3)\n".format(BDD))
                    fichier.write("DB_USER = '{}' # nom de l'utilisateur qui a les droits sur la base de données\n".format(db['USER']))
                    fichier.write("DB_NAME = '{}' # nom de la base de données (ou du fichier .db pour SQLite)\n".format(db['NAME']))
                    fichier.write("DB_PASSWORD = '{}' # mot de passe pour se connecter à la base de données\n".format(db['PASSWORD']))
                    fichier.write("DB_HOST = '{}' # adresse locale de la base de données\n".format(db['HOST']))
                    fichier.write("DB_PORT = '{}' # port de la BDD, vide par défaut. À renseigner si la BDD se trouve sur un port particulier\n".format(db['PORT']))
                    fichier.write("IMAGEMAGICK = {} # utilisation de ImageMagick pour faire des miniatures de la première page des pdf programmes de colle\n".format(IMAGEMAGICK ))
                    fichier.write("ALLOWED_HOSTS = {} # liste des noms de domaine autorisés pour accéder à e-colle\n".format(ALLOWED_HOSTS))
                    fichier.write("INTERNAL_IPS = {} # liste des IP autorisées pour accéder en interne à e-colle quand debug est True\n".format(INTERNAL_IPS))
                    fichier.write("SECRET_KEY = '{}' # clé secrète aléatoire de 50 caractères\n".format(SECRET_KEY))
                    fichier.write("TIME_ZONE = '{}' # fuseau horaire\n".format(TIME_ZONE))
                    fichier.write("HEURE_DEBUT = {} # heure de début des colles (en minutes depuis minuit)\n".format(HEURE_DEBUT))
                    fichier.write("HEURE_FIN = {} # heure de fin des colles (en minutes depuis minuit)\n".format(HEURE_FIN))
                    fichier.write("INTERVALLE = {} # intervalle entre 2 créneaux (en minutes)".format(INTERVALLE))
            self.stdout.write("copie terminée")
            self.stdout.write("sauvegarde de la base de données pour avoir un point de sauvegarde en cas d'échec de la mise à jour")
            try:
                backup = Backup()
                backup.handle(backup_media = False, **options)
            except Exception as e:
                self.stdout.write("Échec de la sauvegarde de la base de données:")
                self.stdout.write(str(e))
                self.stdout.write("La sauvegarde a échoué, voulez-vous poursuivre?")
                poursuite = input("Attention si la mise à jour échoue vous risquez de ne pas pouvoir revenir en arrière (o/N)")
                if poursuite != "" and poursuite in "oO":
                    poursuite = True
                else:
                    poursuite = False
            else:
                poursuite = True
            if poursuite: # si la sauvegarde de la base de données a réussi ou si on s'en passe, on met à jour la migration
                self.stdout.write("Mise à jour de la structure de la base de données")
                chemin = os.path.join("..","e-colle-new","manage.py")
                subprocess.run(["python3",chemin,"migrate"])
                # on copie les fichiers media/backup:
                self.stdout.write("copie des fichiers media/backup")
                repertoires = ['programme','image','photos']
                for rep in repertoires:
                    source = os.path.join("media",rep)
                    target = os.path.join("..","e-colle-new","media",rep)
                    for file in os.listdir(source):
                        filecopy(os.path.join(source,file),target)
                source = "backup"
                target = os.path.join("..","e-colle-new","backup")
                for file in os.listdir(source):
                    filecopy(os.path.join(source,file),target)
                # on renomme e-colle-bak l'ancien réperoire et e-colle le nouveau
                os.rename(os.path.join("..","e-colle"),os.path.join("..","e-colle-bak"))
                os.rename(os.path.join("..","e-colle-new"),os.path.join("..","e-colle"))
        except Exception as e:
            self.stdout.write(str(e))
            self.stdout.write("la mise à jour n'a pas pu aller jusqu'au bout. Si la migration a eu lieu,\n\
                et que e-colle ne fonctionne plus à cause de la base de données\n\
                il est recommandé d'effacer le répertoire 'e-colle',\n\
                renommer 'e-colle' le répertoire 'e-colle-bak', effacer la base de données,\n\
                la recréer et d'utiliser les commandes migrate et restore.")
        else:
            self.stdout.write("la mise a jour a été effectuée avec succès.\n\
                l'ancien répertoire e-colle s'appelle désormais e-colle-bak\n\
                Si jamais ça ne fonctionne pas, vous pouvez revenir à l'état précédent\n\
                en effaçant le répertoire 'e-colle', renommant 'e-colle' le répertoire 'e-colle-bak'\n\
                effaçant la base de données, la recréer et utiliser les commandes migrate et restore\n\
                Pour que les modifications soient prises en compte en production,\n\
                il faut redémarrer le logiciel serveur.")
        finally:
            self.stdout.write("nettoyage")
            self.clean()






    

