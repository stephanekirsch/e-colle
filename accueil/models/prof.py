from django.db import models,connection
from .classe import Classe
from .autre import dictfetchall


class ProfManager(models.Manager):
    def listeprofs(self):
        for classe in Classe.objects.all().select_related('profprincipal__user'):
            requete = "SELECT m.nom nom_matiere, u.first_name prenom, u.last_name nom\
                       FROM accueil_matiere m\
                       INNER JOIN accueil_classe_matieres cm\
                       ON m.id = cm.matiere_id\
                       LEFT OUTER JOIN accueil_prof p\
                       ON (p.matiere_id = m.id AND p.classe_id = %s)\
                       LEFT OUTER JOIN accueil_colleur c\
                       ON p.colleur_id=c.id\
                       LEFT OUTER JOIN accueil_user u\
                       ON u.colleur_id=c.id\
                       WHERE cm.classe_id = %s\
                       ORDER BY m.nom"
            with connection.cursor() as cursor:
                cursor.execute(requete,(classe.pk,classe.pk))
                prof = dictfetchall(cursor)
            yield classe, prof

class Prof(models.Model):
    colleur = models.ForeignKey("Colleur",verbose_name="Professeur", related_name="colleurprof",on_delete =models.CASCADE)
    classe = models.ForeignKey("Classe",verbose_name="Classe", related_name="classeprof",on_delete =models.CASCADE)
    matiere= models.ForeignKey("Matiere",verbose_name="Matière", related_name="matiereprof",on_delete =models.CASCADE)
    modifgroupe = models.BooleanField(verbose_name="Droits de modification des groupes de colle")
    modifcolloscope = models.BooleanField(verbose_name="Droits de modification du colloscope")
    objects = ProfManager()

    class Meta:
        # un seul prof par couple classe/matière
        unique_together=('classe', 'matiere') 

