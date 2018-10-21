from django.db import models
from datetime import date, timedelta
from django.db.models.functions import Lower
from django.db.models import Count, Sum, Q
from .note import Note
from .classe import Classe
from .semaine import Semaine


def mois():
    """Renvoie les mois min et max des semaines de colle. Renvoie le mois courant en double si aucune semaine n'est définie"""
    try:
        moisMin=Semaine.objects.aggregate(Min('lundi'))
        moisMax=Semaine.objects.aggregate(Max('lundi'))
        moisMin=date(moisMin['lundi__min'].year,moisMin['lundi__min'].month,1)
        moisMax=moisMax['lundi__max']+timedelta(days=5)
        moisMax=date(moisMax.year+moisMax.month//12,moisMax.month%12+1,1)-timedelta(days=1)
    except Exception:
        hui=date.today()
        moisMin=moisMax=date(hui.year,hui.month,1)
    return moisMin,moisMax

class RamassageManager(models.Manager):
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

    def decompteParClasse(self,moisMin,moisMax):
        """Renvoie, pour chaque classe, la liste des colleurs avec leur nombre d'heures de colle entre les mois moisMin et moisMax, s'ils en ont effectué"""
        LISTE_GRADES=["inconnu","certifié","bi-admissible","agrégé","chaire sup"]
        classes = Classe.objects.all()
        listeClasses = []
        for classe in classes:
            compte = Note.objects.filter(date_colle__range=(moisMin, moisMax)).filter( Q(classe=classe.pk) | Q(eleve__classe = classe.pk) | Q(eleve__groupe__classe=classe.pk) ).annotate(nom_matiere=Lower('matiere__nom')).values_list('nom_matiere','colleur__etablissement__nom','colleur__grade','colleur__user__last_name','colleur__user__first_name').order_by('nom_matiere','colleur__etablissement__nom','colleur__grade','colleur__user__last_name','colleur__user__first_name').annotate(temps=Sum('matiere__temps'))
            lastMatiere = lastEtab = lastGrade = lastColleur = lastTemps = False
            nbEtabs=nbGrades=nbColleurs=1
            listeDecompte, listeEtablissements, listeGrades, listeColleurs = [], [], [], [] 
            for matiere, etab, grade, nom, prenom, temps in compte:
                if lastMatiere and matiere!=lastMatiere: # si on change de matière
                    listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),lastTemps))
                    listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                    listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                    listeDecompte.append((lastMatiere,listeEtablissements,nbEtabs))
                    listeColleurs,listeGrades,listeEtablissements = [], [], []
                    nbColleurs=nbGrades=nbEtabs=1
                elif lastEtab is not False and etab!=lastEtab: # si on change d'établissement mais pas de matière
                    listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),lastTemps))
                    listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                    listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                    listeColleurs,listeGrades = [],[]
                    nbColleurs=nbGrades=1
                    nbEtabs+=1
                elif lastGrade and lastGrade!=grade: # si on change de grade, mais pas d'établissement ni de matière
                    listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),lastTemps))
                    listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                    listeColleurs=[]
                    nbColleurs=1
                    nbEtabs+=1
                    nbGrades+=1
                elif lastColleur and (nom,prenom)!=lastColleur: # si on change de colleur, mais pas de grade, ni d'établissement, ni de matière
                    listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),lastTemps))
                    nbColleurs+=1
                    nbGrades+=1
                    nbEtabs+=1
                lastColleur, lastGrade, lastEtab, lastMatiere, lastTemps = (nom,prenom), grade, etab, matiere, temps
            if lastColleur:
                listeColleurs.append(("{} {}".format(lastColleur[1].title(),lastColleur[0].upper()),lastTemps))
                listeGrades.append((LISTE_GRADES[lastGrade],listeColleurs,nbColleurs))
                listeEtablissements.append((lastEtab,listeGrades,nbGrades))
                listeDecompte.append((lastMatiere,listeEtablissements,nbEtabs))
            listeClasses.append(listeDecompte)
        return listeClasses, classes



class Ramassage(models.Model):
    def incremente_mois(moment):
        """ajoute un mois à moment"""
        return date(moment.year+moment.month//12,moment.month%12+1,1)
    moisMin,moisMax=mois()
    moiscourant=moisMin
    LISTE_MOIS =[moiscourant]
    moiscourant=incremente_mois(moiscourant)
    while moiscourant<moisMax:
        LISTE_MOIS.append(moiscourant)
        moiscourant=incremente_mois(moiscourant)
    LISTE_MOIS=[(x,x.strftime('%B %Y')) for x in LISTE_MOIS]
    moisDebut = models.DateField(verbose_name='Début',choices=LISTE_MOIS)
    moisFin = models.DateField(verbose_name='Fin',choices=LISTE_MOIS)
    objects = RamassageManager()

    class Meta:
        unique_together=('moisDebut','moisFin')
        ordering=['moisDebut','moisFin']
