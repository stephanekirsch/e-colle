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
            cwd = os.path.split(os.getcwd())[1]
            cwd_new = "e-colle-new"
            cwd_bak = "{}-bak".format(cwd)
            reps = [f for f in os.listdir("..") if not os.path.isfile(f) and f.startswith("stephanekirsch-e-colle")]
            os.rename(os.path.join("..",reps[0]),os.path.join("..",cwd_new))
            # on récupère les données de config de l'ancien e-colle pour les passer au nouveau.
            self.stdout.write("copie des données de configuration")
            import ecolle.config as old_config
            vars = [x for x in dir(old_config) if x[:2] != "__"]
            vardict = {s:getattr(old_config,s) for s in vars}
            with open(os.path.join("..",cwd_new,"ecolle","config.py"),"wt",encoding="utf8") as fichier:
                for key, value in vardict.items():
                    if type(value) is str:
                        fichier.write("{} = '{}'\n".format(key,value))
                    else:
                        fichier.write("{} = {}\n".format(key,value))
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
                os.chdir(os.path.join("..",cwd_new))
                subprocess.run(["pip3","install", "-r","requirements.txt"]) # on installe les éventuelles bilbiothèques manquantes
                subprocess.run(["python3","manage.py","migrate"])
                # on copie les fichiers media/backup:
                self.stdout.write("copie des fichiers media/backup")
                repertoires = os.listdir("media")
                repertoires = [os.path.join("media", file) for file in repertoires]
                repertoires = [d for d in repertoires if os.path.isdir(d)]
                for rep in repertoires:
                    source = os.path.join("media",rep)
                    target = os.path.join("..",cwd_new,"media",rep)
                    for file in os.listdir(source):
                        filecopy(os.path.join(source,file),target)
                source = "backup"
                target = os.path.join("..",cwd_new,"backup")
                for file in os.listdir(source):
                    filecopy(os.path.join(source,file),target)
                # on renomme e-colle-bak l'ancien réperoire et e-colle le nouveau
                os.rename(os.path.join("..",cwd),os.path.join("..",cwd_bak))
                os.rename(os.path.join("..",cwd_new),os.path.join("..",cwd))
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






    

