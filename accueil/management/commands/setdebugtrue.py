from django.core.management.base import BaseCommand
from ecolle.settings import CHEMINVERSECOLLE
import os

class Command(BaseCommand):
    help = """passe en mode DEBUG = True"""

    def handle(self, *args, **options):
        nomfichier = os.path.join(CHEMINVERSECOLLE,"ecolle","debug.py")
        try:
            with open(nomfichier,"wt",encoding="utf8") as fichier:
                fichier.write("DEBUG = True")
                self.stdout.write("variable DEBUG passée à True")
        except Exception:
            self.stdout.write("Les droits sont insuffisants pour modifier le fichier")
    

