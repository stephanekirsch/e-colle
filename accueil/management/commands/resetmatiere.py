from django.core.management.commands.dumpdata import Command as ResetMatiere
from accueil.models import Matiere
class Command(ResetMatiere):
    help = """réinitialise l'attribut nomcomplet des matières"""

    def handle(self,*app_labels,**options):
        try:
            for matiere in Matiere.objects.all():
                matiere.nomcomplet = str(matiere)
                matiere.save()
        except Exception as e:
            print("erreur", str(e))
        else:
            print("Nom des matières réinitialisé")
