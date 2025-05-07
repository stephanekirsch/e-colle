# -*- coding:utf8 -*-
from django.db import models, connection
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
import os
from ecolle.settings import MEDIA_ROOT, IMAGEMAGICK, BDD, \
                            HEURE_DEBUT, HEURE_FIN, INTERVALLE
from PIL import Image
from django.db.models import Sum, F
from random import choice
from .contenttype import ContentTypeRestrictedFileField
from ckeditor.fields import RichTextField
from .eleve import Eleve

semaine = ["lundi", "mardi","mercredi","jeudi","vendredi","samedi","dimanche"]

def texte_aleatoire(taille):
    return "".join(choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789") for i in range(taille))

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


class Creneau(models.Model):
    LISTE_HEURE=[(i,"{}h{:02d}".format(i//60,(i%60))) for i in range(HEURE_DEBUT,HEURE_FIN,INTERVALLE)] 
        # une heure est représentée par le nombre de minutes depuis
        # minuit
    LISTE_JOUR=enumerate(["lundi","mardi","mercredi","jeudi","vendredi","samedi"])
    jour = models.PositiveSmallIntegerField(choices=LISTE_JOUR,default=0)
    heure = models.PositiveSmallIntegerField(choices=LISTE_HEURE,default=480)
    salle = models.CharField(max_length=20,null=True,blank=True)
    classe = models.ForeignKey("Classe",related_name="classecreneau", on_delete=models.PROTECT)

    class Meta:
        ordering=['jour','heure','salle','pk']

    def __str__(self):
        return "{}/{}/{}h{:02d}".format(self.classe.nom,semaine[self.jour],self.heure//60,(self.heure%60))

class Programme(models.Model):
    def update_name(instance, filename):
        return "programme/prog" + texte_aleatoire(20) + ".pdf"
    semaine = models.ManyToManyField("Semaine",verbose_name="Semaine(s)",blank=False)
    classe = models.ForeignKey("Classe",related_name="classeprogramme",on_delete=models.PROTECT)
    matiere = models.ForeignKey("Matiere",related_name="matiereprogramme",on_delete=models.PROTECT)
    titre = models.CharField(max_length = 50)
    detail = models.TextField(verbose_name="Détails",null=True,blank=True)
    fichier = ContentTypeRestrictedFileField(verbose_name="Fichier(pdf)",upload_to=update_name,null=True,blank=True,content_types=["application/pdf"], max_upload_size=5000000)

    def __str__(self):
        return self.titre.title()

class FerieManager(models.Manager):
    def recupFerie(self,jour,semaine,duree,frequence,modulo):
        requete = "SELECT COUNT(jf.id) \
            FROM accueil_semaine s \
            INNER JOIN accueil_jourferie jf \
            ON {} = %s \
            WHERE s.numero >= %s AND s.numero < %s AND s.numero %% %s = %s".format(date_moins_date('jf.date','s.lundi'))
        with connection.cursor() as cursor:
            cursor.execute(requete,(jour,semaine.numero,semaine.numero+duree,frequence,modulo))
            nbferies=cursor.fetchone()
        return nbferies

class JourFerie(models.Model):
    date=models.DateField(unique=True)
    nom=models.CharField(max_length=30)
    objects = FerieManager()

class Information(models.Model):
    expediteur = models.PositiveSmallIntegerField(verbose_name = "Expéditeur", choices = [(1,"Administrateur"), (2,"Secrétariat")], default = 1)
    destinataire = models.PositiveSmallIntegerField(verbose_name = "destinataires", choices = [(1,"Colleurs"),(2,"Élèves"),(3,"Tout le monde")])
    date = models.DateTimeField(auto_now_add=True)
    message = RichTextField(config_name='custom', blank = True, null = True)

class Message(models.Model):
    def update_name(instance, filename):
        return "pj/pj{}.{}".format(texte_aleatoire(20), filename.split(".")[-1])
    date = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey("User", null=True, on_delete=models.CASCADE, related_name="messagesenvoyes")
    hasAuteur = models.BooleanField(default=True)
    luPar = models.TextField(verbose_name="lu par: ")
    listedestinataires = models.TextField(verbose_name="Liste des destinataires")
    titre = models.CharField(max_length=100)
    corps = RichTextField(max_length=2000,blank = True, null = True)
    pj = ContentTypeRestrictedFileField(verbose_name="Pièce jointe",upload_to=update_name,null=True,blank=True,content_types=["text/plain", "text/csv", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "image/jpeg", "image/png", "application/vnd.oasis.opendocument.presentation",
        "application/vnd.oasis.opendocument.spreadsheet", "application/vnd.oasis.opendocument.text", "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation" , "application/x-rar-compressed", "application/rtf",
        "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/pdf", "application/zip", "application/x-7z-compressed"], max_upload_size=5000000)

class Destinataire(models.Model):
    message = models.ForeignKey(Message,related_name="messagerecu",on_delete=models.CASCADE)
    user=models.ForeignKey("User",related_name="destinataire",on_delete=models.CASCADE)
    lu= models.BooleanField(default=False)
    reponses = models.PositiveSmallIntegerField(default=0)

@receiver(post_delete, sender=Programme)
def programme_post_delete_function(sender, instance, **kwargs):
    if instance.fichier and instance.fichier.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.fichier.name)
        if os.path.isfile(fichier):
            os.remove(fichier)
        if IMAGEMAGICK:
            image = os.path.join(MEDIA_ROOT,"image"+instance.fichier.name[9:-3]+"jpg")
            if os.path.isfile(image):
                os.remove(image)

@receiver(post_save, sender=Programme) # après une sauvegarde/modification de programme
def programme_post_save_function(sender, instance, **kwargs):
    try:
        nomfichier=instance.fichier.name # on récupère le nom du fichier joint
        if IMAGEMAGICK and nomfichier: # si le fichier existe et qu'on fait des mini images
            nomimage=os.path.join(MEDIA_ROOT,"image"+instance.fichier.name[9:-3]+"jpg") # on récupère le nom de l'éventuelle image correspondante, lève une exception s'il n'y a pas de pdf car replace n'est pas une méthode de NoneType
            if not os.path.isfile(nomimage): # si l'image n'existe pas
                # on convertit la première page du pdf en jpg (échoue avec une exception s'il n'y pas pas de pdf ou si imagemagick n'est pas installé)
                os.system("convert -density 200 "+os.path.join(MEDIA_ROOT,nomfichier)+"[0] "+nomimage)  
                os.system("convert -resize 50% "+nomimage+" "+nomimage)
    except Exception: # Dans le cas ou plus aucun fichier n'est lié au programme, exception silencieuse
        pass

@receiver(post_save, sender=Eleve)
def eleve_post_save_function(sender, instance, **kwargs):
    if instance.photo and os.path.isfile(os.path.join(MEDIA_ROOT,instance.photo.name)):  # si il y a une photo
        image=Image.open(os.path.join(MEDIA_ROOT,instance.photo.name))
        taille=image.size
        if taille != (300,400):# si la taille n'est pas déjà la bonne:
            try:
                ratio=taille[0]/taille[1]
            except Exception:
                ratio=.75
            if ratio>.75:
                image=image.resize((int(ratio*400),400))
                abscisse=(image.size[0]-300)//2
                image=image.crop((abscisse,0,abscisse+300,400))
            elif ratio<.75:
                image=image.resize((300,int(300/ratio)))
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

@receiver(post_delete, sender=Message)
def eleve_post_delete_function(sender, instance, **kwargs):
    if instance.pj and instance.pj.name is not None:
        fichier=os.path.join(MEDIA_ROOT,instance.pj.name)
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
            ON n1.matiere_id=m.id AND n1.semestre = 1 AND n1.eleve_id = e.id AND n1.cube = e.cube\
            LEFT OUTER JOIN accueil_noteects n2\
            ON n2.matiere_id=m.id AND n2.semestre = 2 AND n2.eleve_id = e.id AND n2.cube = e.cube\
            WHERE m.classe_id=%s AND e.classe_id=%s AND m.id=%s\
            ORDER BY u.last_name,u.first_name"
            with connection.cursor() as cursor:
                cursor.execute(requete,(classe.pk,classe.pk,matiere.pk))
                notes = dictfetchall(cursor)
            listeNotes.append(notes)
        requete = "SELECT DISTINCT e.id id_eleve, u.first_name prenom,u.last_name nom, n.note note\
            FROM accueil_eleve e\
            INNER JOIN accueil_user u\
            ON u.eleve_id=e.id\
            LEFT OUTER JOIN accueil_noteglobaleects n\
            ON n.eleve_id = e.id AND n.annee = %s\
            WHERE e.classe_id=%s\
            ORDER BY u.last_name,u.first_name"
        with connection.cursor() as cursor:
            cursor.execute(requete,(classe.annee,classe.pk,))
            notes = dictfetchall(cursor)
        if classe.annee == 2:
            requete = "SELECT DISTINCT e.id id_eleve, u.first_name prenom,u.last_name nom, n.note note\
            FROM accueil_eleve e\
            INNER JOIN accueil_user u\
            ON u.eleve_id=e.id\
            LEFT OUTER JOIN accueil_noteglobaleects n\
            ON n.eleve_id = e.id AND n.annee = 1\
            WHERE e.classe_id=%s\
            ORDER BY u.last_name,u.first_name"
            with connection.cursor() as cursor:
                cursor.execute(requete,(classe.pk,))
                notesbis = dictfetchall(cursor)
            requete2 = "SELECT DISTINCT e.id id_eleve, u.first_name prenom,u.last_name nom, n.note note\
            FROM accueil_eleve e\
            INNER JOIN accueil_user u\
            ON u.eleve_id=e.id\
            LEFT OUTER JOIN accueil_noteglobaleects n\
            ON n.eleve_id = e.id AND n.annee = 3\
            WHERE e.classe_id=%s\
            ORDER BY u.last_name,u.first_name"
            with connection.cursor() as cursor:
                cursor.execute(requete2,(classe.pk,))
                notester = dictfetchall(cursor)
        if listeNotes:
            if classe.annee == 1:
                return False, list(zip(zip(*[note for note in listeNotes]), notes))
            else:
                return False, list(zip(zip(*[note for note in listeNotes]), notes, notesbis, notester))
        if classe.annee == 1:
            return True, [notes]
        return False, zip(notes,notesbis)

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
        ON ne1.eleve_id = e.id AND ne1.semestre =1 AND ne1.matiere_id=%s AND ne1.cube = e.cube\
        LEFT OUTER JOIN accueil_noteects ne2\
        ON ne2.eleve_id = e.id AND ne2.semestre =2 AND ne2.matiere_id=%s AND ne2.cube = e.cube\
        WHERE me.id=%s\
        ORDER BY u.last_name,u.first_name"
        with connection.cursor() as cursor:
            cursor.execute(requete,(tuple([eleve.pk for eleve in listeEleves]),matiere.pk,matiere.pk,matiere.pk))
            notes = dictfetchall(cursor)
        return notes

    def notePDF(self,eleve):
        if eleve.classe is None:
            return [],[]
        if eleve.classe.annee == 1:
            notes = list(NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=1).values_list('matiere__nom','matiere__precision','matiere__semestre1','matiere__semestre2','note').order_by('semestre','matiere__nom'))
            semestre1 = NoteECTS.objects.filter(eleve=eleve,semestre=1).count()
            ng = NoteGlobaleECTS.objects.filter(annee=1,eleve=eleve)
            return notes[:semestre1], notes[semestre1:], None if not ng.exists() else ng[0].note
        elif eleve.classe.annee == 2 and not eleve.cube:
            notes = list(NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=1).values_list('matiere__nom','matiere__precision','matiere__semestre1','matiere__semestre2','note').order_by('semestre','matiere__nom'))
            semestre1 = NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=1,semestre=1).distinct().count()
            notes2 = list(NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=2,cube=False).values_list('matiere__nom','matiere__precision','matiere__semestre1','matiere__semestre2','note').order_by('semestre','matiere__nom'))
            semestre3 = NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=2,semestre=1,cube=False).distinct().count()
            ng1 = NoteGlobaleECTS.objects.filter(annee=1,eleve=eleve)
            ng2 = NoteGlobaleECTS.objects.filter(annee=2,eleve=eleve)
            return notes[:semestre1], notes[semestre1:], None if not ng1.exists() else ng1[0].note, notes2[:semestre3], notes2[semestre3:], None if not ng2.exists() else ng2[0].note
        else:
            notes = list(NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=1).values_list('matiere__nom','matiere__precision','matiere__semestre1','matiere__semestre2','note').order_by('semestre','matiere__nom'))
            semestre1 = NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=1,semestre=1).distinct().count()
            notes2 = list(NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=2,cube=False).values_list('matiere__nom','matiere__precision','matiere__semestre1','matiere__semestre2','note').order_by('semestre','matiere__nom'))
            semestre3 = NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=2,semestre=1,cube=False).distinct().count()
            notes3 = list(NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=2,cube=True).values_list('matiere__nom','matiere__precision','matiere__semestre1','matiere__semestre2','note').order_by('semestre','matiere__nom'))
            semestre5 = NoteECTS.objects.filter(eleve=eleve,matiere__classe__annee=2,semestre=1,cube=True).distinct().count()
            ng1 = NoteGlobaleECTS.objects.filter(annee=1,eleve=eleve)
            ng2 = NoteGlobaleECTS.objects.filter(annee=2,eleve=eleve)
            ng3 = NoteGlobaleECTS.objects.filter(annee=3,eleve=eleve)
            return notes[:semestre1], notes[semestre1:], None if not ng1.exists() else ng1[0].note, notes2[:semestre3], notes2[semestre3:], None if not ng2.exists() else ng2[0].note, notes3[:semestre5], notes3[semestre5:], None if not ng3.exists() else ng3[0].note



    def moyenneECTS(self,eleve,cube=False):
        if not eleve.classe: return 0
        annee = eleve.classe.annee + eleve.cube
        sem1,sem2,ng1,sem3,sem4,ng2,sem5,sem6,ng3 = self.notePDF(eleve)
        sp=0 # variable qui va contenir la somme pondérée des notes en vue du calcul de la mention globale
        coeff = 0 # somme des coeffs pour vérifier si on en a 60 au total
        if ng1 is not None: # si note globale pour la première année, on écrase le reste pour le calcul de la moyenne
            coeff = 60
            sp = 60*ng1
        else:
            if sem1:
                for note in sem1:
                    sp+=note[2]*note[4]
                    if note[4] !=5:
                        coeff+=note[2]
            if sem2:
                for note in sem2:
                    sp+=note[3]*note[4]
                    if note[4] !=5:
                        coeff+=note[3]
        if annee == 1:
            return round(sp1/60)
        if ng2 is not None: # si note globale pour la deuxième année, on écrase le reste pour le calcul de la moyenne
            coeff2 = 60
            sp2 = 60*ng2
        elif annee == 2 or annee == 3 and cube:
                coeff2 = 0
                sp2 = 0
                if sem3:
                    for note in sem3:
                        sp2+=note[2]*note[4]
                        if note[4] !=5:
                            coeff2+=note[2]
                if sem4:
                    for note in sem4:
                        sp2+=note[3]*note[4]
                        if note[4] !=5:
                            coeff2+=note[3]
        elif annee == 3 and not cube:
            coeff2 = 0
            sp2 = 0
            if sem5:
                for note in sem5:
                    sp2+=note[2]*note[4]
                    if note[4] !=5:
                        coeff2+=note[2]
            if sem6:
                for note in sem6:
                    sp2+=note[3]*note[4]
                    if note[4] !=5:
                        coeff2+=note[3]
        if annee == 2 or annee == 3 and not cube:
            if ng2 is not None:
                return ng2
            else:
                return round((sp2+sp)/120)
        else:
            if ng3 is not None: # si note globale pour la deuxième année, on écrase le reste pour le calcul de la moyenne
                return ng3
            coeff3 = 0
            sp3 = 0
            if sem5:
                for note in sem5:
                    sp3+=note[2]*note[4]
                    if note[4] !=5:
                        coeff3+=note[2]
            if sem6:
                for note in sem6:
                    sp3+=note[3]*note[4]
                    if note[4] !=5:
                        coeff3+=note[3]
       
            if ng2 is not None:
                return round((sp3+120*ng2)/180)
            elif coeff3 == coeff2 == coeff1 == 60:
                return round((sp3+sp2+sp)/180)
            else:
                return round(sp3/60)


    def credits(self,classe):
        if BDD == 'mysql': # la double jointure externe sur même table semble bugger avec mysql, donc j'ai mis un SUM(CASE ....) pour y remédier.
            requete = "SELECT u.first_name prenom, u.last_name nom, e.id, e.ddn, e.ldn, e.ine, SUM(CASE WHEN ne.semestre = 1 THEN m.semestre1 ELSE 0 END) sem1, ng.note note,\
            SUM(CASE WHEN ne.semestre = 2 THEN m.semestre2 ELSE 0 END) sem2\
            FROM accueil_classe cl\
            INNER JOIN accueil_eleve e\
            ON e.classe_id=cl.id\
            INNER JOIN accueil_user u\
            ON u.eleve_id=e.id\
            LEFT OUTER JOIN accueil_noteects ne\
            ON ne.eleve_id = e.id AND ne.note != 5 AND ne.cube = e.cube\
            LEFT OUTER JOIN accueil_matiereects m\
            ON ne.matiere_id = m.id AND m.classe_id = cl.id\
            LEFT OUTER JOIN accueil_noteglobaleects ng\
            ON ((ng.annee = 3 AND e.cube) OR (ng.annee = cl.annee)) AND ng.eleve_id = e.id\
            WHERE cl.id = %s\
            GROUP BY u.last_name, u.first_name, e.id, e.ddn, e.ldn, e.ine, ng.note\
            ORDER BY u.last_name, u.first_name"
        else: # avec sqlite ou postgresql pas de bug! (probablement avec oracle aussi)
            requete = "SELECT u.first_name prenom, u.last_name nom, e.id, e.ddn, e.ldn, e.ine, SUM(m1.semestre1) sem1, SUM(m2.semestre2) sem2, ng.note note\
            FROM accueil_classe cl\
            INNER JOIN accueil_eleve e\
            ON e.classe_id=cl.id\
            INNER JOIN accueil_user u\
            ON u.eleve_id=e.id\
            LEFT OUTER JOIN accueil_noteects ne\
            ON ne.eleve_id = e.id AND ne.note != 5 AND ne.cube = e.cube\
            LEFT OUTER JOIN accueil_matiereects m1\
            ON ne.matiere_id = m1.id AND ne.semestre = 1 AND m1.classe_id = cl.id\
            LEFT OUTER JOIN accueil_matiereects m2\
            ON ne.matiere_id = m2.id AND ne.semestre = 2 AND m2.classe_id = cl.id\
            LEFT OUTER JOIN accueil_noteglobaleects ng\
            ON ((ng.annee = 3 AND e.cube) OR (ng.annee = cl.annee)) AND ng.eleve_id = e.id\
            WHERE cl.id = %s\
            GROUP BY u.last_name, u.first_name, e.id, e.ddn, e.ldn, e.ine, ng.note\
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
            elif credit['note'] is None:
                attest = 0
            if credit['sem2'] == 30:
                total[4]+=1
            elif credit['note'] is None:
                attest = 0
            total[5] += attest
        return credits,total


class NoteECTS(models.Model):
    eleve = models.ForeignKey(Eleve,verbose_name="Élève",on_delete=models.CASCADE)
    matiere = models.ForeignKey(MatiereECTS,on_delete=models.CASCADE)
    semestre = models.PositiveSmallIntegerField(verbose_name="semestre",choices=((1,'1er semestre'),(2,'2ème semestre')))
    note = models.PositiveSmallIntegerField(choices=enumerate("ABCDEF"))
    cube = models.BooleanField(verbose_name="cube", default=False)
    objects=NoteECTSManager()

    class Meta:
        unique_together=(('eleve','matiere','semestre','cube'))

class NoteGlobaleECTSManager(models.Manager):
    def noteEleves(self,classe,annee,listeEleves):
        requete = "SELECT u.first_name prenom, u.last_name nom, n.note note_globale\
        FROM accueil_eleve e\
        INNER JOIN accueil_user u\
        ON u.eleve_id=e.id\
        LEFT OUTER JOIN accueil_noteglobaleects n\
        ON n.eleve_id = e.id AND n.annee=%s \
        WHERE e.classe_id=%s AND e.id IN %s\
        ORDER BY u.last_name,u.first_name"
        with connection.cursor() as cursor:
            cursor.execute(requete,(annee, classe.pk, tuple([eleve.pk for eleve in listeEleves])))
            notes = dictfetchall(cursor)
        return notes

class NoteGlobaleECTS(models.Model):
    eleve = models.ForeignKey(Eleve,verbose_name="Élève",on_delete=models.CASCADE)
    annee = models.PositiveSmallIntegerField(verbose_name="année",choices=((1,'1ère année'),(2,'2ème année'),(3,'3eme année'))) 
    note = models.PositiveSmallIntegerField(choices=enumerate("ABCDEF"))
    objects=NoteGlobaleECTSManager()
