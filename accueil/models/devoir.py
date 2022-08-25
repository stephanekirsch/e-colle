from django.db import models
from datetime import timedelta, time
from .contenttype import ContentTypeRestrictedFileField
from random import choice
from django.db.models.signals import post_delete
from django.db import connection 
from django.dispatch import receiver
import os
from ecolle.settings import MEDIA_ROOT
from unidecode import unidecode

def dictfetchall(cursor):
    """Renvoie les lignes du curseur sous forme de dictionnaire"""
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def texte_aleatoire(taille):
    return "".join(choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789") for i in range(taille))

class DevoirManager(models.Manager):
    def devoirsEleves(self, eleve, matiere = None):
        if matiere is None:
            requete = "SELECT dv.id, dv.numero, dv.date_affichage, m.nom, m.couleur, dv.detail, dv.a_rendre_jour, dv.a_rendre_heure, dv.fichier enonce, dv.corrige\
            , dr.fichier copie, dc.fichier copie_corrige\
            FROM accueil_devoir dv \
            INNER JOIN accueil_matiere m\
            ON dv.matiere_id = m.id\
            LEFT JOIN accueil_devoirrendu dr\
            ON dr.devoir_id = dv.id AND dr.eleve_id = %s\
            LEFT JOIN accueil_devoircorrige dc\
            ON dc.devoir_id = dv.id AND dc.eleve_id = %s\
            WHERE dv.classe_id = %s\
            ORDER BY dv.a_rendre_jour DESC, dv.a_rendre_heure DESC"
            with connection.cursor() as cursor:
                cursor.execute(requete,(eleve.pk, eleve.pk, eleve.classe.pk))
                devoirs = dictfetchall(cursor)
        else:
            requete = "SELECT dv.id, dv.numero, dv.date_affichage, dv.detail, dv.a_rendre_jour, dv.a_rendre_heure, dv.fichier enonce, dv.corrige\
            , dr.fichier copie, dc.fichier copie_corrige\
            FROM accueil_devoir dv \
            LEFT JOIN accueil_devoirrendu dr\
            ON dr.devoir_id = dv.id AND dr.eleve_id = %s\
            LEFT JOIN accueil_devoircorrige dc\
            ON dc.devoir_id = dv.id AND dc.eleve_id = %s\
            WHERE dv.classe_id = %s AND dv.matiere_id = %s\
            ORDER BY dv.a_rendre_jour DESC, dv.a_rendre_heure DESC"
            with connection.cursor() as cursor:
                cursor.execute(requete,(eleve.pk, eleve.pk, eleve.classe.pk, matiere.pk))
                devoirs = dictfetchall(cursor)
        return devoirs

    def devoirsrendus(self, devoir):
        requete = "SELECT e.id, u.first_name, u.last_name, dr.fichier copie, dr.date_rendu, dc.fichier copiecorrige, dc.commentaire\
        FROM accueil_user u\
        INNER JOIN accueil_eleve e\
        ON u.eleve_id = e.id\
        LEFT JOIN accueil_devoirrendu dr\
        ON dr.eleve_id = e.id AND dr.devoir_id = %s\
        LEFT JOIN accueil_devoircorrige dc\
        ON dc.eleve_id = e.id AND dc.devoir_id = %s\
        WHERE e.classe_id = %s \
        ORDER BY u.last_name, u.first_name"
        with connection.cursor() as cursor:
                cursor.execute(requete,(devoir.pk, devoir.pk, devoir.classe.pk))
                copies = dictfetchall(cursor)
        return copies

class Devoir(models.Model):
    def update_name(instance, filename):
        return os.path.join("devoir", "devoir_" + texte_aleatoire(20) + ".pdf")
    def update_name_corrige(instance, filename):
        return os.path.join("devoir", "corrige_" + texte_aleatoire(20) + ".pdf")
    classe = models.ForeignKey("Classe",related_name="classedevoir",on_delete=models.PROTECT)
    matiere= models.ForeignKey("Matiere",related_name="matieredevoir",on_delete=models.PROTECT)
    numero = models.PositiveSmallIntegerField(verbose_name="Numéro", choices = list(zip(range(1,101),range(1,101))))
    detail = models.TextField(verbose_name="Détails",null=True,blank=True)
    date_affichage = models.DateTimeField(auto_now_add = True)
    a_rendre_jour = models.DateField(verbose_name="à rendre le ",null = True, blank = True)
    a_rendre_heure = models.TimeField(verbose_name="à",null = True, blank = True, choices = [(time(h,0,0), "{:2d}h00".format(h)) for h in range(24)])
    fichier = ContentTypeRestrictedFileField(verbose_name="Énoncé(pdf)",upload_to=update_name,null=True,blank=True,content_types=["application/pdf"], max_upload_size=5000000)
    corrige = ContentTypeRestrictedFileField(verbose_name="Corrigé(pdf)",upload_to=update_name_corrige,null=True,blank=True,content_types=["application/pdf"], max_upload_size=5000000)
    objects = DevoirManager()

    class Meta:
        ordering = ['-numero']
        unique_together = ['numero', 'classe', 'matiere']

    def __str__(self):
        return "Devoir n°{} / {} / {}".format(self.numero, self.classe, self.matiere)

class DevoirRendu(models.Model):
    def update_name(instance, filename):
        return os.path.join("devoir", "rendu_{}_{}_{}.pdf".format(unidecode(instance.eleve.user.last_name), unidecode(instance.eleve.user.first_name), texte_aleatoire(20)))
    eleve = models.ForeignKey("Eleve", related_name = "devoireleve", on_delete = models.CASCADE)
    devoir = models.ForeignKey("Devoir", related_name = "rendus", on_delete = models.CASCADE)
    date_rendu = models.DateTimeField(auto_now = True)
    fichier = ContentTypeRestrictedFileField(verbose_name="Fichier(pdf)",upload_to=update_name,null=True,blank=True,content_types=["application/pdf"], max_upload_size=10000000)

    class Meta:
        ordering = ['date_rendu']
        unique_together = ['eleve', 'devoir']

    def __str__(self):
        return "Copie de {} au {}".format(self.eleve, self.devoir)

class DevoirCorrige(models.Model):
    def update_name(instance, filename = ""):
        return os.path.join("devoir", "copiecorrige_{}_{}_{}.pdf".format(unidecode(instance.eleve.user.last_name), unidecode(instance.eleve.user.first_name), texte_aleatoire(20)))
    eleve = models.ForeignKey("Eleve", related_name = "devoircorrigeeleve", on_delete = models.PROTECT)
    devoir = models.ForeignKey("Devoir", related_name = "corriges", on_delete = models.PROTECT)
    commentaire = models.TextField(verbose_name="Commentaire",null=True,blank=True)
    fichier = ContentTypeRestrictedFileField(verbose_name="Fichier(pdf)",upload_to=update_name,null=True,blank=True,content_types=["application/pdf"], max_upload_size=10000000)

    class Meta:
        ordering = ['eleve__user__last_name', 'eleve__user__first_name']
        unique_together = ['eleve', 'devoir']

    def __str__(self):
        return "Copie corrigée de {} au devoir n°{}".format(self.eleve, self.devoir)

class TD(models.Model):
    def update_name(instance, filename):
        return os.path.join("td", "td" + texte_aleatoire(20) + ".pdf")
    classe = models.ForeignKey("Classe",related_name="classetd",on_delete=models.PROTECT)
    matiere = models.ForeignKey("Matiere",related_name="matieretd",on_delete=models.PROTECT)
    numero = models.PositiveSmallIntegerField(verbose_name="Numéro", choices = list(zip(range(1,101),range(1,101))))
    detail = models.TextField(verbose_name="Détails",null=True,blank=True)
    date_affichage = models.DateTimeField(auto_now_add = True)
    fichier = ContentTypeRestrictedFileField(verbose_name="Fichier(pdf)",upload_to=update_name,null=True,blank=True,content_types=["application/pdf"], max_upload_size=2000000)

    class Meta:
        ordering = ['-numero']
        unique_together = ['classe', 'matiere', 'numero']

class Cours(models.Model):
    def update_name(instance, filename):
        return os.path.join("cours", "cours" + texte_aleatoire(20) + ".pdf")
    classe = models.ForeignKey("Classe",related_name="classecours",on_delete=models.PROTECT)
    matiere = models.ForeignKey("Matiere",related_name="matierecours",on_delete=models.PROTECT)
    numero = models.PositiveSmallIntegerField(verbose_name="Numéro", choices = list(zip(range(1,101),range(1,101))))
    detail = models.TextField(verbose_name="Détails",null=True,blank=True)
    date_affichage = models.DateTimeField(auto_now_add = True)
    fichier = ContentTypeRestrictedFileField(verbose_name="Fichier(pdf)",upload_to=update_name,null=True,blank=True,content_types=["application/pdf"], max_upload_size=10000000)

    class Meta:
        ordering = ['-numero']
        unique_together = ['classe', 'matiere', 'numero']

class Document(models.Model):
    def update_name(instance, filename):
        return os.path.join("doc", "doc" + texte_aleatoire(20) + ".pdf")
    classe = models.ForeignKey("Classe",related_name="classedocument",on_delete=models.PROTECT)
    matiere = models.ForeignKey("Matiere",related_name="matieredocument",on_delete=models.PROTECT)
    titre = models.CharField(max_length=80,null=True,blank=True)
    detail = models.TextField(verbose_name="Détails",null=True,blank=True)
    date_affichage = models.DateTimeField(auto_now_add = True)
    fichier = ContentTypeRestrictedFileField(verbose_name="Fichier(pdf)",upload_to=update_name,null=True,blank=True,content_types=["application/pdf"], max_upload_size=10000000)

    class Meta:
        ordering = ['-date_affichage']
        unique_together = ['classe', 'matiere', 'titre']

@receiver(post_delete, sender=Devoir)
def devoir_post_delete_function(sender, instance, **kwargs):
    if instance.fichier and instance.fichier.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.fichier.name)
        if os.path.isfile(fichier):
            os.remove(fichier)
    if instance.corrige and instance.corrige.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.corrige.name)
        if os.path.isfile(fichier):
            os.remove(fichier)

@receiver(post_delete, sender=Cours)
def cours_post_delete_function(sender, instance, **kwargs):
    if instance.fichier and instance.fichier.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.fichier.name)
        if os.path.isfile(fichier):
            os.remove(fichier)

@receiver(post_delete, sender=TD)
def td_post_delete_function(sender, instance, **kwargs):
    if instance.fichier and instance.fichier.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.fichier.name)
        if os.path.isfile(fichier):
            os.remove(fichier)

@receiver(post_delete, sender=Document)
def document_post_delete_function(sender, instance, **kwargs):
    if instance.fichier and instance.fichier.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.fichier.name)
        if os.path.isfile(fichier):
            os.remove(fichier)


@receiver(post_delete, sender=DevoirRendu)
def devoirrendu_post_delete_function(sender, instance, **kwargs):
    if instance.fichier and instance.fichier.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.fichier.name)
        if os.path.isfile(fichier):
            os.remove(fichier)

@receiver(post_delete, sender=DevoirCorrige)
def devoircorrige_post_delete_function(sender, instance, **kwargs):
    if instance.fichier and instance.fichier.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.fichier.name)
        if os.path.isfile(fichier):
            os.remove(fichier)



