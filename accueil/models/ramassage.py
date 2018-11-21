from django.db import models, transaction, connection
from django.shortcuts import get_object_or_404
from django.http import Http404
from datetime import date, timedelta
from django.db.models.functions import Lower
from django.db.models import Count, Sum, Q, Min, Max
from .note import Note
from .autre import dictfetchall
from .classe import Classe
from .semaine import Semaine
from .colleur import Colleur
from .matiere import Matiere
from ecolle.settings import BDD


def mois():
    """Renvoie les mois min et max des semaines de colle. Renvoie le mois courant en double si aucune semaine n'est définie"""
    try:
        moisMin=Semaine.objects.aggregate(Min('lundi'))
        moisMax=Semaine.objects.aggregate(Max('lundi'))
        moisMin=date(moisMin['lundi__min'].year+moisMin['lundi__min'].month//12,moisMin['lundi__min'].month%12+1,1)-timedelta(days=1) # dernier jour du mois
        moisMax=moisMax['lundi__max']+timedelta(days=5)
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
        requete = "SELECT co.id id_colleur, ma.id id_matiere, cl.id id_classe, SUM(ma.temps) \
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
        GROUP BY co.id, ma.id, cl.id".format(1 if BDD == "sqlite3" else "TRUE")
        with connection.cursor() as cursor:
            cursor.execute(requete,(moisFin,))
            with transaction.atomic():
                ramassage.save() # on sauvegarde le ramassage pour le créer ou mettre à jour sa date/heure
                Decompte.objects.filter(pk=ramassage.pk).delete() # on efface le décompte précédent si c'est une maj du ramassage/decompte
                for row in cursor.fetchall(): # on -re-crée le décompte
                    Decompte.objects.create(colleur_id=row[0],matiere_id=row[1],classe_id=row[2],ramassage_id=ramassage.pk,temps=row[3])

    def decompteRamassage(self, ramassage, csv = True, parClasse = True):
        """Renvoie, pour chaque classe, la liste des colleurs avec leur nombre d'heures de colle entre les mois moisMin et moisMax, s'ils en ont effectué"""
        if Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).exists(): # s'il existe un ramassage antérieur
            mois = Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).aggregate(Max('moisFin'))['moisFin__max']
            ramassage_precedent = Ramassage.objects.get(moisFin = mois) # on récupère le ramassage précédent
            # pas de FULL OUTER JOIN avec MySQL, donc on bidouille avec jointure externe à gauche / à droite et un UNION ALL
            requete = "SELECT u.last_name nom, u.first_name prenom, col.id colleur_id, ma.id matiere_id, ma.nom matiere_nom, cl.id classe_id, cl.nom classe_nom, cl.annee,\
            col.grade, COALESCE(et.nom, 'Inconnu') etab, col.etablissement_id etab_id, COALESCE(dec2.temps,0) - COALESCE(dec1.temps,0) heures\
            FROM accueil_decompte dec1\
            LEFT OUTER JOIN accueil_decompte dec2\
            ON dec1.colleur_id = dec2.colleur_id AND dec1.classe_id = dec2.classe_id AND dec1.matiere_id = dec2.matiere_id\
            AND dec1.ramassage_id = %s AND dec2.ramassage_id=%s\
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
            WHERE COALESCE(dec2.temps,0) - COALESCE(dec1.temps,0) > 0\
            UNION ALL SELECT u.last_name, u.first_name, col.id colleur_id, ma.id matiere_id, ma.nom matiere_nom, cl.id classe_id, cl.nom, cl.annee,\
            col.grade, COALESCE(et.nom, 'Inconnu') etab, col.etablissement_id etab_id, COALESCE(dec2.temps,0) - COALESCE(dec1.temps,0) heures\
            FROM accueil_decompte dec2\
            LEFT OUTER JOIN accueil_decompte dec1\
            ON dec1.colleur_id = dec2.colleur_id AND dec1.classe_id = dec2.classe_id AND dec1.matiere_id = dec2.matiere_id\
            AND dec1.ramassage_id = %s AND dec2.ramassage_id=%s\
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
            WHERE dec1.id = NULL\
            AND COALESCE(dec2.temps,0) - COALESCE(dec1.temps,0) > 0\
            ORDER BY annee, classe_nom, matiere_nom, etab, grade, nom, prenom;"
            with connection.cursor() as cursor:
                cursor.execute(requete,(ramassage_precedent.pk,ramassage.pk,ramassage_precedent.pk,ramassage.pk))
                decomptes = dictfetchall(cursor)
        else: # si c'est le premier ramassage:
            requete = "SELECT u.last_name nom, u.first_name prenom, col.id colleur_id, ma.id matiere_id, ma.nom matiere_nom, cl.id classe_id, cl.nom classe_nom, cl.annee,\
            col.grade, COALESCE(et.nom, 'Inconnu') etab, col.etablissement_id etab_id, COALESCE(dec1.temps,0) heures\
            FROM accueil_decompte dec1\
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
            WHERE  dec1.ramassage_id = %s\
            AND COALESCE(dec1.temps,0) > 0\
            ORDER BY annee, classe_nom, matiere_nom, etab, grade, nom, prenom;"
            with connection.cursor() as cursor:
                cursor.execute(requete,(ramassage.pk,))
                decomptes = dictfetchall(cursor)
        if csv and parClasse: # si on note par classe pour un csv
            return decomptes
        LISTE_GRADES=["inconnu","certifié","bi-admissible","agrégé","chaire sup"]
        if not parClasse: # si on note par annee/effectif pour un csv ou un pdf
            LISTE_GRADES=["inconnu","certifié","bi-admissible","agrégé","chaire sup"]
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
            if len(decomptes) > 0:
                lastMatiere, lastEtab, lastGrade, lastColleur = decomptes[0]['matiere_nom'], decomptes[0]['etab'], decomptes[0]['grade'], (decomptes[0]['nom'], decomptes[0]['prenom'])
            nbEtabs=nbGrades=nbColleurs=1
            listeDecompte, listeEtablissements, listeGrades, listeColleurs, listeTemps= [], [], [], [], [0]*nb_decompte
            for decompte in decomptes:
            #for matiere, etab, grade, nom, prenom, classe, temps in decomptes:
                if decompte['matiere_nom']!=lastMatiere: # si on change de matière
                    listeColleurs.append((lastColleur[0].upper(),lastColleur[1].title(),listeTemps))
                    listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                    listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                    listeDecompte.append((lastMatiere,listeEtablissements,nbEtabs))
                    listeTemps,listeColleurs,listeGrades,listeEtablissements=[0]*nb_decompte,[],[],[]
                    nbColleurs=nbGrades=nbEtabs=1
                elif decompte['etab']!=lastEtab: # si on change d'établissement mais pas de matière
                    listeColleurs.append((lastColleur[0].upper(),lastColleur[1].title(),listeTemps))
                    listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                    listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                    listeTemps,listeColleurs,listeGrades=[0]*nb_decompte,[],[]
                    nbColleurs=nbGrades=1
                    nbEtabs+=1
                elif lastGrade!=decompte['grade']: # si on change de grade, mais pas d'établissement ni de matière
                    listeColleurs.append((lastColleur[0].upper(),lastColleur[1].title(),listeTemps))
                    listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                    listeTemps,listeColleurs=[0]*nb_decompte,[]
                    nbColleurs=1
                    nbEtabs+=1
                    nbGrades+=1
                elif (decompte['nom'],decompte['prenom'])!=lastColleur: # si on change de colleur, mais pas de grade, ni d'établissement, ni de matière
                    listeColleurs.append((lastColleur[0].upper(),lastColleur[1].title(),listeTemps))
                    listeTemps=[0]*nb_decompte
                    nbColleurs+=1
                    nbGrades+=1
                    nbEtabs+=1
                listeTemps[effectifs_classe[decompte['classe_id']]]+= decompte['heures']
                lastColleur, lastGrade, lastEtab, lastMatiere = (decompte['nom'], decompte['prenom']), decompte['grade'], decompte['etab'], decompte['matiere_nom']
                listeColleurs.append((lastColleur[0].upper(),lastColleur[1].title(),listeTemps))
                listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                listeDecompte.append((lastMatiere,listeEtablissements,nbEtabs))
            effectifs= list(zip([1]*3+[2]*3,["eff<20","20≤eff≤35","eff>35"]*2))
            effectifs = [x for x,boolean in zip(effectifs,effectif_classe) if boolean is not False]
            return listeDecompte,effectifs
        else: # si on note par classe pour un pdf
            listeMatieres, listeDecompte, listeEtablissements, listeGrades, listeColleurs = [], [], [], [], []
            if len(decomptes) > 0:
                lastClasse, lastMatiere, lastEtab, lastGrade, lastColleur, lastTemps = decomptes[0]['classe_nom'], decomptes[0]['matiere_nom'], decomptes[0]['etab'], decomptes[0]['grade'], (decomptes[0]['nom'], decomptes[0]['prenom']), decomptes[0]['heures']
                nbMatieres = nbEtabs = nbGrades = nbColleurs=1
                for decompte in decomptes:
                    if decompte['classe_nom'] != lastClasse: # si on change de classe
                        listeColleurs.append((lastColleur,lastTemps))
                        listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                        listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                        listeDecompte.append((lastMatiere,listeEtablissements,nbEtabs))
                        listeMatieres.append((lastClasse,listeDecompte,nbMatieres))
                        listeDecompte,listeColleurs,listeGrades,listeEtablissements = [], [], [], []
                        nbMatieres=nbColleurs=nbGrades=nbEtabs=1
                    elif decompte['matiere_nom']!=lastMatiere: # si on change de matière
                        listeColleurs.append((lastColleur,lastTemps))
                        listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                        listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                        listeDecompte.append((lastMatiere,listeEtablissements,nbEtabs))
                        listeColleurs,listeGrades,listeEtablissements = [], [], []
                        nbColleurs=nbGrades=nbEtabs=1
                        nbMatieres+=1
                    elif decompte['etab']!=lastEtab: # si on change d'établissement mais pas de matière
                        listeColleurs.append((lastColleur,lastTemps))
                        listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                        listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                        listeColleurs,listeGrades = [],[]
                        nbColleurs=nbGrades=1
                        nbEtabs+=1
                        nbMatieres+=1
                    elif lastGrade!=decompte['grade']: # si on change de grade, mais pas d'établissement ni de matière
                        listeColleurs.append((lastColleur,lastTemps))
                        listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                        listeColleurs=[]
                        nbColleurs=1
                        nbEtabs+=1
                        nbGrades+=1
                        nbMatieres+=1
                    elif (decompte['nom'],decompte['prenom'])!=lastColleur: # si on change de colleur, mais pas de grade, ni d'établissement, ni de matière
                        listeColleurs.append((lastColleur,lastTemps))
                        nbColleurs+=1
                        nbGrades+=1
                        nbEtabs+=1
                        nbMatieres+=1
                    lastColleur, lastGrade, lastEtab, lastMatiere, lastTemps = (decompte['nom'],decompte['prenom']), decompte['grade'], decompte['etab'], decompte['matiere_nom'], decompte['heures']
                    listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),lastTemps))
                    listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                    listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                    listeDecompte.append((lastMatiere,listeEtablissements,nbEtabs))
                    listeMatieres.append((lastClasse,listeDecompte,nbMatieres))
            return listeMatieres

    def decompte(self,moisMin,moisMax):
        """Renvoie la liste des colleurs avec leur nombre d'heures de colle entre les mois moisMin et moisMax, trié par année/effectif de classe"""
        LISTE_GRADES=["inconnu","certifié","bi-admissible","agrégé","chaire sup"]
        compte = Note.objects.filter(date_colle__range=(moisMin,moisMax)).annotate(nom_matiere=Lower('matiere__nom')).values_list('nom_matiere','colleur__etablissement__nom','colleur__grade','colleur__user__last_name','colleur__user__first_name','classe__id').order_by('nom_matiere','colleur__etablissement__nom','colleur__grade','colleur__user__last_name','colleur__user__first_name').annotate(temps=Sum('matiere__temps'))
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
        lastMatiere = lastEtab = lastGrade = lastColleur = False
        nbEtabs=nbGrades=nbColleurs=1
        listeDecompte, listeEtablissements, listeGrades, listeColleurs, listeTemps= [], [], [], [], [0]*nb_decompte
        for matiere, etab, grade, nom, prenom, classe, temps in compte:
            if lastMatiere and matiere!=lastMatiere: # si on change de matière
                listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),listeTemps))
                listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                listeDecompte.append((lastMatiere,listeEtablissements,nbEtabs))
                listeTemps,listeColleurs,listeGrades,listeEtablissements=[0]*nb_decompte,[],[],[]
                nbColleurs=nbGrades=nbEtabs=1
            elif lastEtab is not False and etab!=lastEtab: # si on change d'établissement mais pas de matière
                listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),listeTemps))
                listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                listeTemps,listeColleurs,listeGrades=[0]*nb_decompte,[],[]
                nbColleurs=nbGrades=1
                nbEtabs+=1
            elif lastGrade and lastGrade!=grade: # si on change de grade, mais pas d'établissement ni de matière
                listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),listeTemps))
                listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                listeTemps,listeColleurs=[0]*nb_decompte,[]
                nbColleurs=1
                nbEtabs+=1
                nbGrades+=1
            elif lastColleur and (nom,prenom)!=lastColleur: # si on change de colleur, mais pas de grade, ni d'établissement, ni de matière
                listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),listeTemps))
                listeTemps=[0]*nb_decompte
                nbColleurs+=1
                nbGrades+=1
                nbEtabs+=1
            listeTemps[effectifs_classe[classe]]+=temps
            lastColleur, lastGrade, lastEtab, lastMatiere = (nom,prenom), grade, etab, matiere
        if lastColleur:
            listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),listeTemps))
            listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
            listeEtablissements.append((lastEtab,listeGrades,nbGrades))
            listeDecompte.append((lastMatiere,listeEtablissements,nbEtabs))
        effectifs= list(zip([1]*3+[2]*3,["eff<20","20≤eff≤35","eff>35"]*2))
        effectifs = [x for x,boolean in zip(effectifs,effectif_classe) if boolean is not False]
        return listeDecompte,effectifs

class Ramassage(models.Model):
    def incremente_mois(moment):
        """ajoute un mois à moment"""
        moment += timedelta(days=1)
        return date(moment.year+moment.month//12,moment.month%12+1,1) - timedelta(days=1)
    moisMin,moisMax=mois()
    moiscourant=moisMin
    LISTE_MOIS =[moiscourant]
    moiscourant=incremente_mois(moiscourant)
    while moiscourant<=moisMax:
        LISTE_MOIS.append(moiscourant)
        moiscourant=incremente_mois(moiscourant)
    LISTE_MOIS=[(x,x.strftime('%B %Y')) for x in LISTE_MOIS]
    moisFin = models.DateField(verbose_name="Jusqu'à (inclus)",choices=LISTE_MOIS, unique = True, blank = False)
    date = models.DateTimeField(auto_now = True)
    objects = RamassageManager()

    class Meta:
        ordering=['moisFin']

class Decompte(models.Model):
    colleur = models.ForeignKey("Colleur", on_delete = models.PROTECT, null = False)
    matiere = models.ForeignKey("Matiere", on_delete = models.PROTECT, null = False)
    classe = models.ForeignKey("Classe", on_delete = models.PROTECT, null = False)
    ramassage = models.ForeignKey(Ramassage, on_delete = models.CASCADE, null = False)
    temps = models.PositiveSmallIntegerField(default = 0)

    class Meta:
        unique_together=('colleur','classe','matiere','ramassage')