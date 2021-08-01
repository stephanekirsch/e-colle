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

    def haslangue(self,matiere,semestre = 1):
        if semestre == 1:
            if matiere.lv == 0:
                return True
            if matiere.lv == 1:
                return Eleve.objects.filter(groupe=self,lv1=matiere).exists()
            if matiere.lv == 2:
                return Eleve.objects.filter(groupe=self,lv2=matiere).exists()
        elif semestre == 2:
            if matiere in (self.classe.option1, self.classe.option2):
                return Eleve.objects.filter(groupe2=self,option=matiere).exists()
            if matiere.lv == 0:
                return True
            if matiere.lv == 1:
                return Eleve.objects.filter(groupe2=self,lv1=matiere).exists()
            if matiere.lv == 2:
                return Eleve.objects.filter(groupe2=self,lv2=matiere).exists()

    def __str__(self):
        return str(self.nom)

    def statut2(self):
        return self.statut(2)

    def statut(self, semestre = 1):
        if semestre == 1:
            lv1 = Eleve.objects.filter(groupe = self).values_list('lv1__nom', flat = True)
            lv2 = Eleve.objects.filter(groupe = self).values_list('lv2__nom', flat = True)
            option = False
        elif semestre == 2:
            lv1 = Eleve.objects.filter(groupe2 = self).values_list('lv1__nom', flat = True)
            lv2 = Eleve.objects.filter(groupe2 = self).values_list('lv2__nom', flat = True)
            option = Eleve.objects.filter(groupe2 = self).values_list('option__nom', flat = True)
        sortie = ""
        lv1 = sorted(set(lv1)-{None})
        if lv1:
            sortie += "LV1: {}".format(" / ".join(x.title() for x in lv1))
        lv2 = sorted(set(lv2)-{None})
        if lv2:
            sortie += "\nLV2: {}".format(" / ".join(x.title() for x in lv2))
        if option:
            option = sorted(set(option)-{None})
            if option:
                sortie += "\nOption: {}".format(" / ".join(x.title() for x in option))
        return sortie
        

