from django.db import models, transaction, connection
from django.http import Http404
from datetime import date, timedelta
from django.db.models.functions import Lower
from django.db.models import Count, Sum, Min, Max
from .note import Note, array2tree
from .classe import Classe
from .semaine import Semaine
from ecolle.settings import BDD

def totalMois(arg):
    if BDD == 'postgresql' or BDD == 'postgresql_psycopg2' or BDD == 'mysql' or BDD == 'oracle':
        return "EXTRACT(YEAR FROM {0})*12 + EXTRACT(MONTH FROM {0}) -1".format(arg)
    elif BDD == 'sqlite3':
        return "strftime('%Y',{0})*12+strftime('%m',{0})-1".format(arg)
    else:
        return "" # à compléter par ce qu'il faut dans le cas ou vous utilisez 
                  # un SGBD qui n'est ni mysql, ni postgresql, ni sqlite ni oracle

def mois():
    """Renvoie les mois min et max (+1 mois) des semaines de colle. Renvoie le mois courant en double si aucune semaine n'est définie"""
    try:
        moisMin=Semaine.objects.aggregate(Min('lundi'))
        moisMax=Semaine.objects.aggregate(Max('lundi'))
        moisMin=date(moisMin['lundi__min'].year+moisMin['lundi__min'].month//12,moisMin['lundi__min'].month%12+1,1)-timedelta(days=1) # dernier jour du mois
        moisMax=moisMax['lundi__max']+timedelta(days=35)
        moisMax=date(moisMax.year+moisMax.month//12,moisMax.month%12+1,1)-timedelta(days=1) # dernier jour du mois
    except Exception:
        hui=date.today()
        moisMin=moisMax=date(hui.year+hui.month//12,hui.month%12+1,1)-timedelta(days=1)
    return moisMin,moisMax


class RamassageManager(models.Manager):
    def createOrUpdate(self, moisFin):
        """crée ou met à jour le ramassage dont le mois de fin est moisFin puis crée le décompte associé"""
        if self.filter(moisFin__gt=moisFin).exists(): # s'il existe un ramassage postérieur, erreur 404 (ça ne doit pas arriver, sauf bidouille)
                raise Http404
        if self.filter(moisFin=moisFin).exists(): # s'il existe déjà un ramassage pour ce mois
            ramassage = self.get(moisFin = moisFin) # on le récupère
        else:
            ramassage = Ramassage(moisFin = moisFin) # sinon on le crée
        requete = "SELECT co.id id_colleur, ma.id id_matiere, cl.id id_classe, {} moisTotal, SUM(ma.temps) \
        FROM accueil_colleur co\
        INNER JOIN accueil_user u\
        ON u.colleur_id = co.id\
        INNER JOIN accueil_colleur_classes cocl\
        ON co.id = cocl.colleur_id\
        INNER JOIN accueil_classe cl\
        ON cocl.classe_id = cl.id\
        INNER JOIN accueil_colleur_matieres coma\
        ON coma.colleur_id = co.id\
        INNER JOIN accueil_matiere ma\
        ON coma.matiere_id = ma.id\
        INNER JOIN accueil_classe_matieres clma\
        ON clma.classe_id = cl.id AND clma.matiere_id = ma.id\
        LEFT OUTER JOIN accueil_note no\
        ON no.colleur_id = co.id AND no.matiere_id = ma.id AND no.classe_id = cl.id\
        WHERE u.is_active = {} AND no.date_colle <= %s\
        GROUP BY co.id, ma.id, cl.id, moisTotal".format(totalMois("no.date_colle"),1 if BDD == "sqlite3" else "TRUE")
        with connection.cursor() as cursor:
            cursor.execute(requete,(moisFin,))
            with transaction.atomic():
                ramassage.save() # on sauvegarde le ramassage pour le créer ou mettre à jour sa date/heure
                Decompte.objects.filter(pk=ramassage.pk).delete() # on efface le décompte précédent si c'est une maj du ramassage/decompte
                for row in cursor.fetchall(): # on -re-crée le décompte
                    Decompte.objects.create(colleur_id=row[0],matiere_id=row[1],classe_id=row[2],ramassage_id=ramassage.pk, mois=row[3] ,temps=row[4])

    def decompteRamassage(self, ramassage, csv = True, parClasse = True, parMois = False):
        """Renvoie, pour chaque classe, la liste des colleurs avec leur nombre d'heures de colle entre les mois moisMin et moisMax, s'ils en ont effectué"""
        if Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).exists(): # s'il existe un ramassage antérieur
            mois = Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).aggregate(Max('moisFin'))['moisFin__max']
            ramassage_precedent = Ramassage.objects.get(moisFin = mois) # on récupère le ramassage précédent
            ramassage_precedent_pk = ramassage_precedent.pk
        else:
            ramassage_precedent_pk = 0
        # pas de FULL OUTER JOIN avec MySQL, donc on bidouille avec jointure externe à gauche / à droite et un UNION ALL
        requete = "SELECT cl.id classe_id, cl.nom classe_nom, cl.annee, ma.nom matiere_nom, COALESCE(et.nom, 'Inconnu') etab, col.grade, u.last_name nom, u.first_name prenom, col.id colleur_id,\
        dec2.mois mois, SUM(dec2.temps) - COALESCE(SUM(dec1.temps),0) heures\
        FROM accueil_decompte dec2\
        LEFT OUTER JOIN accueil_decompte dec1\
        ON dec1.colleur_id = dec2.colleur_id AND dec1.classe_id = dec2.classe_id AND dec1.matiere_id = dec2.matiere_id\
        AND dec1.mois = dec2.mois AND dec1.ramassage_id = %s\
        INNER JOIN accueil_colleur col\
        ON dec2.colleur_id = col.id\
        INNER JOIN accueil_classe cl\
        ON dec2.classe_id = cl.id\
        INNER JOIN accueil_matiere ma\
        ON dec2.matiere_id = ma.id\
        INNER JOIN accueil_user u\
        ON u.colleur_id = col.id\
        LEFT OUTER JOIN accueil_etablissement et\
        ON col.etablissement_id = et.id\
        WHERE dec2.ramassage_id=%s AND dec2.temps - COALESCE(dec1.temps,0) > 0\
        GROUP BY ma.nom, u.last_name, u.first_name, col.id, cl.id, et.nom, dec2.mois\
        UNION ALL SELECT cl.id classe_id, cl.nom classe_nom, cl.annee, ma.nom matiere_nom, COALESCE(et.nom, 'Inconnu') etab, col.grade, u.last_name nom, u.first_name prenom, col.id colleur_id,\
        dec1.mois mois, - COALESCE(SUM(dec1.temps),0) heures\
        FROM accueil_decompte dec1\
        LEFT OUTER JOIN accueil_decompte dec2\
        ON dec1.colleur_id = dec2.colleur_id AND dec1.classe_id = dec2.classe_id AND dec1.matiere_id = dec2.matiere_id\
        AND dec1.mois = dec2.mois AND dec2.ramassage_id=%s\
        INNER JOIN accueil_colleur col\
        ON dec1.colleur_id = col.id\
        INNER JOIN accueil_classe cl\
        ON dec1.classe_id = cl.id\
        INNER JOIN accueil_matiere ma\
        ON dec1.matiere_id = ma.id\
        INNER JOIN accueil_user u\
        ON u.colleur_id = col.id\
        LEFT OUTER JOIN accueil_etablissement et\
        ON col.etablissement_id = et.id\
        WHERE dec2.id = NULL AND dec1.ramassage_id = %s\
        GROUP BY ma.nom, u.last_name, u.first_name, col.id, cl.id, et.nom, dec1.mois"
        if parMois:
            requete = "SELECT * FROM ({}) as req\
            ORDER BY {} req.matiere_nom, req.etab, req.grade, req.nom, req.prenom, req.mois".format(requete, "req.annee, req.classe_nom, " if parClasse else "")
        else:
            requete = "SELECT  req.classe_id, req.classe_nom, req.annee, req.matiere_nom, req.etab, req.grade, req.nom, req.prenom, req.colleur_id, \
            SUM(req.heures) heures FROM ({}) as req\
            GROUP BY req.classe_id, req.classe_nom, req.annee, req.matiere_nom, req.etab, req.grade, req.nom, req.prenom, req.colleur_id\
            ORDER BY {}req.matiere_nom, req.etab, req.grade, req.nom, req.prenom".format(requete, "req.annee, req.classe_nom, " if parClasse else "")
        with connection.cursor() as cursor:
            cursor.execute(requete,(ramassage_precedent_pk,ramassage.pk,ramassage.pk,ramassage_precedent_pk))
            decomptes = cursor.fetchall()
        LISTE_GRADES=["inconnu","certifié","bi-admissible","agrégé","chaire sup"]
        if not parClasse: # si on note par annee/effectif pour un csv ou un pdf
            classes = Classe.objects.annotate(eleve_compte=Count('classeeleve'))
            effectif_classe = [False]*6
            for classe in classes:
                effectif_classe[int(20<=classe.eleve_compte<=35)+2*int(35<classe.eleve_compte)+3*classe.annee-3]=True
            nb_decompte = sum([int(value) for value in effectif_classe])
            j=0
            for i in range(6):
                if effectif_classe[i]:
                    effectif_classe[i]=j
                    j+=1
            effectifs_classe = {classe.pk:effectif_classe[int(20<=classe.eleve_compte<=35)+2*int(35<classe.eleve_compte)+3*classe.annee-3] for classe in classes}
            decomptes2 = []
            if decomptes:
                if parMois:
                    lastMatiere, lastColleur, lastMois = decomptes[0][3], decomptes[0][8], decomptes[0][9] # nom de la matière et id du colleur
                    decomptes2.append(decomptes[0][3:-1] + ([0]*nb_decompte,))
                    for ligne in decomptes: # on va sommer les heures par année/effectif
                        if not(ligne[3] == lastMatiere and ligne[8] == lastColleur and ligne and ligne[9] == lastMois): # si on change pas de colleur, on rajoute une ligne
                            lastMatiere, lastColleur, lastMois = ligne[3], ligne[8], ligne[9]
                            decomptes2.append(ligne[3:-1] + ([0]*nb_decompte,))
                        decomptes2[-1][-1][effectifs_classe[ligne[0]]] += ligne[-1]
                else:
                    lastMatiere, lastColleur = decomptes[0][3], decomptes[0][8] # nom de la matière et id du colleur
                    decomptes2.append(decomptes[0][3:-1] + ([0]*nb_decompte,))
                    for ligne in decomptes: # on va sommer les heures par année/effectif
                        if not(ligne[3] == lastMatiere and ligne[8] == lastColleur and ligne): # si on change pas de colleur, on rajoute une ligne
                            lastMatiere, lastColleur = ligne[3], ligne[8]
                            decomptes2.append(ligne[3:-1] + ([0]*nb_decompte,))
                        decomptes2[-1][-1][effectifs_classe[ligne[0]]] += ligne[-1]
            effectifs= list(zip([1]*3+[2]*3,["eff<20","20≤eff≤35","eff>35"]*2))
            effectifs = [x for x,boolean in zip(effectifs,effectif_classe) if boolean is not False]
            if csv:
                return decomptes2, effectifs
            if parMois:
                profondeurs = [1,1,1,3,2]
                funcs = [lambda t:t, lambda t:t,lambda x:(LISTE_GRADES[x[0]],),lambda x:("{} {}".format(x[1].title(),x[0].upper()),),lambda t:t]
            else:
                profondeurs = [1,1,1,4]
                funcs = [lambda t:t, lambda t:t,lambda x:(LISTE_GRADES[x[0]],),lambda x:("{} {}".format(x[1].title(),x[0].upper()),x[3])]
            return array2tree(decomptes2,profondeurs,funcs), effectifs
        else: # si on note par classe
            if csv : # si on note par classe pour un csv
                return decomptes
            # si on note par classe pour un pdf
            if parMois:
                profondeurs = [3,1,1,1,3,2]
                funcs = [lambda x:(x[1],), lambda t:t, lambda t:t,lambda x:(LISTE_GRADES[x[0]],),lambda x:("{} {}".format(x[1].title(),x[0].upper()),), lambda t:t]
            else:
                profondeurs = [3,1,1,1,4]
                funcs = [lambda x:(x[1],), lambda t:t, lambda t:t,lambda x:(LISTE_GRADES[x[0]],),lambda x:("{} {}".format(x[1].title(),x[0].upper()),x[3]), lambda t:t[0]]
            return array2tree(decomptes,profondeurs,funcs)

    def decompte(self,moisMin,moisMax):
        """Renvoie la liste des colleurs avec leur nombre d'heures de colle entre les mois moisMin et moisMax, trié par année/effectif de classe"""
        LISTE_GRADES=["inconnu","certifié","bi-admissible","agrégé","chaire sup"]
        decomptes = list(Note.objects.filter(date_colle__range=(moisMin,moisMax)).annotate(nom_matiere=Lower('matiere__nom')).values_list('nom_matiere','colleur__etablissement__nom','colleur__grade','colleur__user__last_name','colleur__user__first_name','classe__id','colleur__id').order_by('nom_matiere','colleur__etablissement__nom','colleur__grade','colleur__user__last_name','colleur__user__first_name').annotate(temps=Sum('matiere__temps')))
        classes = Classe.objects.annotate(eleve_compte=Count('classeeleve'))
        effectif_classe = [False]*6
        for classe in classes:
            effectif_classe[int(20<=classe.eleve_compte<=35)+2*int(35<classe.eleve_compte)+3*classe.annee-3]=True
        nb_decompte = sum([int(value) for value in effectif_classe])
        j=0
        for i in range(6):
            if effectif_classe[i]:
                effectif_classe[i]=j
                j+=1
        effectifs_classe = {classe.pk:effectif_classe[int(20<=classe.eleve_compte<=35)+2*int(35<classe.eleve_compte)+3*classe.annee-3] for classe in classes}
        decomptes2 = []
        if decomptes:
            lastMatiere, lastColleur = decomptes[0][0], decomptes[0][6] # nom de la matière et id du colleur
            decomptes2.append(decomptes[0][:-1] + ([0]*nb_decompte,))
            for ligne in decomptes: # on va sommer les heures par année/effectif
                if not(ligne[0] == lastMatiere and ligne[6] == lastColleur and ligne): # si on change pas de colleur, on rajoute une ligne
                    lastMatiere, lastColleur = ligne[0], ligne[6]
                    decomptes2.append(ligne[0:-1] + ([0]*nb_decompte,))
                decomptes2[-1][-1][effectifs_classe[ligne[5]]] += ligne[-1]
        profondeurs = [1,1,1,5]
        funcs = [lambda t:t, lambda t: ["Inconnu"] if t[0] is None else t, lambda t:[LISTE_GRADES[t[0]]], lambda t:("{} {}".format(t[1].title(),t[0].upper()),t[4])]
        listeDecompte = array2tree(decomptes2, profondeurs, funcs)
        effectifs= list(zip([1]*3+[2]*3,["eff<20","20≤eff≤35","eff>35"]*2))
        effectifs = [x for x,boolean in zip(effectifs,effectif_classe) if boolean is not False]
        return listeDecompte,effectifs

class Ramassage(models.Model):
    moisFin = models.DateField(verbose_name="Jusqu'à (inclus)", unique = True, blank = False)
    date = models.DateTimeField(auto_now = True)
    objects = RamassageManager()

    class Meta:
        ordering=['moisFin']

class Decompte(models.Model):
    colleur = models.ForeignKey("Colleur", on_delete = models.CASCADE, null = False)
    matiere = models.ForeignKey("Matiere", on_delete = models.PROTECT, null = False)
    classe = models.ForeignKey("Classe", on_delete = models.PROTECT, null = False)
    ramassage = models.ForeignKey(Ramassage, on_delete = models.CASCADE, null = False)
    temps = models.PositiveSmallIntegerField(default = 0)
    mois = models.PositiveSmallIntegerField(default = 0)

    class Meta:
        unique_together=('colleur','classe','matiere','ramassage','mois')
