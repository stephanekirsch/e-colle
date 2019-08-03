from django.db import models, connection
from .semaine import Semaine
from .autre import Creneau, date_plus_jour, dictfetchall
from django.db.models import Count
from datetime import date, timedelta, datetime, time, timezone

class ColleManager(models.Manager):

    def classe2colloscope(self,classe,semin,semax,modif=False):
        semaines=Semaine.objects.filter(lundi__range=(semin.lundi,semax.lundi))
        jours = Creneau.objects.filter(classe=classe)
        creneaux = Creneau.objects.filter(classe=classe)
        if not modif:
            jours = jours.filter(colle__semaine__lundi__range=(semin.lundi,semax.lundi))
            creneaux = creneaux.filter(colle__semaine__lundi__range=(semin.lundi,semax.lundi)).annotate(nb=Count('colle')).filter(nb__gt=0)
        jours = jours.values('jour').annotate(nb=Count('id',distinct=True)).order_by('jour')            
        requete="SELECT {} cr.id id_cr, c2.id id_col, c2.colleur_id id_colleur, jf.nom ferie, m.id id_matiere, m.nom nom_matiere, m.couleur couleur, m.temps temps, g.nom nomgroupe, cr.jour jour, cr.heure heure, cr.salle salle, cr.id, s.lundi lundi, e.id id_eleve, u2.first_name prenom_eleve,u2.last_name nom_eleve {} \
                        FROM accueil_creneau cr \
                        CROSS JOIN accueil_semaine s\
                        {}\
                        LEFT OUTER JOIN accueil_colle c2 \
                        ON (c2.creneau_id=cr.id AND c2.semaine_id=s.id) \
                        LEFT OUTER JOIN accueil_user u \
                        ON u.colleur_id=c2.colleur_id \
                        LEFT OUTER JOIN accueil_matiere m \
                        ON c2.matiere_id=m.id \
                        LEFT OUTER JOIN accueil_groupe g \
                        ON g.id=c2.groupe_id \
                        LEFT OUTER JOIN accueil_eleve e\
                        ON e.id=c2.eleve_id\
                        LEFT OUTER JOIN accueil_user u2\
                        ON u2.eleve_id = e.id\
                        LEFT OUTER JOIN accueil_jourferie jf \
                        ON jf.date = {}\
                        WHERE cr.classe_id=%s AND s.lundi BETWEEN %s AND %s \
                        ORDER BY s.lundi, cr.jour, cr.heure, cr.salle, cr.id".format("" if modif else "DISTINCT","" if modif else ", g.id groupe, u.last_name nom, u.first_name prenom, {} jourbis".format(date_plus_jour('s.lundi','cr.jour')),"" if modif else "INNER JOIN accueil_colle c \
                        ON c.creneau_id=cr.id INNER JOIN accueil_semaine s2    ON (c.semaine_id=s2.id AND s2.lundi BETWEEN %s AND %s)",date_plus_jour('s.lundi','cr.jour'))
        with connection.cursor() as cursor:
            cursor.execute(requete, ([] if modif else [semin.lundi,semax.lundi])+[classe.pk,semin.lundi,semax.lundi])
            precolles = dictfetchall(cursor)
        colles = []
        longueur = creneaux.count()
        for i in range(semaines.count()):
            colles.append(precolles[:longueur])
            del precolles[:longueur]
        return jours,creneaux,colles,semaines

    def agenda(self,colleur):
        semainemin = date.today()+timedelta(days=-28)
        requete = "SELECT COUNT(n.id) nbnotes, co.id pk, g.nom nom_groupe, cl.nom nom_classe, {} jour, s.numero, cr.heure heure, cr.salle salle, m.id, m.nom nom_matiere, m.couleur couleur, m.lv lv, m.temps, u2.first_name prenom_eleve, u2.last_name nom_eleve, p.titre titre, p.detail detail, p.fichier fichier\
                   FROM accueil_colle co\
                   INNER JOIN accueil_creneau cr\
                   ON co.creneau_id = cr.id\
                   INNER JOIN accueil_matiere m\
                   ON co.matiere_id = m.id\
                   INNER JOIN accueil_semaine s\
                   ON co.semaine_id=s.id\
                   INNER JOIN accueil_colleur c\
                   ON co.colleur_id = c.id\
                   LEFT OUTER JOIN accueil_groupe g\
                   ON co.groupe_id = g.id\
                   LEFT OUTER JOIN accueil_eleve e\
                   ON co.eleve_id = e.id\
                   LEFT OUTER JOIN accueil_eleve e2\
                   ON e2.groupe_id = g.id\
                   LEFT OUTER JOIN accueil_user u2\
                   ON u2.eleve_id = e.id\
                   LEFT OUTER JOIN accueil_classe cl\
                   ON (co.classe_id = cl.id OR g.classe_id=cl.id OR e.classe_id=cl.id)\
                   LEFT OUTER JOIN accueil_programme_semaine ps\
                   ON ps.semaine_id = s.id\
                   LEFT OUTER JOIN accueil_programme p\
                   ON (ps.programme_id = p.id AND p.matiere_id = m.id AND p.classe_id = cl.id)\
                   LEFT OUTER JOIN accueil_note n\
                   ON n.matiere_id = m.id AND n.colleur_id = c.id AND n.semaine_id=s.id AND (n.eleve_id = e.id OR n.eleve_id = e2.id)\
                   WHERE c.id=%s AND s.lundi >= %s\
                   GROUP BY co.id, g.nom, g.id, cl.nom, s.id, cr.jour, cr.heure, cr.salle, m.id, m.nom, m.couleur, m.lv, m.temps, u2.first_name, u2.last_name, p.titre, p.detail, p.fichier\
                   ORDER BY s.lundi,cr.jour,cr.heure".format(date_plus_jour('s.lundi','cr.jour'))
        with connection.cursor() as cursor:
            cursor.execute(requete,(colleur.pk,semainemin))
            colles = dictfetchall(cursor)
        groupeseleve = self.filter(colleur=colleur,semaine__lundi__gte=semainemin,matiere__temps=20).select_related('matiere').prefetch_related('groupe__groupeeleve','groupe__groupeeleve__user')
        groupes = {}
        for colle in groupeseleve:
            groupes[colle.pk] = "; ".join(["{} {}".format(eleve.user.first_name.title(),eleve.user.last_name.upper()) for eleve in colle.groupe.groupeeleve.all() if not colle.matiere.lv or colle.matiere.lv==1 and eleve.lv1 == colle.matiere or colle.matiere.lv==2 and eleve.lv2 == colle.matiere])
        return [{"nbnotes":colle["nbnotes"], "nom_groupe":colle["nom_groupe"], "nom_classe":colle["nom_classe"], "jour":colle["jour"], "numero": colle["numero"], "heure":colle["heure"], "salle":colle["salle"], "nom_matiere":colle["nom_matiere"], "couleur":colle["couleur"],
        "eleve": None if colle["prenom_eleve"] is None else "{} {}".format(colle['prenom_eleve'].title(),colle['nom_eleve'].upper()), "titre":colle["titre"], "fichier":colle["fichier"], "groupe": None if colle["nom_groupe"] is None else groupes[colle["pk"]],
        "detail":colle["detail"], "temps": colle["temps"], "pk": colle["pk"]} for colle in colles]

    def agendaEleve(self,eleve):
        requete = "SELECT s.lundi lundi, s.numero, {} jour, cr.heure heure, cr.salle salle, m.nom nom_matiere, m.couleur couleur, u.first_name prenom, u.last_name nom, p.titre titre, p.detail detail, p.fichier fichier\
                   FROM accueil_colle co\
                   INNER JOIN accueil_creneau cr\
                   ON co.creneau_id = cr.id\
                   INNER JOIN accueil_matiere m\
                   ON co.matiere_id = m.id\
                   INNER JOIN accueil_semaine s\
                   ON co.semaine_id=s.id\
                   INNER JOIN accueil_colleur c\
                   ON co.colleur_id=c.id\
                   INNER JOIN accueil_user u\
                   ON u.colleur_id=c.id\
                   LEFT OUTER JOIN accueil_groupe g\
                   ON co.groupe_id = g.id\
                   INNER JOIN accueil_eleve e\
                   ON e.groupe_id = g.id AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id) OR e.id=co.eleve_id\
                   LEFT OUTER JOIN accueil_programme_semaine ps\
                   ON ps.semaine_id = s.id\
                   LEFT OUTER JOIN accueil_programme p\
                   ON (ps.programme_id = p.id AND p.matiere_id = m.id AND p.classe_id = %s)\
                   WHERE e.id=%s AND s.lundi >= %s\
                   ORDER BY s.lundi,cr.jour,cr.heure".format(date_plus_jour('s.lundi','cr.jour'))
        with connection.cursor() as cursor:
            cursor.execute(requete,(eleve.classe.pk,eleve.pk,date.today()+timedelta(days=-27)))
            colles = dictfetchall(cursor)
        return colles

    def agendaEleveApp(self,eleve):
        requete = "SELECT s.numero, {} jour, cr.heure heure, cr.salle salle, m.nom nom_matiere, m.couleur couleur, u.first_name prenom, u.last_name nom, p.id id_programme\
                   FROM accueil_colle co\
                   INNER JOIN accueil_creneau cr\
                   ON co.creneau_id = cr.id\
                   INNER JOIN accueil_matiere m\
                   ON co.matiere_id = m.id\
                   INNER JOIN accueil_semaine s\
                   ON co.semaine_id=s.id\
                   INNER JOIN accueil_colleur c\
                   ON co.colleur_id=c.id\
                   INNER JOIN accueil_user u\
                   ON u.colleur_id=c.id\
                   LEFT OUTER JOIN accueil_groupe g\
                   ON co.groupe_id = g.id\
                   INNER JOIN accueil_eleve e\
                   ON e.groupe_id = g.id AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id) OR e.id=co.eleve_id\
                   LEFT OUTER JOIN accueil_programme_semaine ps\
                   ON ps.semaine_id = s.id\
                   LEFT OUTER JOIN accueil_programme p\
                   ON (ps.programme_id = p.id AND p.matiere_id = m.id AND p.classe_id = %s)\
                   WHERE e.id=%s AND s.lundi >= %s\
                   ORDER BY s.lundi,cr.jour,cr.heure".format(date_plus_jour('s.lundi','cr.jour'))
        with connection.cursor() as cursor:
            cursor.execute(requete,(eleve.classe.pk,eleve.pk,date.today()+timedelta(days=-27)))
            colles = dictfetchall(cursor)
        return [{'time': int(datetime.combine(agenda['jour'], time(*divmod(agenda['heure'],60))).replace(tzinfo=timezone.utc).timestamp()),
                                     'room':agenda['salle'],
                                     'week':agenda['numero'],
                                     'subject':agenda['nom_matiere'],
                                     'color':agenda['couleur'],
                                     'colleur':agenda['prenom'].title() + " " + agenda['nom'].upper(),
                                     'program':agenda['id_programme']
                                     } for agenda in colles]

    def compatEleve(self,id_classe):
        requete = "SELECT COUNT(DISTINCT co.id) nbColles, COUNT(g.id), s.numero numero, cr.jour jour, cr.heure heure, u.first_name prenom, u.last_name nom\
        FROM accueil_colle co\
        LEFT OUTER JOIN accueil_groupe g\
        ON co.groupe_id = g.id\
        LEFT OUTER JOIN accueil_eleve e\
        ON (e.id = co.eleve_id OR e.groupe_id = g.id)\
        INNER JOIN accueil_semaine s\
        ON co.semaine_id = s.id\
        INNER JOIN accueil_user u\
        ON u.eleve_id = e.id\
        INNER JOIN accueil_creneau cr\
        ON co.creneau_id = cr.id\
        WHERE cr.classe_id=%s\
        GROUP BY s.numero, cr.jour, cr.heure, u.first_name, u.last_name\
        HAVING COUNT(DISTINCT co.id) > 1 AND COUNT(g.id) < COUNT(DISTINCT co.id)\
        ORDER BY s.numero, cr.jour, cr.heure, u.first_name, u.last_name"
        with connection.cursor() as cursor:
            cursor.execute(requete,(id_classe,))
            incompat = dictfetchall(cursor)
        return incompat

class Colle(models.Model):
    creneau = models.ForeignKey("Creneau",on_delete=models.PROTECT)
    colleur = models.ForeignKey("Colleur",on_delete=models.PROTECT)
    matiere = models.ForeignKey("Matiere",on_delete=models.PROTECT)
    groupe = models.ForeignKey("Groupe",on_delete=models.PROTECT,null=True)
    eleve = models.ForeignKey("Eleve",on_delete=models.PROTECT,null=True) # null = True dans l'éventualité où on note un élève fictif pour l'informatique
    classe = models.ForeignKey("Classe",on_delete=models.PROTECT,null=True) # il est nécessaire de préciser la classe si null=true pour eleve et groupe
    semaine = models.ForeignKey("Semaine",on_delete=models.PROTECT)
    objects = ColleManager()

