from django.db import models
from random import choice

def texte_aleatoire(taille):
    return "".join(choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789") for i in range(taille))

class Eleve(models.Model):
    def update_photo(instance, filename):
        """Renvoie l'url vers le fichier photo"""
        return "photos/photo{}.{}".format(texte_aleatoire(20),filename.split('.')[-1])
    classe = models.ForeignKey("Classe",related_name="classeeleve",on_delete=models.PROTECT)
    groupe = models.ForeignKey("Groupe", null=True,related_name="groupeeleve", on_delete=models.SET_NULL)
    photo = models.ImageField(verbose_name="photo(jpg/png, 300x400)",upload_to=update_photo,null=True,blank=True)
    ddn = models.DateField(verbose_name="Date de naissance",null=True,blank=True)
    ldn = models.CharField(verbose_name="Lieu de naissance",max_length=50,blank=True,default="")
    ine = models.CharField(verbose_name="numéro étudiant (INE)",max_length=11,null=True,blank=True)
    lv1 = models.ForeignKey("Matiere",related_name='elevelv1',null=True,blank=True, on_delete = models.SET_NULL)
    lv2 = models.ForeignKey("Matiere",related_name='elevelv2',null=True,blank=True, on_delete = models.SET_NULL)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return "{} {}".format(self.user.first_name.title(),self.user.last_name.upper())
