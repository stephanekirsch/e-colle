# -*- coding:utf8 -*-
from django.db import models, connection
from django.contrib.auth.models import AbstractUser
from datetime import date, timedelta, datetime, time
from django.utils import timezone
import locale
from django.db.models.signals import post_delete, post_save
from django.db import transaction
from django.dispatch import receiver
import os
from ecolle.settings import MEDIA_ROOT, IMAGEMAGICK, BDD, DEFAULT_CSS, HEURE_DEBUT, HEURE_FIN, INTERVALLE
from PIL import Image
from django.db.models import Count, Avg, Min, Max, Sum, F, Q, StdDev
from django.db.models.functions import Lower, Upper, Concat, Substr

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

def group_concat(arg):
	"""renvoie une chaîne de caractères correspondant à la syntaxe SQL qui permet d'utiliser une fonction d'agrégation qui concatène des chaînes"""
	if BDD == 'postgresql' or BDD == 'postgresql_psycopg2':
		return "STRING_AGG(DISTINCT {0:}, ',' ORDER BY {0:})".format(arg)
	elif BDD == 'mysql':
		return "GROUP_CONCAT(DISTINCT {0:} ORDER BY {0:})".format(arg)
	elif BDD == 'sqlite3':
		return "GROUP_CONCAT(DISTINCT {})".format(arg)
	else:
		return "" # à compléter par ce qu'il faut dans le cas ou vous utilisez un SGBD qui n'est ni mysql, ni postgresql, ni sqlite


class ConfigManager(models.Manager):
	def get_config(self):
		try:
			config = self.all()[0]
		except Exception:
			config = Config(nom_etablissement="",modif_secret_col=False,modif_secret_groupe=False,modif_prof_col=True,modif_prof_groupe=True,\
			default_modif_col=False,default_modif_groupe=False,mathjax=True,ects=False,nom_adresse_etablissement="",academie="",ville="",app_mobile=False)
		return config


class Config(models.Model):
	nom_etablissement = models.CharField(verbose_name="Nom de l'établissement",max_length=30,blank=True)
	modif_secret_col = models.BooleanField(verbose_name="Modification du colloscope par le secrétariat",default=False)
	modif_secret_groupe = models.BooleanField(verbose_name="Modification des groupes par le secrétariat",default=False)
	modif_prof_col = models.BooleanField(verbose_name="Modification du colloscope par les enseignants",default=True)
	default_modif_col = models.BooleanField(verbose_name="Modification du colloscope par défaut pour tous les enseignants",default=False)
	modif_prof_groupe = models.BooleanField(verbose_name="Modification des groupes par les enseignants",default=True)
	default_modif_groupe = models.BooleanField(verbose_name="Modification des groupes par défaut pour tous les enseignants",default=False)
	mathjax = models.BooleanField(verbose_name="Mise en forme des formules mathématiques avec Mathjax",default=True)
	ects = models.BooleanField(verbose_name="Gestion des fiches de crédits ECTS",default=False)
	nom_adresse_etablissement = models.TextField(verbose_name="Nom complet de l'établissement + adresse",blank=True)
	ville = models.CharField(verbose_name = "Ville de l'établissement", max_length=40,blank=True)
	academie = models.CharField(verbose_name = "Académie de l'établissement", max_length=40,blank=True)
	app_mobile = models.BooleanField(verbose_name="Application mobile",default=False)
	objects = ConfigManager()

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
	nom = models.CharField(max_length = 20)
	nomcomplet = models.CharField(max_length = 30, default="")
	couleur = models.CharField(max_length = 7, choices=LISTE_COULEURS, default='#696969')
	CHOIX_TEMPS = ((20,'20 min (par groupe de 3)'),(30,'30 min (solo)'),(60,'60 min (informatique)'))
	temps = models.PositiveSmallIntegerField(choices=CHOIX_TEMPS,verbose_name="minutes/colle/élève",default=20)
	lv = models.PositiveSmallIntegerField(verbose_name="Langue vivante",choices=enumerate(['---','LV1','LV2']),default=0)
	class Meta:
		ordering=['nom','lv','temps']
		unique_together=(('nom','lv','temps'))

	def __str__(self):
		dico = {20:'Gr',30:'So',60:'Cl'}
		return self.nom.title() + "({})".format("/".join([dico[self.temps]] + (["LV{}".format(self.lv)] if self.lv else []))) 

class Classe(models.Model):
	ANNEE_PREPA = ((1,"1ère année"),(2,"2ème année"),)
	nom = models.CharField(max_length = 30, unique=True)
	annee = models.PositiveSmallIntegerField(choices=ANNEE_PREPA,default=1)
	matieres = models.ManyToManyField(Matiere,verbose_name="matières",related_name="matieresclasse", blank = True)
	profprincipal = models.ForeignKey('Colleur',null=True,related_name="classeprofprincipal",on_delete=models.SET_NULL)
	class Meta:
		ordering=['annee','nom']

	def matierespk(self):
		if hasattr(self,'listeMatieres'): # si l'attribut existe déjà, on le renvoie
			return self.listeMatieres
		self.listeMatieres = self.matieres.values_list('pk',flat=True) # pour éviter de faire la requête plusieurs fois, on garde le résultat en cache dans un attribut
		return self.listeMatieres

	def __str__(self):
		return self.nom

	def loginsEleves(self):
		"""renvoie la liste des logins des élèves de la classe ordonnés par ordre alphabétique"""
		eleves = self.classeeleve.order_by('user__last_name','user__first_name').annotate(login=Lower(Concat(Substr('user__first_name',1,1),Substr('user__last_name',1,1)))).order_by('login','user__last_name','user__first_name').select_related('user')
		listeLogins = []
		lastlogin = False
		indice=1
		for eleve in eleves:
			login = eleve.login
			if login == lastlogin:
				if indice==1:
					listeLogins[-1]+="1"
				indice+=1
				listeLogins.append("{}{:x}".format(login,indice))
			else:
				indice=1
				listeLogins.append(login)
			lastlogin=login
		elevesLogin = list(zip(eleves,listeLogins))
		elevesLogin.sort(key = lambda x:(x[0].user.last_name,x[0].user.first_name))
		return elevesLogin

	def loginMatiereEleves(self):
		matiereeleves = []
		listeEleves = self.loginsEleves()
		for matiere in self.matieres.filter(colleur__classes=self).distinct():
			if matiere.temps != 30:
				matiereeleves.append(None)
			elif not matiere.lv:
				matiereeleves.append(listeEleves)
			elif matiere.lv==1:
				listeTemp=listeEleves.copy()
				for i in range(len(listeTemp)-1,-1,-1):
					if listeTemp[i][0].lv1 != matiere:
						listeTemp.pop(i)
				matiereeleves.append(listeTemp)
			elif matiere.lv==2:
				listeTemp=listeEleves.copy()
				for i in range(len(listeTemp)-1,-1,-1):
					if listeTemp[i][0].lv2 != matiere:
						listeTemp.pop(i)
				matiereeleves.append(listeTemp)
		return matiereeleves

	def dictEleves(self):
		"""renvoie un dictionnaire dont les clés sont les id des élèves de la classe, et les valeurs le login correspondant"""
		dictEleves={}
		for eleve,login in self.loginsEleves():
			dictEleves[eleve.pk]=login
		return dictEleves

	def loginsColleurs(self,semin=None,semax=None,colleur=None):
		"""renvoie la liste des logins des colleurs de la classe, qui ont des colles entre les semaines semin et semax, ordonnés par ordre alphabétique"""
		if colleur is not None:
			colleurs = Colleur.objects.filter(user__is_active = True, classes__in = colleur.classes.all()).distinct().annotate(login=Upper(Concat(Substr('user__first_name',1,1),Substr('user__last_name',1,1)))).order_by('login','user__last_name','user__first_name')
		elif semin is None or semax is None:
			colleurs = self.colleur_set.filter(user__is_active = True).annotate(login=Upper(Concat(Substr('user__first_name',1,1),Substr('user__last_name',1,1)))).order_by('login','user__last_name','user__first_name')
		else:
			colleurs = self.colleur_set.filter(colle__semaine__lundi__range=(semin.lundi,semax.lundi)).distinct().annotate(login=Upper(Concat(Substr('user__first_name',1,1),Substr('user__last_name',1,1)))).order_by('login', 'user__last_name','user__first_name')
		listeLogins = []
		lastlogin = False
		indice=1
		for colleur in colleurs:
			login = colleur.login
			if login == lastlogin:
				if indice==1:
					listeLogins[-1]+="1"
				indice+=1
				listeLogins.append("{}{:x}".format(login,indice))
			else:
				indice=1
				listeLogins.append(login)
			lastlogin=login
		return list(zip(colleurs,listeLogins))

	def dictColleurs(self,semin=None,semax=None):
		"""renvoie un dictionnaire dont les clés sont les id des colleurs de la classe, et les valeurs le login correspondant"""
		dictColleurs={}
		for colleur,login in self.loginsColleurs(semin,semax):
			dictColleurs[colleur.pk]=login
		return dictColleurs

	def dictGroupes(self,noms=True):
		dictgroupes = dict()
		if noms is True:
			groupes = Groupe.objects.filter(classe=self).prefetch_related('groupeeleve','groupeeleve__user')
			listegroupes = {groupe.pk: (groupe.nom,"; ".join(["{} {}".format(eleve.user.first_name.title(),eleve.user.last_name.upper()) for eleve in groupe.groupeeleve.all()])) for groupe in groupes}
			for matiere in self.matieres.filter(temps=20):
				if matiere.lv == 0:
					dictgroupes[matiere.pk] = listegroupes
				elif matiere.lv == 1:
					dictgroupes[matiere.pk] = {groupe.pk: (groupe.nom,"; ".join(["{} {}".format(eleve.user.first_name.title(),eleve.user.last_name.upper()) for eleve in groupe.groupeeleve.all() if eleve.lv1==matiere])) for groupe in groupes}
				elif matiere.lv == 2:
					dictgroupes[matiere.pk] = {groupe.pk: (groupe.nom,"; ".join(["{} {}".format(eleve.user.first_name.title(),eleve.user.last_name.upper()) for eleve in groupe.groupeeleve.all() if eleve.lv2==matiere])) for groupe in groupes}
		else:
			groupes = Groupe.objects.filter(classe=self)
			listegroupes = [True]*groupes.count()
			for matiere in self.matieres.filter(temps=20):
				if matiere.lv == 0:
					dictgroupes[matiere.pk] = listegroupes
				elif matiere.lv == 1:
					dictgroupes[matiere.pk] = [any(eleve.lv1==matiere for eleve in groupe.groupeeleve.all()) for groupe in groupes]
				elif matiere.lv == 2:
					dictgroupes[matiere.pk] = [any(eleve.lv2==matiere for eleve in groupe.groupeeleve.all()) for groupe in groupes]
		return dictgroupes

	def dictElevespk(self):
		dictEleves = dict()
		listeEleves = [True]*Eleve.objects.filter(classe=self).count()
		for matiere in self.matieres.filter(temps=30):
			if matiere.lv == 0:
				dictEleves[matiere.pk] = listeEleves
			elif matiere.lv == 1:
				dictEleves[matiere.pk] = [eleve.lv1 == matiere for eleve in Eleve.objects.filter(classe=self)]
			elif matiere.lv == 2:
				dictEleves[matiere.pk] = [eleve.lv2 == matiere for eleve in Eleve.objects.filter(classe=self)]
		return dictEleves

class Etablissement(models.Model):
	nom = models.CharField(max_length = 50, unique=True)

	def __str__(self):
		return self.nom

class Groupe(models.Model):
	nom = models.PositiveSmallIntegerField(choices = list(zip(range(1,31),range(1,31))), verbose_name = "Nom")
	classe = models.ForeignKey(Classe,related_name="classegroupe", on_delete=models.PROTECT)

	class Meta:
		unique_together=('nom','classe')
		ordering=['nom']

	def haslangue(self,matiere):
		if not matiere.lv:
			return True
		if matiere.lv == 1:
			return Eleve.objects.filter(groupe=self,lv1=matiere).exists()
		if matiere.lv == 2:
			return Eleve.objects.filter(groupe=self,lv2=matiere).exists()

	def __str__(self):
		return str(self.nom)

class ColleurManager(models.Manager):
	def listeColleurClasse(self, colleur):
		requete = """SELECT DISTINCT colcla.id, colcla.colleur_id, colcla.classe_id FROM accueil_colleur_matieres colmat
					INNER JOIN accueil_colleur col ON col.id = colmat.colleur_id
					INNER JOIN accueil_colleur_classes colcla ON col.id = colcla.colleur_id
					INNER JOIN accueil_prof pr ON pr.classe_id = colcla.classe_id AND pr.matiere_id = colmat.matiere_id
					WHERE pr.colleur_id = %s OR colcla.colleur_id = %s AND colmat.colleur_id = %s"""
		with connection.cursor() as cursor:
			cursor.execute(requete,[colleur.id, colleur.id, colleur.id])
			return cursor.fetchall()

	def listeColleurMatiere(self, colleur):
		requete = """SELECT DISTINCT colmat.id, colmat.colleur_id, colmat.matiere_id FROM accueil_colleur_matieres colmat
					INNER JOIN accueil_colleur col ON col.id = colmat.colleur_id
					INNER JOIN accueil_colleur_classes colcla ON col.id = colcla.colleur_id
					INNER JOIN accueil_prof pr ON pr.classe_id = colcla.classe_id AND pr.matiere_id = colmat.matiere_id
					WHERE pr.colleur_id = %s OR colcla.colleur_id = %s AND colmat.colleur_id = %s"""
		with connection.cursor() as cursor:
			cursor.execute(requete,[colleur.id, colleur.id, colleur.id])
			return cursor.fetchall()

	def listeColleurs(self,matiere,classe):
		base  = self
		if matiere is not None:
			base = base.filter(matieres=matiere)
		if classe is not None:
			base = base.filter(classes=classe)
		# pour éviter de multiples accès à la BDD (même avec optimisation avec prefetch_related)
		# on fait la requête à la main avec fonction d'aggrégation pour concaténer les classes/matières 
		if matiere is None:
			if classe is None:
				where = ""
			else:
				where = "WHERE cl.id = %s"
		else:
			if classe is None:
				where = "WHERE m.id = %s"
			else:
				where = "WHERE m.id = %s AND cl.id = %s"
		requete = """SELECT u.first_name prenom, u.last_name nom, u.username identifiant, u.email email, u.is_active actif,
				  c.grade grade, c.id id, e.nom etablissement, u.id user_id, {}, {} FROM accueil_colleur c
				  INNER JOIN accueil_user u
				  ON u.colleur_id = c.id
				  LEFT OUTER JOIN accueil_etablissement e
				  ON c.etablissement_id = e.id
				  {}
				  {}
				  LEFT OUTER JOIN accueil_colleur_matieres cm2
				  ON cm2.colleur_id = c.id
				  LEFT OUTER JOIN accueil_matiere m2
				  ON cm2.matiere_id = m2.id
				  LEFT OUTER JOIN accueil_colleur_classes cc2
				  ON cc2.colleur_id = c.id
				  LEFT OUTER JOIN accueil_classe cl2
				  ON cc2.classe_id = cl2.id
				  {}
				  GROUP BY u.id, c.id, e.id
				  ORDER BY u.last_name, u.first_name, c.id
				  """.format(group_concat("m2.nomcomplet") + " matieres", group_concat('cl2.nom') + " classes", "" if matiere is None else """LEFT OUTER JOIN accueil_colleur_matieres cm
				  ON cm.colleur_id = c.id
				  LEFT OUTER JOIN accueil_matiere m
				  ON cm.matiere_id = m.id""","" if classe is None else """LEFT OUTER JOIN accueil_colleur_classes cc
				  ON cc.colleur_id = c.id
				  LEFT OUTER JOIN accueil_classe cl
				  ON cc.classe_id = cl.id""", where)
		with transaction.atomic():
			arguments = [x.id for x in (matiere, classe) if x is not None]
			with connection.cursor() as cursor:
				cursor.execute(requete, arguments)
				colleurs = dictfetchall(cursor)
		return colleurs


class Colleur(models.Model):
	LISTE_GRADES=[(0,"autre"),(1,"certifié"),(2,"bi-admissible"),(3,"agrégé"),(4,"chaire supérieure")]
	matieres = models.ManyToManyField(Matiere, verbose_name="Matière(s)")
	classes = models.ManyToManyField(Classe, verbose_name="Classe(s)")
	grade = models.PositiveSmallIntegerField(choices=LISTE_GRADES, default=3)
	etablissement = models.ForeignKey(Etablissement, verbose_name="Établissement", null=True,blank=True, on_delete=models.PROTECT)
	objects = ColleurManager()
	
	def allprofs(self):
		return self.colleurprof.prefetch_related('classe')

	def classeGroupes(self):
		classes = set()
		for prof in self.colleurprof.prefetch_related('classe').all():
			if prof.modifgroupe or prof.classe.profprincipal == self:
				classes.add(prof.classe)
		return sorted(classes, key = lambda x:x.nom)

	def modifgroupe(self):
		if Config.objects.get_config().modif_prof_groupe:
			for prof in self.colleurprof.all():
				if prof.modifgroupe or prof.classe.profprincipal == self:
					return True
		return False

	def ectsclasses(self):
		return Classe.objects.filter(Q(profprincipal=self) | Q(classematiereECTS__profs=self)).distinct().order_by('nom')

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
	ddn = models.DateField(verbose_name="Date de naissance",null=True,blank=True)
	ldn = models.CharField(verbose_name="Lieu de naissance",max_length=50,blank=True,default="")
	ine = models.CharField(verbose_name="numéro étudiant (INE)",max_length=11,null=True,blank=True)
	lv1 = models.ForeignKey(Matiere,related_name='elevelv1',null=True,blank=True, on_delete = models.SET_NULL)
	lv2 = models.ForeignKey(Matiere,related_name='elevelv2',null=True,blank=True, on_delete = models.SET_NULL)

	class Meta:
		ordering=['user__last_name','user__first_name']

	def __str__(self):
		return "{} {}".format(self.user.first_name.title(),self.user.last_name.upper())

class User(AbstractUser):
	eleve = models.OneToOneField(Eleve, null=True, on_delete=models.CASCADE)
	colleur = models.OneToOneField(Colleur, null=True, on_delete=models.CASCADE)

	css = models.CharField(verbose_name="Style préféré",default=DEFAULT_CSS,null=True,blank=True,max_length=50)

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
	# utilisation d'une fonction lambda car en python 3 les compréhensions on leur propre espace de nom, et les variables d'une classe englobante y sont invisibles
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
	LISTE_HEURE=[(i,"{}h{:02d}".format(i//60,(i%60))) for i in range(HEURE_DEBUT,HEURE_FIN,INTERVALLE)] 
        # une heure est représentée par le nombre de minutes depuis
        # minuit
	LISTE_JOUR=enumerate(["lundi","mardi","mercredi","jeudi","vendredi","samedi"])
	jour = models.PositiveSmallIntegerField(choices=LISTE_JOUR,default=0)
	heure = models.PositiveSmallIntegerField(choices=LISTE_HEURE,default=24)
	salle = models.CharField(max_length=20,null=True,blank=True)
	classe = models.ForeignKey(Classe,related_name="classecreneau", on_delete=models.PROTECT)

	class Meta:
		ordering=['jour','heure','salle','pk']

	def __str__(self):
		return "{}/{}/{}h{:02d}".format(self.classe.nom,semaine[self.jour],self.heure//60,(self.heure%60))

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
	def listeNotesApp(self,colleur):
		requete = "SELECT s.numero semaine, n.id, n.date_colle, n.heure, n.note, n.commentaire, n.matiere_id, n.classe_id, n.eleve_id, n.rattrapee\
				   FROM accueil_note n\
				   INNER JOIN accueil_semaine s\
				   ON n.semaine_id=s.id\
				   WHERE n.colleur_id= %s\
				   ORDER BY s.numero DESC, n.date_colle DESC, n.heure DESC"
		with connection.cursor() as cursor:
			cursor.execute(requete,(colleur.pk,))
			notes = dictfetchall(cursor)
			return [[note["id"], note["matiere_id"], note["classe_id"], note["note"],  note["commentaire"], note["semaine"], datetime.combine(note["date_colle"],
				time(note["heure"] // 4, 15 * (note["heure"] % 4))).replace(tzinfo=timezone.utc).timestamp(), note["eleve_id"], bool(note["rattrapee"])] for note in notes]

	def listeNotes(self,colleur,classe,matiere):
		requete = "SELECT n.id pk, s.numero semaine, p.titre, p.detail, n.date_colle, n.heure, u.first_name prenom, u.last_name nom, n.note, n.commentaire\
				   FROM accueil_note n\
				   LEFT OUTER JOIN accueil_eleve e\
				   ON n.eleve_id = e.id\
				   LEFT OUTER JOIN accueil_user u\
				   ON u.eleve_id = e.id\
				   INNER JOIN accueil_semaine s\
				   ON n.semaine_id=s.id\
				   LEFT OUTER JOIN accueil_programme p\
				   ON p.semaine_id = s.id AND p.classe_id= %s AND p.matiere_id = %s\
				   WHERE n.classe_id = %s AND n.colleur_id= %s AND n.matiere_id = %s\
				   ORDER BY s.numero DESC, n.date_colle DESC, n.heure DESC"
		with connection.cursor() as cursor:
			cursor.execute(requete,(classe.pk,matiere.pk,classe.pk,colleur.pk,matiere.pk))
			notes = dictfetchall(cursor)
		listeNotes = []
		listeDates = []
		listeHeures = []
		listeEleves = []
		nbeleves=nbheures=nbdates=0
		try:
			heure,date_colle,semaine,titre,detail = notes[0]['heure'],notes[0]['date_colle'], notes[0]['semaine'], notes[0]['titre'], notes[0]['detail']
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
		eleves = [elevesdict[eleve.pk] for eleve in listeEleves] 
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

	def bilanEleve(self,eleve,semin,semax):
		matieres = self.filter(eleve=eleve).exclude(note__gt=20)
		if semin:
			matieres=matieres.filter(semaine__lundi__range=(semin.lundi,semax.lundi))
		matieres=matieres.values_list('matiere__pk').order_by('matiere__nom').distinct()
		moyenne = self.filter(eleve=eleve,matiere__pk__in=matieres).exclude(note__gt=20)
		moyenne_classe = self.filter(matiere__pk__in=matieres,classe=eleve.classe,eleve__isnull=False).exclude(note__gt=20) 
		if semin:
			moyenne=moyenne.filter(semaine__lundi__range=[semin.lundi,semax.lundi])
			moyenne_classe = moyenne_classe.filter(semaine__lundi__range=[semin.lundi,semax.lundi])
		moyenne = list(moyenne.values('matiere__nom','matiere__couleur').annotate(Avg('note'),Min('note'),Max('note'),Count('note'),StdDev('note')).order_by('matiere__nom'))
		moyenne_classe = moyenne_classe.values('matiere__pk').annotate(Avg('note')).order_by('matiere__nom')
		rangs=[]
		for i,matiere in enumerate(matieres):
			rang=self.exclude(note__gt=20).filter(classe=eleve.classe,eleve__isnull=False,matiere__pk=matiere[0])
			if semin:
				rang=rang.filter(semaine__lundi__range=[semin.lundi,semax.lundi])
			if moyenne[i]['note__avg']:
				rang=rang.values('eleve').annotate(Avg('note')).filter(note__avg__gt=moyenne[i]['note__avg']+0.0001).count()+1
			else:
				rang=0
			rangs.append(rang)
		return [{"note__max": x["note__max"], "matiere__couleur": x["matiere__couleur"], "note__stddev": x["note__stddev"], "note__min": x["note__min"], 
		"matiere__nom": x["matiere__nom"], "note__count": x["note__count"], "note__avg": x["note__avg"], "noteclasse__avg":y["note__avg"],"rang":z} for x,y,z in zip(moyenne,moyenne_classe,rangs)]

class Note(models.Model):
	LISTE_JOUR=enumerate(["lundi","mardi","mercredi","jeudi","vendredi","samedi"])
	LISTE_HEURE=[(i,"{}h{:02d}".format(i//60,(i%60))) for i in range(HEURE_DEBUT,HEURE_FIN,INTERVALLE)] 
	LISTE_NOTE=[(21,"n.n"),(22,"Abs")]
	LISTE_NOTE.extend(zip(range(21),range(21)))
	colleur = models.ForeignKey(Colleur,on_delete=models.PROTECT)
	matiere = models.ForeignKey(Matiere,on_delete=models.PROTECT)
	date_enreg = models.DateField(auto_now_add = True)
	semaine = models.ForeignKey(Semaine,related_name="semainenote",on_delete=models.PROTECT,blank=False)
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
				   LEFT OUTER JOIN accueil_programme p\
				   ON (p.semaine_id = s.id AND p.matiere_id = m.id AND p.classe_id = cl.id)\
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
				   LEFT OUTER JOIN accueil_programme p\
				   ON (p.semaine_id = s.id AND p.matiere_id = m.id AND p.classe_id = %s)\
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
				   LEFT OUTER JOIN accueil_programme p\
				   ON (p.semaine_id = s.id AND p.matiere_id = m.id AND p.classe_id = %s)\
				   WHERE e.id=%s AND s.lundi >= %s\
				   ORDER BY s.lundi,cr.jour,cr.heure".format(date_plus_jour('s.lundi','cr.jour'))
		with connection.cursor() as cursor:
			cursor.execute(requete,(eleve.classe.pk,eleve.pk,date.today()+timedelta(days=-27)))
			colles = dictfetchall(cursor)
		return [{'time': int(datetime.combine(agenda['jour'], time(agenda['heure'] // 4, 15 * (agenda['heure'] % 4))).replace(tzinfo=timezone.utc).timestamp()),
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
	creneau = models.ForeignKey(Creneau,on_delete=models.PROTECT)
	colleur = models.ForeignKey(Colleur,on_delete=models.PROTECT)
	matiere = models.ForeignKey(Matiere,on_delete=models.PROTECT)
	groupe = models.ForeignKey(Groupe,on_delete=models.PROTECT,null=True)
	eleve = models.ForeignKey(Eleve,on_delete=models.PROTECT,null=True) # null = True dans l'éventualité où on note un élève fictif pour l'informatique
	classe = models.ForeignKey(Classe,on_delete=models.PROTECT,null=True) # il est nécessaire de préciser la classe si null=true pour eleve et groupe
	semaine = models.ForeignKey(Semaine,on_delete=models.PROTECT)
	objects = ColleManager()

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
	profs = models.ManyToManyField(Colleur,verbose_name="Professeur", related_name="colleurmatiereECTS",blank=True)
	classe = models.ForeignKey(Classe,verbose_name="Classe", related_name="classematiereECTS",on_delete =models.CASCADE)
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
