from django.db import models,connection
from .classe import Classe
from .autre import dictfetchall
from ecolle.settings import BDD


class ProfManager(models.Manager):
    def listeprofs(self):
        for classe in Classe.objects.all().select_related('profprincipal__user'):
            requete = "SELECT m.nom nom_matiere, m.id id, u.first_name prenom, u.last_name nom\
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
                       ORDER BY m.nom, m.id"
            with connection.cursor() as cursor:
                cursor.execute(requete,(classe.pk,classe.pk))
                profs = dictfetchall(cursor)
                profcolleur = []
                lastid = 0
                for prof in profs:
                  if prof["id"] == lastid and prof["nom"] is not None and prof["prenom"] is not None:
                    profcolleur[-1]["colleur"] += "; {} {}".format(prof['prenom'].title(), prof['nom'].upper())
                  else:
                    profcolleur.append({"id":prof['id'],"matiere":prof["nom_matiere"],"colleur": None if (prof['nom'] is None or prof['prenom'] is None) else "{} {}".format(prof["prenom"].title(), prof["nom"].upper())})
                  lastid = prof["id"]
            yield classe, profcolleur

class Prof(models.Model):
    colleur = models.ForeignKey("Colleur",verbose_name="Professeur", related_name="colleurprof",on_delete =models.CASCADE)
    classe = models.ForeignKey("Classe",verbose_name="Classe", related_name="classeprof",on_delete =models.CASCADE)
    matiere= models.ForeignKey("Matiere",verbose_name="Matière", related_name="matiereprof",on_delete =models.CASCADE)
    modifgroupe = models.BooleanField(verbose_name="Droits de modification des groupes de colle")
    modifcolloscope = models.BooleanField(verbose_name="Droits de modification du colloscope")
    cacherang = models.BooleanField(verbose_name = "masquer les rangs des étudiants",default=False)
    objects = ProfManager()