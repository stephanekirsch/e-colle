# -*- coding:utf8 -*-
from django.db import models, connection
from django.contrib.auth.models import AbstractUser
from datetime import date, timedelta, time
import locale
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
import os
from ecolle.settings import MEDIA_ROOT, IMAGEMAGICK, BDD
from django.core.files import File
from PIL import Image
from django.db.models import Count, Avg, Min, Max, F 

semaine = ["lundi", "mardi","mercredi","jeudi","vendredi","samedi","dimanche"]

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def date_plus_jour(dateSQL,jourSQL):
	"""renvoie une chaîne de caractères correspondant à la syntaxe SQL qui permet d'ajouter un objet de type date, dateSQL, avec un nombre de jours, jourSQL"""
	if BDD == 'postgresql' or BDD == 'postgresql_psycopg2' or BDD == 'oracle':
		return "{}+{}".format(dateSQL,jourSQL)
	elif BDD == 'mysql':
		return "{} + INTERVAL {} DAY".format(dateSQL,jourSQL)
	elif BDD == 'sqlite3':
		return "date({},'+{} days')".format(dateSQL,jourSQL)
	else:
		return "" # à compléter par ce qu'il faut dans le cas ou vous utilisez un SGBD qui n'est ni mysql, ni postgresql, ni sqlite ni oracle

def date_moins_date(date1,date2):
	"""renvoie une chaîne de caractères correspondant à la syntaxe SQL qui permet de faire la différence date1-date2 en nombre de jours"""
	if BDD == 'postgresql' or BDD == 'postgresql_psycopg2' or BDD == 'oracle':
		return "{}-{}".format(date1,date2)
	elif BDD == 'mysql':
		return "DATEDIFF({},{})".format(date1,date2)
	elif BDD == 'sqlite3':
		return "julianday({})-julianday({})".format(date1,date2)
	else:
		return "" # à compléter par ce qu'il faut dans le cas ou vous utilisez un SGBD qui n'est ni mysql, ni postgresql, ni sqlite ni oracle

class Matiere(models.Model):
	LISTE_COULEURS=(('#696969',"Gris mat"),('#808080',"Gris"),('#A9A9A9',"Gris foncé"),('#C0C0C0',"Gris argent"),('#D3D3D3',"Gris clair"),('#DCDCDC',"Gris Gainsboro"),('#FFC0CB',"Rose"),('#FFB6C1',"Rose clair"),
		('#FF69B4',"Rose passion"),('#FF1493' ,"Rose profond"),('#DB7093',"Violet Pâle"),('#FF00FF',"Fushia"),('#C71585',"Violet moyen"),('#D8BFD8',"Violet chardon"),('#DDA0DD',"Prune"),('#EE82EE',"Violet"),('#DA70D6',"Orchidée"),
		('#9932CC',"Orchidée foncé"),('#9400D3',"Violet foncé"),('#8A2BE2',"Bleu violet"),('#4B0082',"Indigo"),('#7B68EE',"Bleu ardoise moyen"),('#6A5ACD',"Bleu ardoise"),('#483D8B',"Bleu ardoise foncé"),('#9370DB',"Pourpre moyen"),
		('#8B008B',"Magenta foncé"),('#800080',"Pourpre"),('#BC8F8F',"Brun rosé"),('#F08080',"Corail clair"),('#FF7F50',"Corail"),('#FF6347',"Tomate"),('#FF4500',"Orangé"),('#FF0000',"Rouge"),('#DC143C',"Rouge cramoisi"),('#FFA07A',"Saumon clair"),
		('#E9967A',"Saumon foncé"),('#FA8072',"Saumon"),('#CD5C5C',"Rouge indien"),('#B22222',"Rouge brique"),('#A52A2A',"Marron"),('#8B0000',"Rouge foncé"),('#800000',"Bordeaux"),('#DEB887',"Brun bois"),('#D2B48C',"Brun roux"),('#F4A460',"Brun sable"),
		('#FFA500',"Orange"),('#FF8C00',"Orange foncé"),('#D2691E',"Chocolat"),('#CD853F',"Brun péro"),('#A0522D',"Terre de Sienne"),('#8B4513',"Brun cuir"),('#F0E68C',"Brun kaki"),('#FFFF00',"Jaune"),('#FFD700',"Or"),('#DAA520',"Jaune doré"),('#B8860B',"Jaune doré foncé"),
		('#BDB76B',"Brun kaki foncé"),('#9ACD32',"Jaune vert"),('#6B8E23',"Kaki"),('#808000',"Olive"),('#556B2F',"Olive foncé"),('#ADFF2F',"Vert jaune"),('#7FFF00',"Chartreuse"),('#7CFC00',"Vert prairie"),('#00FF00',"Cirton vert"),('#32CD32',"Citron vers foncé"),
		('#98FB98',"Vert pâle"),('#90EE90',"Vert clair"),('#00FF7F',"Vert printemps"),('#00FA9A',"Vert printemps mpyen"),('#228B22',"Vert forêt"),('#008000',"Vert"),('#006400',"Vert foncé"),('#8FBC8F',"Vert océan foncé"),('#3CB371',"Vert océan moyen"),('#2E8B57',"Vert océan"),
		('#778899',"Gris aroise clair"),('#708090',"Gris ardoise"),('#2F4F4F',"Gris ardoise foncé"),('#7FFFD4',"Aigue-marine"),('#66CDAA',"Aigue-marine moyen"),('#00FFFF',"Cyan"),('#40E0D0',"Turquoise"),('#48D1CC',"Turquoise moyen"),('#00CED1',"Turquoise foncé"),
		('#20B2AA',"Vert marin clair"),('#008B8B',"Cyan foncé"),('#008080',"Vert sarcelle"),('#5F9EA0',"Bleu pétrole"),('#B0E0E6',"Bleu poudre"),('#ADD8E6',"Bleu clair"),('#87CEFA',"Bleu azur clair"),('#87CEEB',"Bleu azur"),('#00BFFF',"Bleu azur profond"),
		('#1E90FF',"Bleu toile"),('#B0C4DE',"Bleu acier clair"),('#6495ED',"Bleuet"),('#4682B4',"Bleu acier"),('#4169E1',"Bleu royal"),('#0000FF',"Bleu"),('#0000CD',"Bleu moyen"),('#00008B',"Bleu foncé"),('#000080',"Bleu marin"),('#191970',"Bleu de minuit"),)
	nom = models.CharField(max_length = 30, unique=True)
	couleur = models.CharField(max_length = 7, choices=LISTE_COULEURS, default='#696969')
	CHOIX_TEMPS = ((20,'20 min'),(30,'30 min'),(60,'60 min (informatique)'))
	temps = models.PositiveSmallIntegerField(choices=CHOIX_TEMPS,verbose_name="minutes/colle/élève",default=20)
	class Meta:
		ordering=['nom']

	def __str__(self):
		return self.nom

class Classe(models.Model):
	ANNEE_PREPA = ((1,"1ère année"),(2,"2ème année"),)
	nom = models.CharField(max_length = 30, unique=True)
	annee = models.PositiveSmallIntegerField(choices=ANNEE_PREPA,default=1)
	matieres = models.ManyToManyField(Matiere,verbose_name="matières",related_name="matieresclasse", blank = True)
	profprincipal = models.ForeignKey('Colleur',null=True,related_name="classeprofprincipal",on_delete=models.SET_NULL)
	class Meta:
		ordering=['annee','nom']

	def __str__(self):
		return self.nom

	def loginsEleves(self):
		"""renvoie la liste des logins des élèves de la classe ordonnés par ordre alphabétique"""
		if hasattr(self,'listeLoginsEleves'):
			return self.listeLoginsEleves
		eleves = self.classeeleve.all().select_related('user')
		listeLogins = []
		lastlogin = False
		indice=1
		for eleve in eleves:
			login = eleve.user.first_name[0].lower()+eleve.user.last_name[0].lower()
			if login == lastlogin:
				if indice==1:
					listeLogins[-1]+="1"
				indice+=1
				listeLogins.append("{}{}".format(login,indice))
			else:
				indice=1
				listeLogins.append(login)
			lastlogin=login
		self.listeLoginsEleves = list(zip(eleves,listeLogins))
		return self.listeLoginsEleves

	def dictEleves(self):
		"""renvoie un dictionnaire dont les clés sont les id des élèves de la classe, et les valeurs le login correspondant"""
		if hasattr(self,'dictAttrEleves'):
			return self.dictAttrEleves
		dictEleves={}
		for eleve,login in self.loginsEleves():
			dictEleves[eleve.pk]=login
		self.dictAttrEleves = dictEleves
		return dictEleves

	def loginsColleurs(self,semin,semax):
		"""renvoie la liste des logins des colleurs de la classe, qui ont des colles entre les semaines semin et semax, ordonnés par ordre alphabétique"""
		if hasattr(self,'listeLoginsColleurs_{}_{}'.format(semin.pk,semax.pk)):
			return getattr(self,'listeLoginsColleurs_{}_{}'.format(semin.pk,semax.pk))
		colleurs = self.colleur_set.filter(colle__semaine__lundi__range=(semin.lundi,semax.lundi)).distinct().order_by('user__last_name','user__first_name')
		listeLogins = []
		lastlogin = False
		indice=1
		for colleur in colleurs:
			login = colleur.user.first_name[0].upper()+colleur.user.last_name[0].upper()
			if login == lastlogin:
				if indice==1:
					listeLogins[-1]+="1"
				indice+=1
				listeLogins.append("{}{}".format(login,indice))
			else:
				indice=1
				listeLogins.append(login)
			lastlogin=login
		setattr(self,'listeLoginsColleurs_{}_{}'.format(semin.pk,semax.pk),list(zip(colleurs,listeLogins)))
		return getattr(self,'listeLoginsColleurs_{}_{}'.format(semin.pk,semax.pk))

	def dictColleurs(self,semin,semax):
		"""renvoie un dictionnaire dont les clés sont les id des colleurs de la classe, et les valeurs le login correspondant"""
		if hasattr(self,'dictAttrColleurs_{}_{}'.format(semin.pk,semax.pk)):
			return getattr(self,'dictAttrColleurs_{}_{}'.format(semin.pk,semax.pk))
		dictColleurs={}
		for colleur,login in self.loginsColleurs(semin,semax):
			dictColleurs[colleur.pk]=login
		setattr(self,'dictAttrColleurs_{}_{}'.format(semin.pk,semax.pk),dictColleurs)
		return getattr(self,'dictAttrColleurs_{}_{}'.format(semin.pk,semax.pk))


class Etablissement(models.Model):
	nom = models.CharField(max_length = 50, unique=True,)

	def __str__(self):
		return self.nom

class Groupe(models.Model):
	nom = models.CharField(max_length = 10)
	classe = models.ForeignKey(Classe,related_name="classegroupe", on_delete=models.PROTECT)

	class Meta:
		unique_together=('nom','classe')
		ordering=['nom']

	def __str__(self):
		return self.nom

class Colleur(models.Model):
	LISTE_GRADES=[(0,"autre"),(1,"certifié"),(2,"bi-admissible"),(3,"agrégé"),(4,"chaire supérieure")]
	matieres = models.ManyToManyField(Matiere, verbose_name="Matière(s)")
	classes = models.ManyToManyField(Classe, verbose_name="Classe(s)")
	grade = models.PositiveSmallIntegerField(choices=LISTE_GRADES, default=3)
	etablissement = models.ForeignKey(Etablissement, verbose_name="Établissement", null=True,blank=True, on_delete=models.PROTECT)

	def allprofs(self):
		return self.colleurprof.prefetch_related('classe')

	def modifgroupe(self):
		for prof in self.colleurprof.all():
			if prof.modifgroupe or prof.classe.profprincipal == self:
				return True
		return False

	def __str__(self):
		if hasattr(self,'user'):
			return "{} {}".format(self.user.first_name.title(),self.user.last_name.upper())
		return ""

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
			yield classe,prof

class Prof(models.Model):
	colleur = models.ForeignKey(Colleur,verbose_name="Professeur", related_name="colleurprof",on_delete =models.CASCADE)
	classe = models.ForeignKey(Classe,verbose_name="Classe", related_name="classeprof",on_delete =models.CASCADE)
	matiere= models.ForeignKey(Matiere,verbose_name="Matière", related_name="matiereprof",on_delete =models.CASCADE)
	modifgroupe = models.BooleanField(verbose_name="Droits de modification des groupes de colle")
	modifcolloscope = models.BooleanField(verbose_name="Droits de modification du colloscope")
	objects = ProfManager()

	class Meta:
		unique_together=('classe','matiere') # un seul prof par couple classe/matière

class Eleve(models.Model):
	def update_photo(instance, filename):
		"""Renvoie l'url vers le fichier photo"""
		return "photos/photo.{}".format(filename.split('.')[-1])
	classe = models.ForeignKey(Classe,related_name="classeeleve",on_delete=models.PROTECT)
	groupe = models.ForeignKey(Groupe, null=True,related_name="groupeeleve", on_delete=models.SET_NULL)
	photo = models.ImageField(verbose_name="photo(jpg/png, 300x400)",upload_to=update_photo,null=True,blank=True)

	class Meta:
		ordering=['user__last_name','user__first_name']

	def __str__(self):
		return "{} {}".format(self.user.first_name.title(),self.user.last_name.upper())

class User(AbstractUser):
	eleve = models.OneToOneField(Eleve, null=True, on_delete=models.CASCADE)
	colleur = models.OneToOneField(Colleur, null=True, on_delete=models.CASCADE)

	def totalmessages(self):
		return Destinataire.objects.filter(user=self).count()

	def messagesnonlus(self):
		return Destinataire.objects.filter(user=self,lu=False).count()

	def __str__(self):
		return "{} {}".format(self.first_name.title(),self.last_name.upper())

class Semaine(models.Model):
	locale.setlocale(locale.LC_ALL,'')
	LISTE_SEMAINES=zip(range(1,36),range(1,36))
	base = date.today()
	base = base-timedelta(days=base.weekday())
	# utilisation d'une fonction lambda car en python 3 les compréhensions on leur propre espace de nom, et les variable d'une classe englobante y sont invisibles
	liste1=(lambda y:[y+timedelta(days=7*x) for x in range(-40,60)])(base)
	liste2=[d.strftime('%d %B %Y') for d in liste1]
	LISTE_LUNDIS=zip(liste1,liste2)
	numero = models.PositiveSmallIntegerField(unique=True, choices=LISTE_SEMAINES, default=1)
	lundi = models.DateField(unique=True, choices=LISTE_LUNDIS, default=base)

	class Meta:
		ordering=['lundi']

	def __str__(self):
		samedi=self.lundi+timedelta(days=5)
		return "{}:{}/{}-{}/{}".format(self.numero,self.lundi.day,self.lundi.month,samedi.day,samedi.month)

class Creneau(models.Model):
	LISTE_HEURE=[(i,"{}h{:02d}".format(i//4,15*(i%4))) for i in range(24,89)] # une heure est représentée par le nombre de 1/4 d'heure depuis 0h00. entre 6h et 22h
	LISTE_JOUR=enumerate(["lundi","mardi","mercredi","jeudi","vendredi","samedi"])
	jour = models.PositiveSmallIntegerField(choices=LISTE_JOUR,default=0)
	heure = models.PositiveSmallIntegerField(choices=LISTE_HEURE,default=14)
	salle = models.CharField(max_length=20,null=True,blank=True)
	classe = models.ForeignKey(Classe,related_name="classecreneau")

	class Meta:
		ordering=['jour','heure','salle','pk']

	def __str__(self):
		return "{}/{}/{}h{:02d}".format(self.classe.nom,semaine[self.jour],self.heure//4,15*(self.heure%4))

class Programme(models.Model):
	def update_name(instance, filename):
		return "programme/prog"+str(instance.semaine.pk)+"-"+str(instance.classe.pk)+"-"+str(instance.matiere.pk)+".pdf"
	semaine = models.ForeignKey(Semaine,related_name="semaineprogramme",on_delete=models.PROTECT)
	classe = models.ForeignKey(Classe,related_name="classeprogramme",on_delete=models.PROTECT)
	matiere = models.ForeignKey(Matiere,related_name="matiereprogramme",on_delete=models.PROTECT)
	titre = models.CharField(max_length = 50)
	detail = models.TextField(verbose_name="Détails",null=True,blank=True)
	fichier = models.FileField(verbose_name="Fichier(pdf)",upload_to=update_name,null=True,blank=True)

	class Meta:
		unique_together=('semaine','classe','matiere') # un programme maximum par semaine/classe/matière

	def __str__(self):
		return self.titre.title()

class NoteManager(models.Manager):
	def listeNotes(self,classe,matiere,colleur):
		requete = "SELECT n.id pk, s.numero semaine, p.titre titre, p.detail detail, n.date_colle date_colle, n.heure heure, u.first_name prenom, u.last_name nom, n.note note, n.commentaire commentaire\
				   FROM accueil_note n\
				   LEFT OUTER JOIN accueil_eleve e\
				   ON n.eleve_id = e.id\
				   LEFT OUTER JOIN accueil_user u\
				   ON u.eleve_id = e.id\
				   INNER JOIN accueil_semaine s\
				   ON n.semaine_id=s.id\
				   LEFT OUTER JOIN accueil_programme p\
				   ON p.semaine_id = s.id AND p.classe_id=%s AND p.matiere_id = %s\
				   WHERE n.classe_id = %s AND n.colleur_id= %s\
				   ORDER BY s.numero DESC, n.jour DESC, n.heure DESC"
		with connection.cursor() as cursor:
			cursor.execute(requete,(classe.pk,matiere.pk,classe.pk,colleur.pk))
			notes = dictfetchall(cursor)
		listeNotes = []
		listeDates = []
		listeHeures = []
		listeEleves = []
		nbeleves=nbheures=nbdates=0
		try:
			heure,date_colle,semaine,titre,detail,pk = notes[0]['heure'],notes[0]['date_colle'], notes[0]['semaine'], notes[0]['titre'], notes[0]['detail'], notes[0]['pk']
		except Exception:
			pass
		else:
			for note in notes:
				if not (note['heure'] == heure and note['date_colle'] == date_colle):
					nbheures += nbeleves
					listeHeures.append((listeEleves,heure,nbeleves))
					heure = note['heure']
					nbeleves=1
					listeEleves = [("Élève fictif" if not note['prenom'] else "{} {}".format(note['prenom'].title(),note['nom'].upper()),note['note'],note['commentaire'],note['pk'])]
					if note['date_colle'] != date_colle:
						nbdates+=nbheures
						listeDates.append((listeHeures,date_colle,nbheures))
						date_colle = note['date_colle']
						nbheures=0
						listeHeures=[]
						if note['semaine'] != semaine:
							listeNotes.append((listeDates,semaine,titre,detail,nbdates))
							semaine,titre,detail = note['semaine'],note['titre'],note['detail']
							nbdates=0
							listeDates=[]
				elif note['prenom']:
					listeEleves.append(("{} {}".format(note['prenom'].title(),note['nom'].upper()),note['note'],note['commentaire'],note['pk']))
					nbeleves+=1
				else:
					listeEleves.append(("Élève fictif",note['note'],note['commentaire'],note['pk']))
					nbeleves+=1
			listeHeures.append((listeEleves,heure,nbeleves))
			nbheures += nbeleves
			listeDates.append((listeHeures,date_colle,nbheures))
			nbdates+=nbheures	
			listeNotes.append((listeDates,semaine,titre,detail,nbdates))
		return listeNotes

	def classe2resultat(self,matiere,classe,semin,semax):
		semaines = Semaine.objects.filter(semainenote__classe=classe,semainenote__matiere=matiere,lundi__range=(semin.lundi,semax.lundi)).distinct().order_by('lundi')
		yield semaines
		listeEleves = list(Eleve.objects.filter(classe=classe).select_related('user'))
		elevesdict = {eleve.pk:[eleve.user.first_name.title(),eleve.user.last_name.upper(),"",""] for eleve in listeEleves}
		moyennes = list(Note.objects.exclude(note__gt=20).filter(matiere=matiere,classe=classe).filter(semaine__lundi__range=[semin.lundi,semax.lundi]).values('eleve__id','eleve__user__first_name','eleve__user__last_name').annotate(Avg('note')).order_by('eleve__user__last_name','eleve__user__first_name'))
		moyennes.sort(key=lambda x:x['note__avg'],reverse=True)
		for i,x in enumerate(moyennes):
			x['rang']=i+1
		for i in range(len(moyennes)-1):
			if moyennes[i]['note__avg']-moyennes[i+1]['note__avg']<1e-6:
				moyennes[i+1]['rang']=moyennes[i]['rang']
		for moyenne in moyennes:
			elevesdict[moyenne['eleve__id']][2:]=[moyenne['note__avg'],moyenne['rang']]
		eleves = list(elevesdict.values())
		eleves.sort(key=lambda x:(x[1],x[0]))
		for elevemoy,eleve in zip(eleves,listeEleves):
			note=dict()
			note['eleve']=eleve
			note['moyenne']=elevemoy[2]
			note['rang']=elevemoy[3]
			note['semaine']=list()
			for semaine in semaines:
				note['semaine'].append(Note.objects.filter(eleve=eleve,matiere=matiere,semaine=semaine).values('note','colleur__user__first_name','colleur__user__last_name','commentaire'))
			yield note

	def noteEleve(self,eleve,matiere=None):
		requete = "SELECT m.nom nom_matiere, m.couleur couleur, n.date_colle date_colle, u.first_name prenom, u.last_name nom, p.titre titre, p.detail programme, n.note note, n.commentaire commentaire\
				   FROM accueil_note n\
				   INNER JOIN accueil_matiere m\
				   ON n.matiere_id=m.id\
				   INNER JOIN accueil_colleur c\
				   ON n.colleur_id=c.id\
				   INNER JOIN accueil_user u\
				   ON u.colleur_id=c.id\
				   INNER JOIN accueil_semaine s\
				   ON n.semaine_id = s.id\
				   LEFT OUTER JOIN accueil_programme p\
				   ON p.semaine_id = s.id AND p.classe_id = n.classe_id AND p.matiere_id=m.id\
				   WHERE n.eleve_id = %s "
		if matiere:
			requete+="AND m.id = %s "
		requete+="ORDER BY date_colle DESC"
		with connection.cursor() as cursor:
			cursor.execute(requete,[eleve.pk] + ([matiere.pk] if matiere else []))
			notes = dictfetchall(cursor)
		return notes

class Note(models.Model):
	LISTE_JOUR=enumerate(["lundi","mardi","mercredi","jeudi","vendredi","samedi"])
	LISTE_HEURE=[(i,"{}h{:02d}".format(i//4,15*(i%4))) for i in range(28,88)]
	LISTE_NOTE=[(21,"n.n"),(22,"Abs")]
	LISTE_NOTE.extend(zip(range(21),range(21)))
	colleur = models.ForeignKey(Colleur,on_delete=models.PROTECT)
	matiere = models.ForeignKey(Matiere,on_delete=models.PROTECT)
	date_enreg = models.DateField(auto_now_add = True)
	semaine = models.ForeignKey(Semaine,related_name="semainenote",on_delete=models.PROTECT)
	date_colle = models.DateField(verbose_name = 'date de rattrapage',default=date.today)
	rattrapee = models.BooleanField(verbose_name="rattrapée")
	jour = models.PositiveSmallIntegerField(choices=LISTE_JOUR,default=0)
	note = models.PositiveSmallIntegerField(choices=LISTE_NOTE,default=22)
	eleve = models.ForeignKey(Eleve,null=True,on_delete=models.PROTECT)
	classe = models.ForeignKey(Classe,on_delete=models.PROTECT)
	heure = models.PositiveSmallIntegerField(choices=LISTE_HEURE,default=14)
	commentaire = models.TextField(max_length=2000,verbose_name="Commentaire(facultatif)",null = True, blank=True)
	objects = NoteManager()

	def update(self):
		if not self.rattrapee: # si la colle n'est pas rattrapée, on calcule la date de colle à partir de la semaine et du jour de la semaine
			self.date_colle=self.semaine.lundi+timedelta(days=int(self.jour))

	def __str__(self):
		return "{} {} {} {}".format(self.eleve.user.last_name.upper(),self.matiere.nom,self.semaine.numero,self.note)

class ColleManager(models.Manager):

	def classe2colloscope(self,classe,semin,semax,modif=False):
		semaines=Semaine.objects.filter(lundi__range=(semin.lundi,semax.lundi))
		jours = Creneau.objects.filter(classe=classe)
		creneaux = Creneau.objects.filter(classe=classe)
		if not modif:
			jours = jours.filter(colle__semaine__lundi__range=(semin.lundi,semax.lundi))
			creneaux = creneaux.filter(colle__semaine__lundi__range=(semin.lundi,semax.lundi)).annotate(nb=Count('colle')).filter(nb__gt=0)
		jours = jours.values('jour').annotate(nb=Count('id',distinct=True)).order_by('jour')			
		requete="SELECT {} cr.id id_cr, c2.id id_col, jf.nom ferie, u.username login, m.id id_matiere, m.nom nom_matiere, m.couleur couleur, m.temps temps, g.nom nomgroupe, cr.jour jour, cr.heure heure, cr.salle salle, cr.id, s.lundi lundi, e.id id_eleve, u2.first_name prenom_eleve,u2.last_name nom_eleve {} \
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
						ON c.creneau_id=cr.id INNER JOIN accueil_semaine s2	ON (c.semaine_id=s2.id AND s2.lundi BETWEEN %s AND %s)",date_plus_jour('s.lundi','cr.jour'))
		with connection.cursor() as cursor:
			cursor.execute(requete, ([] if modif else [semin.lundi,semax.lundi])+[classe.pk,semin.lundi,semax.lundi])
			precolles = dictfetchall(cursor)
		colles = []
		longueur = creneaux.count()
		for i in range(semaines.count()):
			colles.append(precolles[:longueur])
			del precolles[:longueur]
		return jours,creneaux,colles,semaines

	def agenda(self,colleur,semainemin):
		requete = "SELECT DISTINCT COUNT(n.id) nbnotes, co.id pk, g.nom nom_groupe, g.id id_groupe, cl.nom nom_classe, s.lundi lundi, s.id, cr.jour jour,cr.heure heure, cr.salle salle, m.id, m.nom nom_matiere, m.couleur couleur, m.temps temps, u.first_name prenom, u.last_name nom, u2.first_name prenom_eleve, u2.last_name nom_eleve, p.titre titre, p.detail detail, p.fichier fichier\
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
				   LEFT OUTER JOIN accueil_eleve e\
				   ON co.eleve_id = e.id\
				   LEFT OUTER JOIN accueil_classe cl2\
				   ON g.classe_id = cl2.id\
				   LEFT OUTER JOIN accueil_user u2\
				   ON u2.eleve_id = e.id\
				   LEFT OUTER JOIN accueil_classe cl\
				   ON g.classe_id = cl.id\
				   LEFT OUTER JOIN accueil_programme p\
				   ON (p.semaine_id = s.id AND p.matiere_id = m.id AND p.classe_id = cl.id)\
				   LEFT OUTER JOIN accueil_note n\
				   ON n.matiere_id = m.id AND n.colleur_id = c.id AND n.semaine_id=s.id AND n.jour = cr.jour AND n.heure = cr.heure AND n.semaine_id = s.id\
				   WHERE c.id=%s AND s.lundi >= %s\
				   GROUP BY co.id, g.nom, g.id, cl.nom, s.lundi, s.id, cr.jour, cr.heure, cr.salle, m.id, m.nom, m.couleur, u.first_name, u.last_name, u2.first_name, u2.last_name, p.titre, p.detail, p.fichier\
				   ORDER BY s.lundi,cr.jour,cr.heure"
		with connection.cursor() as cursor:
			cursor.execute(requete,(colleur.pk,semainemin))
			colles = dictfetchall(cursor)
		groupesnb = self.filter(colleur=colleur,semaine__lundi__gte=semainemin).values('groupe').annotate(nb=Count('groupe__groupeeleve',distinct=True)).order_by('groupe__pk')
		groupeseleve = list(self.filter(colleur=colleur,semaine__lundi__gte=semainemin).values('groupe__groupeeleve__user__first_name','groupe__groupeeleve__user__last_name').distinct().order_by('groupe__pk','groupe__groupeeleve__user__last_name','groupe__groupeeleve__user__first_name'))
		groupes = dict()
		for groupe in groupesnb:
			groupes[groupe['groupe']] = "; ".join(["{} {}".format(x['groupe__groupeeleve__user__first_name'].title(),x['groupe__groupeeleve__user__last_name'].upper()) for x in groupeseleve[:groupe['nb']]])
			del groupeseleve[:groupe['nb']]
		return groupes, colles

	def agendaEleve(self,eleve,semainemin):
		requete = "SELECT s.lundi lundi, cr.jour jour,cr.heure heure, cr.salle salle, m.nom nom_matiere, m.couleur couleur, u.first_name prenom, u.last_name nom, p.titre titre, p.detail detail, p.fichier fichier\
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
				   ON (e.groupe_id = g.id OR e.id=co.eleve_id)\
				   LEFT OUTER JOIN accueil_programme p\
				   ON (p.semaine_id = s.id AND p.matiere_id = m.id AND p.classe_id = %s)\
				   WHERE e.id=%s AND s.lundi >= %s\
				   ORDER BY s.lundi,cr.jour,cr.heure"
		with connection.cursor() as cursor:
			cursor.execute(requete,(eleve.classe.pk,eleve.pk,semainemin))
			colles = dictfetchall(cursor)
		return colles

class Colle(models.Model):
	creneau = models.ForeignKey(Creneau,on_delete=models.PROTECT)
	colleur = models.ForeignKey(Colleur,on_delete=models.PROTECT)
	matiere = models.ForeignKey(Matiere,on_delete=models.PROTECT)
	groupe = models.ForeignKey(Groupe,on_delete=models.PROTECT,null=True)
	eleve = models.ForeignKey(Eleve,on_delete=models.PROTECT,null=True)
	classe = models.ForeignKey(Classe,on_delete=models.PROTECT,null=True) # dans l'éventualité où on note un élève fictif.
	semaine = models.ForeignKey(Semaine,on_delete=models.PROTECT)
	objects = ColleManager()

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

class Ramassage(models.Model):
	def incremente_mois(moment):
		"""ajoute un mois à moment"""
		return date(moment.year+moment.month//12 ,moment.month%12+1,1)
	moisMin,moisMax=mois()
	LISTE_MOIS =[]
	moiscourant=moisMin
	while moiscourant<moisMax:
		LISTE_MOIS.append(moiscourant)
		moiscourant=incremente_mois(moiscourant)
	LISTE_MOIS=[(x,x.strftime('%B %Y')) for x in LISTE_MOIS]
	moisDebut = models.DateField(verbose_name='Début',choices=LISTE_MOIS)
	moisFin = models.DateField(verbose_name='Fin',choices=LISTE_MOIS)

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
	auteur = models.ForeignKey(User,null=True,on_delete=models.SET_NULL,related_name="messagesenvoyes")
	hasAuteur = models.BooleanField(default=True)
	luPar = models.TextField(verbose_name="lu par: ")
	listedestinataires = models.TextField(verbose_name="Liste des destinataires")
	titre = models.CharField(max_length=100)
	corps = models.TextField(max_length=2000)

class Destinataire(models.Model):
	message = models.ForeignKey(Message,related_name="messagerecu",on_delete=models.CASCADE)
	user=models.ForeignKey(User,related_name="destinataire",on_delete=models.CASCADE)
	lu= models.BooleanField(default=False)
	reponses = models.PositiveSmallIntegerField(default=0)

def update_name(programme):
	nomimage=programme.fichier.name.replace('programme','image').replace('pdf','jpg')
	nouveaufichier="programme/prog"+str(programme.semaine.pk)+"-"+str(programme.classe.pk)+"-"+str(programme.matiere.pk)+".pdf"
	nouvelleimage=nouveaufichier.replace('programme','image').replace('pdf','jpg')
	os.rename(MEDIA_ROOT+programme.fichier.name,MEDIA_ROOT+nouveaufichier)
	os.rename(MEDIA_ROOT+nomimage,MEDIA_ROOT+nouvelleimage)
	programme.fichier.name=nouveaufichier
	programme.save()

@receiver(post_delete, sender=Programme)
def programme_post_delete_function(sender, instance, **kwargs):
	if instance.fichier:
		fichier=MEDIA_ROOT+instance.fichier.name
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
			if not os.path.isfile(MEDIA_ROOT+nomimage): # si l'image n'existe pas
				# on convertit la première page du pdf en jpg (échoue avec une exception s'il n'y pas pas de pdf ou si imagemagick n'est pas installé)
				os.system("convert -density 200 "+MEDIA_ROOT+nomfichier+"[0] "+MEDIA_ROOT+nomimage)  
				os.system("convert -resize 50% "+MEDIA_ROOT+nomimage+" "+MEDIA_ROOT+nomimage)
		if nomfichier != "programme/prog"+str(instance.semaine.pk)+"-"+str(instance.classe.pk)+"-"+str(instance.matiere.pk)+".pdf":
			# si le nom du fichier ne correspond pas à ses caractéristiques (semaine/classe/matière), ce qui signifie qu'un de ces 3 champs a été modifié, on met à jour le nom du fichier.
			update_name(instance)
	except Exception: # Dans le cas ou plus aucun fichier n'est lié au programme, on efface l'éventuel fichier présent avant la modification
		nomfichier = MEDIA_ROOT+"programme/prog"+str(instance.semaine.pk)+"-"+str(instance.classe.pk)+"-"+str(instance.matiere.pk)+".pdf"
		if os.path.isfile(nomfichier): # s'il y a bien un fichier, on l'efface
			os.remove(nomfichier)
		if IMAGEMAGICK:
			nomimage=nomfichier.replace('programme','image').replace('pdf','jpg')
			if os.path.isfile(nomimage): # s'il y a bien un fichier, on l'efface
				os.remove(nomimage)
	
def update_photo(eleve):
	try:
		nomphoto = 'photos/photo_{}.{}'.format(eleve.pk,eleve.photo.name.split(".")[-1].lower())
		os.rename(MEDIA_ROOT+eleve.photo.name,MEDIA_ROOT+nomphoto)
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
		image=Image.open(MEDIA_ROOT+instance.photo.name)
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
		image.save(MEDIA_ROOT+instance.photo.name)

@receiver(post_delete, sender=Eleve)
def eleve_post_delete_function(sender, instance, **kwargs):
	if instance.photo:
		fichier=MEDIA_ROOT+instance.photo.name
		if os.path.isfile(fichier):
			os.remove(fichier)