from django.core.management.commands.loaddata import Command as Loaddata
from django.core.management.commands.flush import Command as Flush
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS
from ecolle.settings import BACKUP_ROOT, MEDIA_ROOT
import os
import bz2
import tarfile
import subprocess

class Command(BaseCommand):

	def handle(self,*app_labels,**options):
		fichiers_bz2 = sorted([f for f in os.listdir(BACKUP_ROOT) if f[-4:] == ".bz2"])
		if not fichiers_bz2:
			self.stdout.write("""Aucune sauvegarde des données n'est présente,
				impossible de charger des données antérieures""")
		else:
			for num, fichier in zip(range(1,len(fichiers_bz2)+1),fichiers_bz2):
				self.stdout.write("{}: {}".format(num, fichier))
			num = input("Quelle sauvegarde voulez-vous charger? (Taper le numéro ou a pour abandon): ")
			while not (num == "a" or num.isnumeric() and 0 < int(num) <= len(fichiers_bz2)):
				self.stdout.write("numéro inexistant, recommencez")
				num = input("Quelle sauvegarde voulez-vous charger? (Taper le numéro ou a pour abandon): ")
			if num=="a":
				self.stdout.write("abandon")
			else:
				num = int(num)
				fichier = fichiers_bz2[num-1]
				date = fichier.split("_")[1].split(".")[0]
				fichier_media = "ecolle-media_{}.tar.xz".format(date)
				choix="1"
				if os.path.isfile(os.path.join(BACKUP_ROOT,fichier_media)):
					self.stdout.write("""Il existe une sauvegarde des fichiers media associée, que voulez-vous faire?
1. l'ignorer
2. effacer tous les fichiers media existants et mettre ceux de la sauvegarde à la place
3. conserver les fichiers media existants et ajouter en plus ceux de la sauvegarde (en écrasant les doublons)
a. abandonner\n""")
					choix = input()
					while choix not in "a123":
						self.stdout.write("choix invalide, recommencez")
						choix = input()
					if choix == "a":
						self.stdout.write("abandon")
					else:
						if choix == "2":
							repertoires = [os.path.join(MEDIA_ROOT, x) for x in ('programme','image','photos')]
							for repertoire in repertoires:
								for fichiermedia in os.listdir(repertoire):
									if fichiermedia  != ".gitignore":
										os.remove(os.path.join(repertoire,fichiermedia))
						if choix in "23":
							self.stdout.write("Début restauration des fichiers media")
							try:
								archive_zip = tarfile.open(os.path.join(BACKUP_ROOT,fichier_media),"r:xz")
								archive_zip.extractall(MEDIA_ROOT)
								# on redonne les droits au groupe web sur les frichiers retaurés
								try:
									subprocess.run(["chgrp","-R","web",MEDIA_ROOT])
								except Exception:
									self.stdout.write("Problème dans l'attribution des droits des fichiers media")
							except Exception:
								self.stdout.write("Erreur lors de la restauration des fichiers media")
							else:
								self.stdout.write("Restauration des fichiers media terminée")
							finally:
								archive_zip.close()
				if choix != "a":
					# flush de la base de donnée puis loaddata
					self.stdout.write("Début du nettoyage de la base de données.")
					Flush().handle(database = DEFAULT_DB_ALIAS, verbosity=1, interactive=False)
					self.stdout.write("Nettoyage de la base de données terminé.")
					self.stdout.write("début insertion de la sauvegarde dans la base de données.")
					fichier_json = os.path.join(BACKUP_ROOT,'e-colle.json')
					with bz2.open(os.path.join(BACKUP_ROOT,fichier),'rb') as fichier_bz2:
						with open(fichier_json, 'wb') as fichierjson:
							fichierjson.write(bz2.decompress(fichier_bz2.read()))
					try:
						Loaddata().handle(fichier_json, database=DEFAULT_DB_ALIAS, format="json",
							exclude=[], ignore=False, app_label=None, verbosity=1)
					except Exception as e:
						self.stdout.write("Erreur lors de l'insertion des données: {}".format(str(e)))
					else:
						self.stdout.write("Insertion de la sauvegarde dans la base de données terminée.")
					finally:
						os.remove(fichier_json)


