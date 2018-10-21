# -*- coding:utf8 -*-
from django.db import models, connection
from django.contrib.auth.models import AbstractUser
from datetime import date, timedelta, datetime, time
from django.utils import timezone
from django.db.models.signals import post_delete, post_save
from django.db import transaction
from django.dispatch import receiver
import os
from ecolle.settings import MEDIA_ROOT, IMAGEMAGICK, BDD, \
                            HEURE_DEBUT, HEURE_FIN, INTERVALLE
from PIL import Image
from django.db.models import Count, Avg, Min, Max, Sum, F, Q, StdDev
from django.db.models.functions import Lower, Upper, Concat, Substr

from .eleve import Eleve
from .note import Note
from .classe import Classe

semaine = ["lundi", "mardi","mercredi","jeudi","vendredi","samedi","dimanche"]

def dictfetchall(cursor):
    """Renvoie les lignes du curseur sous forme de dictionnaire"""
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def date_plus_jour(dateSQL, jourSQL):
    """Renvoie une chaîne de caractères correspondant à la syntaxe SQL 
    qui permet d'ajouter un objet de type date, dateSQL, avec un nombre 
    de jours, jourSQL"""
    if BDD == 'postgresql' or BDD == 'postgresql_psycopg2' or BDD == 'oracle':
        return "{}+{}".format(dateSQL, jourSQL)
    elif BDD == 'mysql':
        return "{} + INTERVAL {} DAY".format(dateSQL, jourSQL)
    elif BDD == 'sqlite3':
        return "date({},'+{} days')".format(dateSQL, jourSQL)
    else:
        return "" # à compléter par ce qu'il faut dans le cas ou vous utilisez 
                  # un SGBD qui n'est ni mysql, ni postgresql, ni sqlite ni oracle

def date_moins_date(date1,date2):
    """Renvoie une chaîne de caractères correspondant à la syntaxe SQL
    qui permet de faire la différence date1-date2 en nombre de jours"""
    if BDD == 'postgresql' or BDD == 'postgresql_psycopg2' or BDD == 'oracle':
        return "{}-{}".format(date1, date2)
    elif BDD == 'mysql':
        return "DATEDIFF({},{})".format(date1, date2)
    elif BDD == 'sqlite3':
        return "julianday({})-julianday({})".format(date1, date2)
    else:
        return "" # à compléter par ce qu'il faut dans le cas ou vous utilisez 
                  # un SGBD qui n'est ni mysql, ni postgresql, ni sqlite ni oracle


def group_concat(arg):
    """Renvoie une chaîne de caractères correspondant à la syntaxe SQL 
    qui permet d'utiliser une fonction d'agrégation qui concatène des chaînes"""
    if BDD == 'postgresql' or BDD == 'postgresql_psycopg2':
        return "STRING_AGG(DISTINCT {0:}, ',' ORDER BY {0:})".format(arg)
    elif BDD == 'mysql':
        return "GROUP_CONCAT(DISTINCT {0:} ORDER BY {0:})".format(arg)
    elif BDD == 'sqlite3':
        return "GROUP_CONCAT(DISTINCT {})".format(arg)
    else:
        return "" # à compléter par ce qu'il faut dans le cas ou vous utilisez 
                  # un SGBD qui n'est ni mysql, ni postgresql, ni sqlite













class Creneau(models.Model):
    LISTE_HEURE=[(i,"{}h{:02d}".format(i//60,(i%60))) for i in range(HEURE_DEBUT,HEURE_FIN,INTERVALLE)] 
        # une heure est représentée par le nombre de minutes depuis
        # minuit
    LISTE_JOUR=enumerate(["lundi","mardi","mercredi","jeudi","vendredi","samedi"])
    jour = models.PositiveSmallIntegerField(choices=LISTE_JOUR,default=0)
    heure = models.PositiveSmallIntegerField(choices=LISTE_HEURE,default=24)
    salle = models.CharField(max_length=20,null=True,blank=True)
    classe = models.ForeignKey("Classe",related_name="classecreneau", on_delete=models.PROTECT)

    class Meta:
        ordering=['jour','heure','salle','pk']

    def __str__(self):
        return "{}/{}/{}h{:02d}".format(self.classe.nom,semaine[self.jour],self.heure//60,(self.heure%60))

class Programme(models.Model):
    def update_name(instance, filename):
        return "programme/prog"+str(instance.semaine.pk)+"-"+str(instance.classe.pk)+"-"+str(instance.matiere.pk)+".pdf"
    semaine = models.ForeignKey("Semaine",related_name="semaineprogramme",on_delete=models.PROTECT)
    classe = models.ForeignKey("Classe",related_name="classeprogramme",on_delete=models.PROTECT)
    matiere = models.ForeignKey("Matiere",related_name="matiereprogramme",on_delete=models.PROTECT)
    titre = models.CharField(max_length = 50)
    detail = models.TextField(verbose_name="Détails",null=True,blank=True)
    fichier = models.FileField(verbose_name="Fichier(pdf)",upload_to=update_name,null=True,blank=True)

    class Meta:
        unique_together=('semaine','classe','matiere') # un programme maximum par semaine/classe/matière

    def __str__(self):
        return self.titre.title()




def mois():
    """Renvoie les mois min et max des semaines de colle. Renvoie le mois courant en double si aucune semaine n'est définie"""
    try:
        moisMin=Semaine.objects.aggregate(Min('lundi'))
        moisMax=Semaine.objects.aggregate(Max('lundi'))
        moisMin=date(moisMin['lundi__min'].year,moisMin['lundi__min'].month,1)
        moisMax=moisMax['lundi__max']+timedelta(days=5)
        moisMax=date(moisMax.year+moisMax.month//12,moisMax.month+1,1)-timedelta(days=1)
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

class FerieManager(models.Manager):
    def recupFerie(self,jour,semaine,duree,frequence,modulo):
        requete = "SELECT COUNT(jf.id) \
            FROM accueil_semaine s \
            INNER JOIN accueil_jourferie jf \
            ON {} = %s \
            WHERE s.numero >= %s AND s.numero < %s AND s.numero %% %s = %s".format(date_moins_date('jf.date','s.lundi'))
        with connection.cursor() as cursor:
            cursor.execute(requete,(jour,semaine.numero,semaine.numero+int(duree),frequence,modulo))
            nbferies=cursor.fetchone()
        return nbferies

class JourFerie(models.Model):
    date=models.DateField(unique=True)
    nom=models.CharField(max_length=30)
    objects = FerieManager()

class Message(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey("User",null=True,on_delete=models.SET_NULL,related_name="messagesenvoyes")
    hasAuteur = models.BooleanField(default=True)
    luPar = models.TextField(verbose_name="lu par: ")
    listedestinataires = models.TextField(verbose_name="Liste des destinataires")
    titre = models.CharField(max_length=100)
    corps = models.TextField(max_length=2000)

class Destinataire(models.Model):
    message = models.ForeignKey(Message,related_name="messagerecu",on_delete=models.CASCADE)
    user=models.ForeignKey("User",related_name="destinataire",on_delete=models.CASCADE)
    lu= models.BooleanField(default=False)
    reponses = models.PositiveSmallIntegerField(default=0)

def update_name(programme):
    nomimage=programme.fichier.name.replace('programme','image').replace('pdf','jpg')
    nouveaufichier="programme/prog"+str(programme.semaine.pk)+"-"+str(programme.classe.pk)+"-"+str(programme.matiere.pk)+".pdf"
    nouvelleimage=nouveaufichier.replace('programme','image').replace('pdf','jpg')
    os.rename(os.path.join(MEDIA_ROOT,programme.fichier.name),os.path.join(MEDIA_ROOT,nouveaufichier))
    os.rename(os.path.join(MEDIA_ROOT,nomimage),os.path.join(MEDIA_ROOT,nouvelleimage))
    programme.fichier.name=nouveaufichier
    programme.save()

@receiver(post_delete, sender=Programme)
def programme_post_delete_function(sender, instance, **kwargs):
    if instance.fichier and instance.fichier.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.fichier.name)
        if os.path.isfile(fichier):
            os.remove(fichier)
        if IMAGEMAGICK:
            image=fichier.replace('programme','image').replace('pdf','jpg')
            if os.path.isfile(image):
                os.remove(image)

@receiver(post_save, sender=Programme) # après une sauvegarde/modification de programme
def programme_post_save_function(sender, instance, **kwargs):
    try:
        nomfichier=instance.fichier.name # on récupère le nom du fichier joint
        if IMAGEMAGICK:
            nomimage=nomfichier.replace('programme','image').replace('pdf','jpg') # on récupère le nom de l'éventuelle image correspondante, lève une exception s'il n'y a pas de pdf car replace n'est pas une méthode de NoneType
            if not os.path.isfile(os.path.join(MEDIA_ROOT,nomimage)): # si l'image n'existe pas
                # on convertit la première page du pdf en jpg (échoue avec une exception s'il n'y pas pas de pdf ou si imagemagick n'est pas installé)
                os.system("convert -density 200 "+os.path.join(MEDIA_ROOT,nomfichier)+"[0] "+os.path.join(MEDIA_ROOT,nomimage))  
                os.system("convert -resize 50% "+os.path.join(MEDIA_ROOT,nomimage)+" "+os.path.join(MEDIA_ROOT,nomimage))
        if nomfichier != os.path.join("programme","prog")+str(instance.semaine.pk)+"-"+str(instance.classe.pk)+"-"+str(instance.matiere.pk)+".pdf":
            # si le nom du fichier ne correspond pas à ses caractéristiques (semaine/classe/matière), ce qui signifie qu'un de ces 3 champs a été modifié, on met à jour le nom du fichier.
            update_name(instance)
    except Exception: # Dans le cas ou plus aucun fichier n'est lié au programme, on efface l'éventuel fichier présent avant la modification
        nomfichier = os.path.join(MEDIA_ROOT,"programme","prog")+str(instance.semaine.pk)+"-"+str(instance.classe.pk)+"-"+str(instance.matiere.pk)+".pdf"
        if os.path.isfile(nomfichier): # s'il y a bien un fichier, on l'efface
            os.remove(nomfichier)
        if IMAGEMAGICK:
            nomimage=nomfichier.replace('programme','image').replace('pdf','jpg')
            if os.path.isfile(nomimage): # s'il y a bien un fichier, on l'efface
                os.remove(nomimage)
    
def update_photo(eleve):
    try:
        nomphoto = 'photos/photo_{}.{}'.format(eleve.pk,eleve.photo.name.split(".")[-1].lower())
        os.rename(os.path.join(MEDIA_ROOT,eleve.photo.name),os.path.join(MEDIA_ROOT,nomphoto))
        if nomphoto != eleve.photo.name:
            eleve.photo.name=nomphoto
            eleve.save()
    except Exception:
        eleve.photo=None
        eleve.save()

@receiver(post_save, sender=Eleve)
def eleve_post_save_function(sender, instance, **kwargs):
    if instance.photo:
        update_photo(instance)
    if instance.photo: # si l'exécution de update_photo a effacé la photo
        image=Image.open(os.path.join(MEDIA_ROOT,instance.photo.name))
        taille=image.size
        try:
            ratio=taille[0]/taille[1]
        except Exception:
            ratio=.75
        if ratio>.75:
            image=image.resize((int(ratio*400),400))
            abscisse=(image.size[0]-300)//2
            image=image.crop((abscisse,0,abscisse+300,400))
        elif ratio<.75:
            image=image.resize((300,int(400/ratio)))
            ordonnee=(image.size[1]-400)//2
            image=image.crop((0,ordonnee,300,ordonnee+400))
        else:
            image=image.resize((300,400))
        image.save(os.path.join(MEDIA_ROOT,instance.photo.name))

@receiver(post_delete, sender=Eleve)
def eleve_post_delete_function(sender, instance, **kwargs):
    if instance.photo and instance.photo.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.photo.name)
        if os.path.isfile(fichier):
            os.remove(fichier)

class MatiereECTS(models.Model):
    profs = models.ManyToManyField("Colleur",verbose_name="Professeur", related_name="colleurmatiereECTS",blank=True)
    classe = models.ForeignKey("Classe",verbose_name="Classe", related_name="classematiereECTS",on_delete =models.CASCADE)
    nom = models.CharField(max_length=80,verbose_name="Matière")
    precision = models.CharField(max_length=20,verbose_name="Précision",blank=True) # si plusieurs déclinaisons/coefficients, comme pour les langues, ou les options SI/info/Chimie en MPSI/PCSI
    semestre1 = models.PositiveSmallIntegerField(verbose_name='coefficient semestre 1',choices=enumerate(range(21)),null=True,blank=True)
    semestre2 = models.PositiveSmallIntegerField(verbose_name='coefficient semestre 2',choices=enumerate(range(21)),null=True,blank=True)

    class Meta:
        unique_together=(('classe','nom','precision'))

    def __str__(self):
        if self.precision:
            return "{}({})".format(self.nom.title(),self.precision)
        return self.nom

class NoteECTSManager(models.Manager):
    def note(self,classe,matieres):
        listeNotes=[]
        for matiere in matieres:
            requete="SELECT DISTINCT e.id id_eleve, u.first_name prenom,u.last_name nom, m.nom matiere, m.precision, n1.note note1, n2.note note2\
            FROM accueil_eleve e\
            INNER JOIN accueil_user u\
            ON u.eleve_id=e.id\
            CROSS JOIN accueil_matiereects m\
            INNER JOIN accueil_matiereects_profs mp\
            ON mp.matiereects_id = m.id\
            LEFT OUTER JOIN accueil_noteects n1\
            ON n1.matiere_id=m.id AND n1.semestre = 1 AND n1.eleve_id = e.id\
            LEFT OUTER JOIN accueil_noteects n2\
            ON n2.matiere_id=m.id AND n2.semestre = 2 AND n2.eleve_id = e.id\
            WHERE m.classe_id=%s AND e.classe_id=%s AND m.id=%s\
            ORDER BY u.last_name,u.first_name"
            with connection.cursor() as cursor:
                cursor.execute(requete,(classe.pk,classe.pk,matiere.pk))
                notes = dictfetchall(cursor)
            listeNotes.append(notes)
        return zip(*[note for note in listeNotes])

    def noteEleves(self,matiere,listeEleves):
        requete = "SELECT u.first_name prenom, u.last_name nom, ne1.note semestre1, ne2.note semestre2\
        FROM accueil_matiereects me\
        INNER JOIN accueil_classe cl\
        ON me.classe_id = cl.id\
        INNER JOIN accueil_eleve e\
        ON e.classe_id=cl.id AND e.id IN %s\
        INNER JOIN accueil_user u\
        ON u.eleve_id=e.id\
        LEFT OUTER JOIN accueil_noteects ne1\
        ON ne1.eleve_id = e.id AND ne1.semestre =1 AND ne1.matiere_id=%s\
        LEFT OUTER JOIN accueil_noteects ne2\
        ON ne2.eleve_id = e.id AND ne2.semestre =2 AND ne2.matiere_id=%s\
        WHERE me.id=%s\
        ORDER BY u.last_name,u.first_name"
        with connection.cursor() as cursor:
            cursor.execute(requete,(tuple([eleve.pk for eleve in listeEleves]),matiere.pk,matiere.pk,matiere.pk))
            notes = dictfetchall(cursor)
        return notes

    def notePDF(self,eleve):
        notes = list(NoteECTS.objects.filter(eleve=eleve).values_list('matiere__nom','matiere__precision','matiere__semestre1','matiere__semestre2','note').order_by('semestre','matiere__nom'))
        semestre1 = NoteECTS.objects.filter(eleve=eleve,semestre=1).count()
        return notes[:semestre1],notes[semestre1:]

    def moyenneECTS(self,eleve):
        somme = NoteECTS.objects.filter(eleve=eleve,semestre=1).annotate(notepond=F('note')*F('matiere__semestre1')).aggregate(sp=Sum('notepond'))['sp']
        somme += NoteECTS.objects.filter(eleve=eleve,semestre=2).annotate(notepond=F('note')*F('matiere__semestre2')).aggregate(sp=Sum('notepond'))['sp']
        return int(somme/60+.5)

    def credits(self,classe):
        if BDD == 'mysql': # la double jointure externe sur même table semble bugger avec mysql, donc j'ai mis un SUM(CASE ....) pour y remédier.
            requete = "SELECT u.first_name prenom, u.last_name nom, e.id, e.ddn, e.ldn, e.ine, SUM(CASE WHEN ne.semestre = 1 THEN m.semestre1 ELSE 0 END) sem1,\
            SUM(CASE WHEN ne.semestre = 2 THEN m.semestre2 ELSE 0 END) sem2\
            FROM accueil_classe cl\
            INNER JOIN accueil_eleve e\
            ON e.classe_id=cl.id\
            INNER JOIN accueil_user u\
            ON u.eleve_id=e.id\
            LEFT OUTER JOIN accueil_noteects ne\
            ON ne.eleve_id = e.id AND ne.note != 5\
            LEFT OUTER JOIN accueil_matiereects m\
            ON ne.matiere_id = m.id\
            WHERE cl.id = %s\
            GROUP BY u.last_name, u.first_name, e.id, e.ddn, e.ldn, e.ine\
            ORDER BY u.last_name, u.first_name"
        else: # avec sqlite ou postgresql pas de bug! (probablement avec oracle aussi)
            requete = "SELECT u.first_name prenom, u.last_name nom, e.id, e.ddn, e.ldn, e.ine, SUM(m1.semestre1) sem1, SUM(m2.semestre2) sem2\
            FROM accueil_classe cl\
            INNER JOIN accueil_eleve e\
            ON e.classe_id=cl.id\
            INNER JOIN accueil_user u\
            ON u.eleve_id=e.id\
            LEFT OUTER JOIN accueil_noteects ne\
            ON ne.eleve_id = e.id AND ne.note != 5\
            LEFT OUTER JOIN accueil_matiereects m1\
            ON ne.matiere_id = m1.id AND ne.semestre = 1\
            LEFT OUTER JOIN accueil_matiereects m2\
            ON ne.matiere_id = m2.id AND ne.semestre = 2\
            WHERE cl.id = %s\
            GROUP BY u.last_name, u.first_name, e.id, e.ddn, e.ldn, e.ine\
            ORDER BY u.last_name, u.first_name"
        with connection.cursor() as cursor:
            cursor.execute(requete,(classe.pk,))
            credits = dictfetchall(cursor)
        total = [0]*6
        for credit in credits:
            attest = 1
            if credit['ddn']:
                total[0]+=1
            else:
                attest = 0
            if credit['ldn']:
                total[1]+=1
            else:
                attest = 0
            if credit['ine']:
                total[2]+=1
            else:
                attest = 0
            if credit['sem1'] == 30:
                total[3]+=1
            else:
                attest = 0
            if credit['sem2'] == 30:
                total[4]+=1
            else:
                attest = 0
            total[5] += attest
        return credits,total


class NoteECTS(models.Model):
    eleve = models.ForeignKey(Eleve,verbose_name="Élève",on_delete=models.CASCADE)
    matiere = models.ForeignKey(MatiereECTS,on_delete=models.CASCADE)
    semestre = models.PositiveSmallIntegerField(verbose_name="semestre",choices=((1,'1er semestre'),(2,'2ème semestre')))
    note = models.PositiveSmallIntegerField(choices=enumerate("ABCDEF"))
    objects=NoteECTSManager()

    class Meta:
        unique_together=(('eleve','matiere','semestre'))
