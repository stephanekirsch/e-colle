from django.db import models, connection
from django.shortcuts import get_object_or_404
from .classe import Classe
from .groupe import Groupe
from .semaine import Semaine
from .autre import Creneau, date_plus_jour, dictfetchall
from .config import Config
from django.db.models import Count
from datetime import date, timedelta, datetime, time, timezone
from ecolle.settings import BDD


def group_concat(arg):
    """Renvoie une chaîne de caractères correspondant à la syntaxe SQL 
    qui permet d'utiliser une fonction d'agrégation qui concatène des chaînes"""
    if BDD == 'postgresql' or BDD == 'postgresql_psycopg2':
        return "STRING_AGG(DISTINCT CAST(COALESCE({0:},0) AS TEXT), ',' ORDER BY CAST(COALESCE({0:},0) AS TEXT))".format(arg)
    elif BDD == 'mysql':
        return "GROUP_CONCAT(DISTINCT COALESCE({0:},0))".format(arg)
    elif BDD == 'sqlite3':
        return "GROUP_CONCAT(DISTINCT CAST (COALESCE({},0) AS TEXT))".format(arg)
    else:
        return "" # à compléter par ce qu'il faut dans le cas ou vous utilisez 
                  # un SGBD qui n'est ni mysql, ni postgresql, ni sqlite

class ColleManager(models.Manager):

    def classe2colloscope(self,classe,semin,semax,modif=False,transpose=False):
        semaines=Semaine.objects.filter(lundi__range=(semin.lundi,semax.lundi))
        if transpose:
            # selection des couples créneau/colleur
            requete1 = "SELECT DISTINCT m.nom matiere_nom, m.lv, m.couleur, u.first_name prenom, u.last_name nom, cr.jour jds, cr.heure, cr.salle, cr.id\
            FROM accueil_creneau cr \
            INNER JOIN accueil_colle col\
            ON col.creneau_id = cr.id\
            INNER JOIN accueil_colleur co\
            ON col.colleur_id = co.id\
            INNER JOIN accueil_user u\
            ON u.colleur_id = co.id\
            INNER JOIN accueil_semaine s\
            ON col.semaine_id = s.id\
            INNER JOIN accueil_matiere m\
            ON col.matiere_id = m.id\
            WHERE cr.classe_id = %s AND s.lundi BETWEEN %s AND %s\
            ORDER BY cr.jour, cr.heure, cr.salle, cr.id, m.nom"
            with connection.cursor() as cursor:
                cursor.execute(requete1, ([classe.pk,semin.lundi,semax.lundi]))
                creneaux = dictfetchall(cursor)
            #selection des groupes de colle
            requete2 = "SELECT DISTINCT {} groupe, {} id_groupe, COUNT(col.id) nbcolles, colcr.id_colleur, colcr.jour, colcr.heure, colcr.salle, colcr.id_creneau, colcr.nom nom_matiere, colcr.id_matiere, s.numero, u.last_name nom, u.first_name prenom, e.id id_eleve, colcr.temps\
            FROM accueil_semaine s\
            CROSS JOIN \
            (SELECT DISTINCT co.id id_colleur, cr.id id_creneau, cr.jour jour, cr.heure heure, cr.salle salle, m.nom, m.temps, m.id id_matiere FROM accueil_creneau cr \
            INNER JOIN accueil_colle col\
            ON col.creneau_id = cr.id\
            INNER JOIN accueil_matiere m\
            ON col.matiere_id = m.id\
            INNER JOIN accueil_colleur co\
            ON col.colleur_id = co.id\
            INNER JOIN accueil_semaine s\
            ON col.semaine_id = s.id\
            WHERE cr.classe_id = %s AND s.lundi BETWEEN %s AND %s\
            ORDER BY jour, heure, salle, id_creneau) colcr\
            LEFT OUTER JOIN accueil_colle col\
            ON col.creneau_id = colcr.id_creneau AND col.semaine_id = s.id AND col.colleur_id = colcr.id_colleur\
            LEFT OUTER JOIN accueil_groupe g\
            ON col.groupe_id = g.id\
            LEFT OUTER JOIN accueil_eleve e\
            ON e.id=col.eleve_id\
            LEFT OUTER JOIN accueil_user u\
            ON u.eleve_id = e.id\
            WHERE s.lundi BETWEEN %s AND %s\
            GROUP BY colcr.id_colleur, colcr.jour, colcr.heure, colcr.salle, colcr.id_creneau, nom_matiere, colcr.id_matiere, s.numero, u.last_name,  u.first_name, id_eleve, colcr.temps\
            ORDER BY colcr.jour, colcr.heure, colcr.salle, colcr.id_creneau, colcr.nom, colcr.id_colleur, s.numero".format(group_concat('g.nom'), group_concat('g.id'))
            with connection.cursor() as cursor:
                cursor.execute(requete2, ([classe.pk,semin.lundi,semax.lundi,semin.lundi,semax.lundi]))
                groupes = dictfetchall(cursor)
            for i in range(len(groupes)):
                groupes[i]["id_groupe"] = eval("(" + groupes[i]["id_groupe"] + ",)")
            groupescolles = []
            longueur = semaines.count()
            for i in range(len(creneaux)):
                groupescolles.append(groupes[:longueur])
                del groupes[:longueur]
            return creneaux, groupescolles, semaines
        else:
            jours = Creneau.objects.filter(classe=classe)
            creneaux = Creneau.objects.filter(classe=classe)
            if not modif:
                jours = jours.filter(colle__semaine__lundi__range=(semin.lundi,semax.lundi))
                creneaux = creneaux.filter(colle__semaine__lundi__range=(semin.lundi,semax.lundi)).annotate(nb=Count('colle')).filter(nb__gt=0)
            creneaux = creneaux.order_by('jour','heure','salle','pk')
            jours = jours.values('jour').annotate(nb=Count('id',distinct=True)).order_by('jour')            
            requete="SELECT {} groupe, {} id_groupe, cr.id id_cr, COUNT(c2.id) nbcolles, c2.colleur_id id_colleur, jf.nom ferie, m.id id_matiere, m.nom nom_matiere, m.couleur couleur, m.temps temps, cr.jour jour, cr.heure heure, cr.salle salle, s.lundi lundi, e.id id_eleve, u2.first_name prenom_eleve,u2.last_name nom_eleve {} \
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
                            GROUP BY cr.id, c2.colleur_id, jf.nom, m.id, m.nom, m.couleur, m.temps, cr.jour, cr.heure, cr.salle, s.lundi, e.id, u2.first_name,u2.last_name {} \
                            ORDER BY s.lundi, cr.jour, cr.heure, cr.salle, cr.id".format(group_concat('g.nom'), group_concat('g.id') ,"" if modif else ", u.last_name nom, u.first_name prenom, {} jourbis".format(date_plus_jour('s.lundi','cr.jour')),"" if modif else "INNER JOIN accueil_colle c \
                            ON c.creneau_id=cr.id INNER JOIN accueil_semaine s2 ON (c.semaine_id=s2.id AND s2.lundi BETWEEN %s AND %s)",date_plus_jour('s.lundi','cr.jour'), "" if modif else ",u.last_name, u.first_name")
            with connection.cursor() as cursor:
                cursor.execute(requete, ([] if modif else [semin.lundi,semax.lundi])+[classe.pk,semin.lundi,semax.lundi])
                precolles = dictfetchall(cursor)
                for i in range(len(precolles)):
                    precolles[i]["id_groupe"] = eval("(" + precolles[i]["id_groupe"] + ",)")
            colles = []
            longueur = creneaux.count()
            for i in range(semaines.count()):
                colles.append(precolles[:longueur])
                del precolles[:longueur]
            return jours,creneaux,colles,semaines

    def agenda(self,colleur):
        semainemin = date.today()+timedelta(days=-28)
        semestre2 = Config.objects.get_config().semestre2
        requete = "SELECT COUNT(n.id) nbnotes, {} nom_groupe, {} id_groupes, {} id_colles, cr.id, cl.nom nom_classe, cl.semestres, {} jour, s.numero, cr.heure heure, cr.salle salle, m.id matiere_id, m.nom nom_matiere, m.lv, cl.option1_id, cl.option2_id, m.couleur couleur, m.lv lv, m.temps, u2.first_name prenom_eleve, u2.last_name nom_eleve, p.titre titre, p.detail detail, p.fichier fichier\
                   FROM accueil_colle co\
                   INNER JOIN accueil_creneau cr\
                   ON co.creneau_id = cr.id\
                   INNER JOIN accueil_matiere m\
                   ON co.matiere_id = m.id\
                   INNER JOIN accueil_semaine s\
                   ON co.semaine_id=s.id\
                   INNER JOIN accueil_colleur c\
                   ON co.colleur_id = c.id\
                   LEFT OUTER JOIN accueil_classe cl\
                   ON cr.classe_id = cl.id\
                   LEFT OUTER JOIN accueil_groupe g\
                   ON co.groupe_id = g.id\
                   LEFT OUTER JOIN accueil_eleve e\
                   ON co.eleve_id = e.id\
                   LEFT OUTER JOIN accueil_eleve e2\
                   ON (((cl.semestres IS FALSE OR s.numero < %s) AND e2.groupe_id = g.id)\
                   OR (cl.semestres IS TRUE AND s.numero >= %s AND e2.groupe2_id = g.id))\
                   LEFT OUTER JOIN accueil_user u2\
                   ON u2.eleve_id = e.id\
                   LEFT OUTER JOIN (SELECT ps.semaine_id, sub.matiere_id, sub.classe_id, sub.titre, sub.detail, sub.fichier FROM accueil_programme_semaine ps\
                   INNER JOIN accueil_programme sub\
                   ON ps.programme_id = sub.id) p\
                   ON p.semaine_id = s.id AND p.matiere_id = m.id AND p.classe_id = cl.id\
                   LEFT OUTER JOIN accueil_note n\
                   ON n.matiere_id = m.id AND n.colleur_id = c.id AND n.semaine_id=s.id AND (n.eleve_id = e.id OR n.eleve_id = e2.id)\
                   WHERE c.id=%s AND s.lundi >= %s\
                   GROUP BY cl.nom, cl.semestres, cl.option1_id, cl.option2_id,s.id, cr.id, cr.jour, cr.heure, cr.salle, m.id, m.nom, m.couleur, m.lv, m.temps, u2.first_name, u2.last_name, p.titre, p.detail, p.fichier\
                   ORDER BY s.lundi,cr.jour,cr.heure".format(group_concat('g.nom'), group_concat('g.id'), group_concat('co.id'), date_plus_jour('s.lundi','cr.jour'))
        requete2 = "SELECT COUNT(n.note) nbnotes, pl.id id_planche, cl.nom nom_classe, {} jour, s.numero, pl.heure heure, pl.salle salle, m.id matiere_id, m.nom nom_matiere, m.couleur couleur, m.temps, u.first_name prenom_eleve, u.last_name nom_eleve, pl.commentaire titre\
                   FROM accueil_planche pl\
                   INNER JOIN accueil_matiere m\
                   ON pl.matiere_id = m.id\
                   INNER JOIN accueil_semaine s\
                   ON pl.semaine_id=s.id\
                   INNER JOIN accueil_colleur c\
                   ON pl.colleur_id = c.id\
                   LEFT OUTER JOIN accueil_eleve e\
                   ON pl.eleve_id = e.id\
                   LEFT OUTER JOIN accueil_user u\
                   ON u.eleve_id = e.id\
                   LEFT OUTER JOIN accueil_classe cl\
                   ON e.classe_id = cl.id\
                   LEFT OUTER JOIN accueil_note n\
                   ON n.matiere_id = m.id AND n.colleur_id = c.id AND n.semaine_id=s.id AND n.eleve_id = e.id AND pl.heure=n.heure AND pl.semaine_id = n.semaine_id AND pl.jour = n.jour \
                   WHERE pl.eleve_id IS NOT NULL AND c.id=%s\
                   GROUP BY pl.id, cl.nom, pl.jour, s.numero, s.lundi, pl.heure, pl.salle, m.id, m.nom, m.couleur, m.temps, u.first_name, u.last_name, pl.commentaire\
                   ORDER BY s.lundi,pl.jour,pl.heure".format(date_plus_jour('s.lundi','pl.jour'))
        with connection.cursor() as cursor:
            cursor.execute(requete,(semestre2, semestre2, colleur.pk,semainemin))
            colles = dictfetchall(cursor)
        with connection.cursor() as cursor:
            cursor.execute(requete2,(colleur.pk,))
            colles2 = dictfetchall(cursor)
        eleves = []
        for colle in colles:
            if colle["id_groupes"] == "0":
                if colle["nom_eleve"]:
                    eleves.append("{} {}".format(colle["nom_eleve"].upper(),colle["prenom_eleve"].title()))
                else:
                    eleves.append(colle["nom_classe"])
            else:
                if colle["semestres"] and colle["numero"] >= semestre2:
                    isoption = colle["matiere_id"] == colle["option1_id"] or colle["matiere_id"] == colle["option2_id"]
                    eleves.append("; ".join(["{} {}".format("" if x[0] is None else x[0].upper(),"" if x[1] is None else x[1].title()) for x in Groupe.objects.filter(pk__in=map(int,colle["id_groupes"].split(","))).values_list("groupe2eleve__user__last_name","groupe2eleve__user__first_name","groupe2eleve__lv1","groupe2eleve__lv2","groupe2eleve__option") 
                        if isoption and x[4] == colle["matiere_id"] or not isoption and colle["lv"] == 0 or colle["lv"] == 1 and x[2] == colle["matiere_id"] or colle["lv"] == 2 and x[3] == colle["matiere_id"]]))
                else:
                    eleves.append("; ".join(["{} {}".format("" if x[0] is None else x[0].upper(),"" if x[1] is None else x[1].title()) for x in Groupe.objects.filter(pk__in=map(int,colle["id_groupes"].split(","))).values_list("groupeeleve__user__last_name","groupeeleve__user__first_name","groupeeleve__lv1","groupeeleve__lv2") 
                        if colle["lv"] == 0 or colle["lv"] == 1 and x[2] == colle["matiere_id"] or colle["lv"] == 2 and x[3] == colle["matiere_id"]]))
        for colle in colles2:
            eleves.append("{} {}".format(colle["nom_eleve"].upper(),colle["prenom_eleve"].title()))
        liste1 = [{"nbnotes":colle["nbnotes"], "nom_groupe":colle["nom_groupe"], "nom_classe":colle["nom_classe"], "jour":colle["jour"], "numero": colle["numero"], "heure":colle["heure"], "salle":colle["salle"], "nom_matiere":colle["nom_matiere"], "couleur":colle["couleur"],
        "eleve": None if colle["prenom_eleve"] is None else "{} {}".format(colle['prenom_eleve'].title(),colle['nom_eleve'].upper()), "titre":colle["titre"], "fichier":colle["fichier"], "groupe": colle["nom_groupe"],
        "detail":colle["detail"], "temps": colle["temps"], "id_colles": colle["id_colles"],"groupe": eleve, "is_planche":False} for colle, eleve in zip(colles,eleves)]
        liste2 = [{"nbnotes":colle["nbnotes"], "nom_classe":colle["nom_classe"], "jour":colle["jour"], "numero": colle["numero"], "heure":colle["heure"], "salle":colle["salle"], "nom_matiere":colle["nom_matiere"], "couleur":colle["couleur"],
        "eleve": "{} {}".format(colle['prenom_eleve'].title(),colle['nom_eleve'].upper()), "titre":colle["titre"], "temps": colle["temps"], "id_planche": colle["id_planche"], "is_planche":True} for colle in colles2]
        return sorted(liste1 + liste2, key = lambda x:(x['numero'], x['jour'],x['heure']))

    def agendaEleve(self,eleve):
        if eleve.classe.semestres:
            semestre2 = Config.objects.get_config().semestre2
            requete = "SELECT s.lundi lundi, s.numero, {} jour, cr.heure heure, cr.salle salle, m.nom nom_matiere, m.couleur couleur, u.first_name prenom, u.last_name nom, p.titre titre, p.detail detail, p.fichier fichier\
                       FROM accueil_colle co\
                       INNER JOIN accueil_creneau cr\
                       ON co.creneau_id = cr.id\
                       INNER JOIN accueil_classe cl\
                       ON cr.classe_id = cl.id\
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
                       ON (s.numero < %s AND e.groupe_id = g.id AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id))\
                       OR (s.numero >= %s AND e.groupe2_id = g.id AND ((cl.option1_id IS NULL OR m.id != cl.option1_id) AND (cl.option2_id IS NULL OR m.id != cl.option2_id) OR e.option_id = m.id) AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id))\
                       OR e.id=co.eleve_id\
                       OR co.eleve_id IS NULL AND co.groupe_id IS NULL AND co.classe_id = e.classe_id\
                       LEFT OUTER JOIN (SELECT ps.semaine_id, sub.matiere_id, sub.classe_id, sub.titre, sub.detail, sub.fichier FROM accueil_programme_semaine ps\
                       INNER JOIN accueil_programme sub\
                       ON ps.programme_id = sub.id) p\
                       ON p.semaine_id = s.id AND p.matiere_id = m.id AND p.classe_id = %s\
                       WHERE e.id=%s AND s.lundi >= %s\
                       ORDER BY s.lundi,cr.jour,cr.heure".format(date_plus_jour('s.lundi','cr.jour'))
            with connection.cursor() as cursor:
                cursor.execute(requete,(semestre2,semestre2,eleve.classe.pk,eleve.pk,date.today()+timedelta(days=-28)))
                colles = dictfetchall(cursor)
            return colles
        else:
            requete = "SELECT s.lundi lundi, s.numero, {} jour, cr.heure heure, cr.salle salle, m.nom nom_matiere, m.couleur couleur, u.first_name prenom, u.last_name nom, p.titre titre, p.detail detail, p.fichier fichier\
                       FROM accueil_colle co\
                       INNER JOIN accueil_creneau cr\
                       ON co.creneau_id = cr.id\
                       INNER JOIN accueil_classe cl\
                       ON cr.classe_id = cl.id\
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
                       OR co.eleve_id IS NULL AND co.groupe_id IS NULL AND co.classe_id = e.classe_id\
                       LEFT OUTER JOIN (SELECT ps.semaine_id, sub.matiere_id, sub.classe_id, sub.titre, sub.detail, sub.fichier FROM accueil_programme_semaine ps\
                       INNER JOIN accueil_programme sub\
                       ON ps.programme_id = sub.id) p\
                       ON p.semaine_id = s.id AND p.matiere_id = m.id AND p.classe_id = %s\
                       WHERE e.id=%s AND s.lundi >= %s\
                       ORDER BY s.lundi,cr.jour,cr.heure".format(date_plus_jour('s.lundi','cr.jour'))
            with connection.cursor() as cursor:
                cursor.execute(requete,(eleve.classe.pk,eleve.pk,date.today()+timedelta(days=-28)))
                colles = dictfetchall(cursor)
            requete2 = "SELECT s.lundi lundi, s.numero, {} jour, pl.heure heure, pl.salle salle, m.nom nom_matiere, m.couleur couleur, u.first_name prenom, u.last_name nom, pl.commentaire titre \
                       FROM accueil_planche pl\
                       INNER JOIN accueil_matiere m\
                       ON pl.matiere_id = m.id\
                       INNER JOIN accueil_semaine s\
                       ON pl.semaine_id=s.id\
                       INNER JOIN accueil_colleur c\
                       ON pl.colleur_id=c.id\
                       INNER JOIN accueil_user u\
                       ON u.colleur_id=c.id\
                       WHERE pl.eleve_id=%s\
                       ORDER BY s.lundi,pl.jour,pl.heure".format(date_plus_jour('s.lundi','pl.jour'))
            with connection.cursor() as cursor:
                cursor.execute(requete2,(eleve.pk,))
                colles2 = dictfetchall(cursor)
            return sorted(colles + colles2, key = lambda x:(x['numero'], x['jour'],x['heure']))

    def agendaEleveApp(self,eleve):
        if eleve.classe.semestres:
            semestre2 = Config.objects.get_config().semestre2
            requete = "SELECT s.numero, {} jour, cr.heure heure, cr.salle salle, m.nom nom_matiere, m.couleur couleur, u.first_name prenom, u.last_name nom, p.id id_programme\
                       FROM accueil_colle co\
                       INNER JOIN accueil_creneau cr\
                       ON co.creneau_id = cr.id\
                       INNER JOIN accueil_classe cl\
                       ON cr.classe_id = cl.id\
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
                       ON (s.numero < %s AND e.groupe_id = g.id AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id))\
                       OR (s.numero >= %s AND e.groupe2_id = g.id AND ((cl.option1_id IS NULL OR m.id != cl.option1_id) AND (cl.option2_id IS NULL OR m.id != cl.option2_id) OR e.option_id = m.id) AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id))\
                       OR e.id=co.eleve_id\
                       OR co.eleve_id IS NULL AND co.groupe_id IS NULL AND co.classe_id = e.classe_id\
                       LEFT OUTER JOIN (SELECT ps.semaine_id, sub.matiere_id, sub.classe_id, sub.titre, sub.detail, sub.fichier, sub.id FROM accueil_programme_semaine ps\
                       INNER JOIN accueil_programme sub\
                       ON ps.programme_id = sub.id) p\
                       ON p.semaine_id = s.id AND p.matiere_id = m.id AND p.classe_id = %s\
                       WHERE e.id=%s AND s.lundi >= %s\
                       ORDER BY s.lundi,cr.jour,cr.heure".format(date_plus_jour('s.lundi','cr.jour'))
            with connection.cursor() as cursor:
                cursor.execute(requete,(semestre2, semestre2, eleve.classe.pk,eleve.pk,date.today()+timedelta(days=-28)))
                colles = dictfetchall(cursor)
        else:
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
                       OR co.eleve_id IS NULL AND co.groupe_id IS NULL AND co.classe_id = e.classe_id\
                       LEFT OUTER JOIN (SELECT ps.semaine_id, sub.matiere_id, sub.classe_id, sub.titre, sub.detail, sub.fichier, sub.id FROM accueil_programme_semaine ps\
                       INNER JOIN accueil_programme sub\
                       ON ps.programme_id = sub.id) p\
                       ON p.semaine_id = s.id AND p.matiere_id = m.id AND p.classe_id = %s\
                       WHERE e.id=%s AND s.lundi >= %s\
                       ORDER BY s.lundi,cr.jour,cr.heure".format(date_plus_jour('s.lundi','cr.jour'))
            with connection.cursor() as cursor:
                cursor.execute(requete,(eleve.classe.pk,eleve.pk,date.today()+timedelta(days=-28)))
                colles = dictfetchall(cursor)
        requete2 = "SELECT s.numero, {} jour, pl.heure heure, pl.salle salle, m.nom nom_matiere, m.couleur couleur, u.first_name prenom, u.last_name nom, pl.commentaire commentaire\
                       FROM accueil_planche pl\
                       INNER JOIN accueil_matiere m\
                       ON pl.matiere_id = m.id\
                       INNER JOIN accueil_semaine s\
                       ON pl.semaine_id=s.id\
                       INNER JOIN accueil_colleur c\
                       ON pl.colleur_id=c.id\
                       INNER JOIN accueil_user u\
                       ON u.colleur_id=c.id\
                       WHERE pl.eleve_id=%s\
                       ORDER BY s.lundi,pl.jour,pl.heure".format(date_plus_jour('s.lundi','pl.jour'))
        with connection.cursor() as cursor:
            cursor.execute(requete2,(eleve.pk,))
            colles2 = dictfetchall(cursor)
        return sorted([{'time': int(datetime.combine(agenda['jour'], time(*divmod(agenda['heure'],60))).replace(tzinfo=timezone.utc).timestamp()),
                                     'room':agenda['salle'],
                                     'week':agenda['numero'],
                                     'subject':agenda['nom_matiere'],
                                     'color':agenda['couleur'],
                                     'colleur':agenda['prenom'].title() + " " + agenda['nom'].upper(),
                                     'program':agenda['id_programme'],
                                     'commentaire':""
                                     } for agenda in colles]+[{'time': int(datetime.combine(agenda['jour'], time(*divmod(agenda['heure'],60))).replace(tzinfo=timezone.utc).timestamp()),
                                     'room':agenda['salle'],
                                     'week':agenda['numero'],
                                     'subject':agenda['nom_matiere'],
                                     'color':agenda['couleur'],
                                     'colleur':agenda['prenom'].title() + " " + agenda['nom'].upper(),
                                     'program':None,
                                     'commentaire':agenda['commentaire']
                                     } for agenda in colles2],key=lambda x:x['time'])

    def compatEleve(self,id_classe):
        classe = get_object_or_404(Classe, pk=id_classe)
        if classe.semestres:
            semestre2 = Config.objects.get_config().semestre2
            requete = "SELECT COUNT(DISTINCT co.id) nbColles, COUNT(g.id), s.numero numero, cr.jour jour, cr.heure heure, u.first_name prenom, u.last_name nom\
            FROM accueil_colle co\
            INNER JOIN accueil_semaine s\
            ON co.semaine_id = s.id\
            LEFT OUTER JOIN accueil_groupe g\
            ON co.groupe_id = g.id\
            LEFT OUTER JOIN accueil_matiere m\
            ON co.matiere_id = m.id\
            INNER JOIN accueil_creneau cr\
            ON co.creneau_id = cr.id\
            LEFT OUTER JOIN accueil_classe cl\
            ON cr.classe_id = cl.id\
            INNER JOIN accueil_eleve e\
            ON (s.numero < %s AND e.groupe_id = g.id AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id))\
            OR (s.numero >= %s AND e.groupe2_id = g.id AND ((cl.option1_id IS NULL OR m.id != cl.option1_id) AND (cl.option2_id IS NULL OR m.id != cl.option2_id) OR e.option_id = m.id) AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id))\
            OR e.id=co.eleve_id\
            INNER JOIN accueil_user u\
            ON u.eleve_id = e.id\
            WHERE cr.classe_id=%s\
            GROUP BY s.numero, cr.jour, cr.heure, u.first_name, u.last_name\
            HAVING COUNT(DISTINCT co.id) > 1\
            ORDER BY s.numero, cr.jour, cr.heure, u.first_name, u.last_name"
            with connection.cursor() as cursor:
                cursor.execute(requete,(semestre2, semestre2, id_classe))
                incompat = dictfetchall(cursor)
        else:
            requete = "SELECT COUNT(DISTINCT co.id) nbColles, COUNT(g.id), s.numero numero, cr.jour jour, cr.heure heure, u.first_name prenom, u.last_name nom\
            FROM accueil_colle co\
            LEFT OUTER JOIN accueil_groupe g\
            ON co.groupe_id = g.id\
            LEFT OUTER JOIN accueil_matiere m\
            ON co.matiere_id = m.id\
            INNER JOIN accueil_creneau cr\
            ON co.creneau_id = cr.id\
            LEFT OUTER JOIN accueil_classe cl\
            ON cr.classe_id = cl.id\
            INNER JOIN accueil_eleve e\
            ON e.groupe_id = g.id AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id) OR e.id=co.eleve_id\
            INNER JOIN accueil_semaine s\
            ON co.semaine_id = s.id\
            INNER JOIN accueil_user u\
            ON u.eleve_id = e.id\
            WHERE cr.classe_id=%s\
            GROUP BY s.numero, cr.jour, cr.heure, u.first_name, u.last_name\
            HAVING COUNT(DISTINCT co.id) > 1\
            ORDER BY s.numero, cr.jour, cr.heure, u.first_name, u.last_name"
            with connection.cursor() as cursor:
                cursor.execute(requete,(id_classe,))
                incompat = dictfetchall(cursor)
        return incompat

    def compatColleur(self,id_classe):
        classe = get_object_or_404(Classe, pk=id_classe)
        if classe.semestres:
            semestre2 = Config.objects.get_config().semestre2
            requete = "SELECT COUNT(DISTINCT e.id) nbeleves, COUNT(g.id), s.numero numero, cr.jour jour, cr.heure heure, u.first_name prenom, u.last_name nom\
            FROM accueil_colle co\
            INNER JOIN accueil_semaine s\
            ON co.semaine_id = s.id\
            LEFT OUTER JOIN accueil_groupe g\
            ON co.groupe_id = g.id\
            LEFT OUTER JOIN accueil_matiere m\
            ON co.matiere_id = m.id\
            INNER JOIN accueil_creneau cr\
            ON co.creneau_id = cr.id\
            INNER JOIN accueil_colleur col\
            ON co.colleur_id = col.id\
            LEFT OUTER JOIN accueil_classe cl\
            ON cr.classe_id = cl.id\
            INNER JOIN accueil_eleve e\
            ON (s.numero < %s AND e.groupe_id = g.id AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id))\
            OR (s.numero >= %s AND e.groupe2_id = g.id AND ((cl.option1_id IS NULL OR m.id != cl.option1_id) AND (cl.option2_id IS NULL OR m.id != cl.option2_id) OR e.option_id = m.id) AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id))\
            OR e.id=co.eleve_id\
            INNER JOIN accueil_user u\
            ON u.colleur_id = col.id\
            WHERE cr.classe_id=%s AND m.temps = 20\
            GROUP BY s.numero, cr.jour, cr.heure, u.first_name, u.last_name\
            HAVING COUNT(DISTINCT e.id) > 3\
            ORDER BY s.numero, cr.jour, cr.heure, u.first_name, u.last_name"
            with connection.cursor() as cursor:
                cursor.execute(requete,(semestre2, semestre2, id_classe))
                incompat = dictfetchall(cursor)
        else:
            requete = "SELECT COUNT(DISTINCT e.id) nbeleves, COUNT(g.id), s.numero numero, cr.jour jour, cr.heure heure, u.first_name prenom, u.last_name nom\
            FROM accueil_colle co\
            LEFT OUTER JOIN accueil_groupe g\
            ON co.groupe_id = g.id\
            LEFT OUTER JOIN accueil_matiere m\
            ON co.matiere_id = m.id\
            INNER JOIN accueil_creneau cr\
            ON co.creneau_id = cr.id\
            INNER JOIN accueil_colleur col\
            ON co.colleur_id = col.id\
            LEFT OUTER JOIN accueil_classe cl\
            ON cr.classe_id = cl.id\
            INNER JOIN accueil_eleve e\
            ON e.groupe_id = g.id AND (m.lv=0 OR m.lv=1 AND e.lv1_id=m.id OR m.lv=2 AND e.lv2_id=m.id) OR e.id=co.eleve_id\
            INNER JOIN accueil_semaine s\
            ON co.semaine_id = s.id\
            INNER JOIN accueil_user u\
            ON u.colleur_id = col.id\
            WHERE cr.classe_id=%s  AND m.temps = 20\
            GROUP BY s.numero, cr.jour, cr.heure, u.first_name, u.last_name\
            HAVING COUNT(DISTINCT co.id) > 1\
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

