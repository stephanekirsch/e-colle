from django.core.management.commands.dumpdata import Command as Backup
from django.db import DEFAULT_DB_ALIAS
from ecolle.settings import BACKUP_ROOT, MEDIA_ROOT
import os
import tarfile
import bz2
import datetime

class Command(Backup):

    def add_arguments(self, parser):
        parser.add_argument(
            '-m', '--media', action='store_true', dest='backup_media',
            help="""include media files in the backup,
            which can increase drastically the size disk space required""")

    def handle(self,*app_labels,**options):
        backup_media = options['backup_media']
        output = os.path.join(BACKUP_ROOT,'ecolle.json')
        bz2_output = os.path.join(BACKUP_ROOT,'ecolle_{}.json.bz2'.format(datetime.date.today().isoformat()))
        media_output = os.path.join(BACKUP_ROOT,'ecolle-media_{}.tar.xz'.format(datetime.date.today().isoformat()))
        self.stdout.write("Début de la sauvegarde de la base de donnée")
        super().handle(exclude=['auth' ,'contenttypes','sessions'], format='json',
            verbosity=1, indent=2, database=DEFAULT_DB_ALIAS, traceback=True,
            use_natural_foreign_keys=False, use_natural_primary_keys=False,
            use_base_manager=False, primary_keys=[], output=output)
        self.stdout.write("sauvegarde de la base de donnée terminée\n")
        taille_fichier = os.path.getsize(output)
        self.stdout.write("Début compression de la sauvegarde\n")
        with open(output, 'rb') as fichier:
            with bz2.open(bz2_output,'wb') as fichier_bz2:
                fichier_bz2.write(bz2.compress(fichier.read()))
                os.remove(output)
        compression = (1-os.path.getsize(bz2_output)/taille_fichier)*100
        self.stdout.write("Compression de la sauvegarde terminée (taux de compression: {:.02f}%)\n".format(compression))
        if backup_media:
            self.stdout.write("Début de la sauvegarde des fichiers media\n")
            taille_repertoire = 0
            with tarfile.open(media_output, 'w:xz') as archive_zip:
                for folder, subfolders, files in os.walk(MEDIA_ROOT):
                    for file in files:
                        if (file != '.gitignore'):
                            taille_repertoire += os.path.getsize(os.path.join(folder, file))
                            archive_zip.add(os.path.join(folder, file), os.path.relpath(os.path.join(folder,file), MEDIA_ROOT))
            compression = (1-os.path.getsize(media_output)/taille_repertoire)*100
            self.stdout.write("Sauvegarde des fichiers media terminée (taux de compression: {:.02f}%)\n".format(compression))




