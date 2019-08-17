from django.core.management.base import BaseCommand
from django.db import connection, transaction
from ecolle.settings import BDD, MEDIA_ROOT
import os
 
class Command(BaseCommand):
    help = """prépare la base de donnée pour une nouvelle année:
    efface les messages, les notes, les colles, les semaines etc ....
    conserve les classes/colleurs/eleves/matières/établissements.
    Cela effaca aussi tous les fichiers
    Il est conseillé de faire une sauvegarde de la base de donnée
    avant de lancer cette commande"""

    def handle(self, *args, **options):
        if input("Êtes-vous sûr de vouloir réinitialiser la base de données? (o/n): ").lower() == "o":
            self.stdout.write("lancement de la réinitialisation")
            with connection.cursor() as cursor:
                try:
                    if BDD in ("postgresql","postgresql_pyscopg2"):
                        # on vide les tables en question et on redémarre les ids à 1. 
                        cursor.execute("TRUNCATE accueil_colle,\
                            accueil_creneau,\
                            accueil_decompte,\
                            accueil_destinataire,\
                            accueil_jourferie,\
                            accueil_message,\
                            accueil_note,\
                            accueil_noteects,\
                            accueil_programme,\
                            accueil_programme_semaine,\
                            accueil_ramassage,\
                            accueil_semaine,\
                            django_session\
                            RESTART IDENTITY;")
                        cursor.execute("VACUUM;")
                    elif BDD == "mysql":
                        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;\
                            TRUNCATE TABLE accueil_colle;\
                            TRUNCATE TABLE accueil_creneau;\
                            TRUNCATE TABLE accueil_decompte;\
                            TRUNCATE TABLE accueil_destinataire;\
                            TRUNCATE TABLE accueil_jourferie;\
                            TRUNCATE TABLE accueil_message;\
                            TRUNCATE TABLE accueil_note;\
                            TRUNCATE TABLE accueil_noteects;\
                            TRUNCATE TABLE accueil_programme;\
                            TRUNCATE TABLE accueil_programme_semaine,\
                            TRUNCATE TABLE accueil_ramassage;\
                            TRUNCATE TABLE accueil_semaine;\
                            TRUNCATE TABLE django_session;\
                            SET FOREIGN_KEY_CHECKS = 1;")
                    else: # cas SQLite
                        with transaction.atomic():
                            cursor.execute("DELETE FROM accueil_colle;")
                            cursor.execute("DELETE FROM accueil_creneau;")
                            cursor.execute("DELETE FROM accueil_decompte;")
                            cursor.execute("DELETE FROM accueil_destinataire;")
                            cursor.execute("DELETE FROM accueil_jourferie;")
                            cursor.execute("DELETE FROM accueil_jourferie;")
                            cursor.execute("DELETE FROM accueil_message;")
                            cursor.execute("DELETE FROM accueil_note;")
                            cursor.execute("DELETE FROM accueil_noteects;")
                            cursor.execute("DELETE FROM accueil_programme;")
                            cursor.execute("DELETE FROM accueil_programme_semaine;")
                            cursor.execute("DELETE FROM accueil_ramassage;")
                            cursor.execute("DELETE FROM accueil_semaine;")
                            cursor.execute("DELETE FROM django_session;")
                        cursor.execute("VACUUM;")
                except Exception as e:
                    self.stdout.write("La réinitialisation a échoué: {}".format(e))
                else:
                    repertoire = os.path.join(MEDIA_ROOT,'programme')
                    try:
                        for fichier in os.listdir(repertoire):
                            if fichier != ".gitignore":
                                os.remove(os.path.join(repertoire,fichier))
                    except Exception:
                        self.stdout.write("Les fichiers programmes n'ont pas pu tous être effacés,\
                            videz le répertoire media/programme à la main.")
                    repertoire = os.path.join(MEDIA_ROOT,'image')
                    try:
                        for fichier in os.listdir(repertoire):
                            if fichier != ".gitignore":
                                os.remove(os.path.join(repertoire,fichier))
                    except Exception:
                        self.stdout.write("Les fichiers image n'ont pas pu tous être effacés,\
                            videz le répertoire media/image à la main.")
                    self.stdout.write("Réinitialisation complète")
        else:
            self.stdout.write("abandon")
