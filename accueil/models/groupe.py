from django.db import models
from .eleve import Eleve

class Groupe(models.Model):
    nom = models.PositiveSmallIntegerField(
        choices = [(i,i) for i in range(1,31)],
        verbose_name = "Nom"
    )
    classe = models.ForeignKey(
        "Classe",
        related_name="classegroupe", 
        on_delete=models.PROTECT
    )

    class Meta:
        unique_together=('nom','classe')
        ordering=['nom']

    def haslangue(self,matiere):
        if not matiere.lv:
            return True
        if matiere.lv == 1:
            return Eleve.objects.filter(groupe=self,lv1=matiere).exists()
        if matiere.lv == 2:
            return Eleve.objects.filter(groupe=self,lv2=matiere).exists()

    def __str__(self):
        return str(self.nom)
