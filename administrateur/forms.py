#-*- coding: utf-8 -*-
from django import forms
from accueil.models import Classe, Matiere, Etablissement, Semaine, Colleur, Eleve, JourFerie, User, Prof
from django.forms.extras.widgets import SelectDateWidget
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from ecolle.settings import RESOURCES_ROOT, CHEMINVERSECOLLE
from lxml import etree
from random import choice
from os import path
conf = __import__('ecolle.config')

def random_string():
	"""renvoie une chaine de caractères aléatoires contenant des lettres ou des chiffres ou un des symboles _+-.@"""
	return "".join([choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_+-.@0123456789") for i in range (30)])

class ConfigForm(forms.Form):
	NOM_ETABLISSEMENT=""
	MODIF_SECRETARIAT_COLLOSCOPE=True
	MODIF_PROF_COLLOSCOPE=True
	MODIF_SECRETARIAT_GROUPE=True
	MODIF_PROF_GROUPE=True
	DEFAULT_MODIF_COLLOSCOPE=True
	DEFAULT_MODIF_GROUPE=True
	MATHJAX=True
	ECTS=True
	NOM_ADRESSE_ETABLISSEMENT=""
	VILLE=""
	ACADEMIE=""
	try:
		NOM_ETABLISSEMENT=conf.config.NOM_ETABLISSEMENT
		MODIF_SECRETARIAT_COLLOSCOPE=conf.config.MODIF_SECRETARIAT_COLLOSCOPE
		MODIF_PROF_COLLOSCOPE=conf.config.MODIF_PROF_COLLOSCOPE
		MODIF_SECRETARIAT_GROUPE=conf.config.MODIF_SECRETARIAT_GROUPE
		MODIF_PROF_GROUPE=conf.config.MODIF_PROF_GROUPE
		DEFAULT_MODIF_COLLOSCOPE=conf.config.DEFAULT_MODIF_COLLOSCOPE
		DEFAULT_MODIF_GROUPE=conf.config.DEFAULT_MODIF_GROUPE
		MATHJAX=conf.config.MATHJAX
		ECTS=conf.config.ECTS
		NOM_ADRESSE_ETABLISSEMENT=conf.config.NOM_ADRESSE_ETABLISSEMENT
		VILLE=conf.config.VILLE
		ACADEMIE=conf.config.ACADEMIE
	except Exception:
		pass
	nomEtab = forms.CharField(label="Nom de l'établissement",max_length=70,required=False,initial = NOM_ETABLISSEMENT)
	modifSecretCol = forms.BooleanField(label="Modification du colloscope par le secrétariat",required=False, initial = MODIF_SECRETARIAT_COLLOSCOPE)
	modifSecretGroupe = forms.BooleanField(label="Modification des groupes de colle par le secrétariat",required=False, initial = MODIF_SECRETARIAT_GROUPE)
	modifProfCol = forms.BooleanField(label="Modification du colloscope par les enseignants",required=False, initial = MODIF_PROF_COLLOSCOPE)
	defaultModifCol = forms.BooleanField(label="Modification du colloscope par défaut pour tous les enseignants",required=False, initial = DEFAULT_MODIF_COLLOSCOPE)
	modifProfGroupe = forms.BooleanField(label="Modification des groupes de colle par les enseignants",required=False, initial = MODIF_PROF_GROUPE)
	defaultModifGroupe = forms.BooleanField(label="Modification des groupes par défaut pour tous les enseignants",required=False, initial = DEFAULT_MODIF_GROUPE)
	mathjax = forms.BooleanField(label="Mise en forme des formules mathématiques avec Mathjax",required=False, initial = MATHJAX)
	ects = forms.BooleanField(label="Gestion des fiches de crédits ECTS",required=False, initial = ECTS)
	nomEtabFull = forms.CharField(label="Nom complet de l'établissement + adresse",widget=forms.Textarea,required=False, initial = NOM_ADRESSE_ETABLISSEMENT)
	ville = forms.CharField(label="Ville de l'établissement",max_length=50,required=False, initial = VILLE)
	academie = forms.CharField(label="Académie de l'établissement",max_length=50,required=False, initial = ACADEMIE)

	def save(self):
		with open(path.join(CHEMINVERSECOLLE,'ecolle','config.py'),'wt',encoding="utf8") as fichier:
			fichier.write("\n".join(['NOM_ETABLISSEMENT="{}"'.format(self.cleaned_data['nomEtab']),
			'MODIF_SECRETARIAT_COLLOSCOPE={}'.format(self.cleaned_data['modifSecretCol']),
			'MODIF_PROF_COLLOSCOPE={}'.format(self.cleaned_data['modifProfCol']),
			'MODIF_SECRETARIAT_GROUPE={}'.format(self.cleaned_data['modifSecretGroupe']),
			'MODIF_PROF_GROUPE={}'.format(self.cleaned_data['modifProfGroupe']),
			'DEFAULT_MODIF_COLLOSCOPE={}'.format(self.cleaned_data['defaultModifCol']),
			'DEFAULT_MODIF_GROUPE={}'.format(self.cleaned_data['defaultModifGroupe']),
			'MATHJAX={}'.format(self.cleaned_data['mathjax']),
			'ECTS={}'.format(self.cleaned_data['ects']),
			'NOM_ADRESSE_ETABLISSEMENT="""{}"""'.format(self.cleaned_data['nomEtabFull']),
			'VILLE="{}"'.format(self.cleaned_data['ville']),
			'ACADEMIE="{}"'.format(self.cleaned_data['academie'])]))


class ColleurFormSetMdp(forms.BaseFormSet):
	def save(self):
		"""Sauvegarde en BDD les colleurs/users du formulaire"""
		# on ne peut pas utiliser bulk_create ici, puisqu'on a besoin des pk pour les relation un-un et many-many
		for form in self.forms:
			colleur= Colleur(grade=form.cleaned_data['grade'],etablissement=form.cleaned_data['etablissement'])
			colleur.save() # on sauvegarde en BDD pour avoir un pk, indispensable pour les relations many-many
			# on ajoute les matières et les classes
			colleur.matieres=form.cleaned_data['matiere']
			colleur.classes=form.cleaned_data['classe']
			# on crée le user
			user = User(username=random_string(),first_name=form.cleaned_data['prenom'],last_name=form.cleaned_data['nom'],email=form.cleaned_data['email'],colleur=colleur)
			user.set_password(form.cleaned_data['motdepasse'])
			user.save()		

class ColleurFormSet(forms.BaseFormSet):
	def __init__(self,chaine_colleurs=[],*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.chaine_colleurs=chaine_colleurs
				
	def save(self):
		"""Sauvegarde (mise à jour) en BDD les colleurs/users du formulaire"""
		for colleur,form in zip(self.chaine_colleurs,self.forms):
			colleur.grade=form.cleaned_data['grade']
			colleur.etablissement=form.cleaned_data['etablissement']
			colleur.classes=form.cleaned_data['classe']
			colleur.matieres=form.cleaned_data['matiere']
			colleur.save()
			user=colleur.user
			user.username=random_string()
			user.first_name=form.cleaned_data['prenom']
			user.last_name=form.cleaned_data['nom']
			user.email=form.cleaned_data['email']
			user.is_active=form.cleaned_data['active']
			user.set_password(form.cleaned_data['motdepasse'])
			user.save()

class AdminConnexionForm(forms.Form):
	username = forms.CharField(label="identifiant")
	password = forms.CharField(label="Mot de passe",widget=forms.PasswordInput)


class ClasseForm(forms.ModelForm):
	class Meta:
		model = Classe
		fields=['nom','annee','matieres']
		widgets = {'matieres':forms.CheckboxSelectMultiple}

class ClasseGabaritForm(forms.ModelForm):
	gabarit=forms.BooleanField(label="gabarit",required=False)
	tree=etree.parse(path.join(RESOURCES_ROOT,'classes.xml'))
	types={x.get("type")+'_'+x.get("annee") for x in tree.xpath("/classes/classe")}
	types = list(types)
	types.sort()
	LISTE_CLASSES=[]
	for typ in types:
		style,annee=typ.split("_")
		LISTE_CLASSES.append((style+" "+annee+"è"+("r" if annee=="1" else "m")+"e année",sorted((lambda y,z:[(x.get("nom")+"_"+x.get("annee"),x.get("nom")) for x in z.xpath("/classes/classe") if [x.get("type"),x.get("annee")] == y.split("_")])(typ,tree))))
	classe = forms.ChoiceField(label="classe",choices=LISTE_CLASSES)
	class Meta:
		model = Classe
		fields=['nom','annee','matieres']
		widgets = {'matieres':forms.CheckboxSelectMultiple}

	def save(self):
		if self.cleaned_data['gabarit']: # si on crée une classe via gabarit
			nom,annee=self.cleaned_data['classe'].split("_")
			annee=int(annee)
			# on passe en revue les matières, si elles existent, on les associe, sinon on les crée
			classe=self.tree.xpath("/classes/classe[@nom='{}'][@annee='{}']".format(nom,annee)).pop()
			nouvelleClasse = Classe(nom=self.cleaned_data['nom'],annee=classe.get("annee")) #On crée la classe
			nouvelleClasse.save() # on la sauvegarde
			listeMatieres=[]
			for matiere in list(classe):# on parcourt les matières du gabarit de la classe
				query = Matiere.objects.filter(nom__iexact=matiere.get('nom'),temps=int(matiere.get("temps")),lv=int(matiere.get('lv') or 0))
				if query.exists():
					matiere = query[0]
				else:
					matiere = Matiere(nom=matiere.get("nom"),temps=matiere.get("temps"),lv=(matiere.get('lv') or 0),couleur=choice(list(zip(*Matiere.LISTE_COULEURS))[0]))
					matiere.save()
				listeMatieres.append(matiere)
			nouvelleClasse.matieres.add(*listeMatieres)
		else:
			super().save()

class MatiereForm(forms.ModelForm):
	class Meta:
		model = Matiere
		fields=['nom','lv','couleur','temps']

class EtabForm(forms.ModelForm):
	class Meta:
		model = Etablissement
		fields=['nom']

class SemaineForm(forms.ModelForm):
	class Meta:
		model = Semaine
		fields=['numero','lundi']

class JourFerieForm(forms.ModelForm):
	class Meta:
		model = JourFerie
		fields=['date','nom']
		widgets = {'date':SelectDateWidget()}

class ColleurForm(forms.Form):
	LISTE_GRADE=((0,"autre"),(1,"certifié"),(2,"bi-admissible"),(3,"agrégé"),(4,"chaire supérieure"))
	nom = forms.CharField(max_length=30)
	prenom = forms.CharField(label="Prénom",max_length=30)
	motdepasse = forms.CharField(label="Mot de passe",max_length=30,required=False)
	active = forms.BooleanField(label="actif",required=False)
	email = forms.EmailField(label="email(facultatif)",max_length=50,required=False)
	grade = forms.ChoiceField(choices=LISTE_GRADE)
	etablissement = forms.ModelChoiceField(queryset=Etablissement.objects.order_by('nom'),empty_label="inconnu",required=False)
	matiere = forms.ModelMultipleChoiceField(label="Matière(s)",queryset=Matiere.objects.order_by('nom'), required=False)
	classe = forms.ModelMultipleChoiceField(label="Classe(s)",queryset=Classe.objects.order_by('annee','nom'),required=False)

	# validation du mot de passe
	def clean_motdepasse(self):
		user=User()
		if 'prenom' in self.cleaned_data:
			user.first_name=self.cleaned_data['prenom']
		if 'nom' in self.cleaned_data:
			user.last_name=self.cleaned_data['nom']
		data = self.cleaned_data['motdepasse']
		if data:
			validate_password(data,user)
		return data

class ColleurFormMdp(forms.Form):
	LISTE_GRADE=enumerate(["autre","certifié","bi-admissible","agrégé","chaire supérieure"])
	nom = forms.CharField(max_length=30)
	prenom = forms.CharField(label="Prénom",max_length=30)
	motdepasse = forms.CharField(label="Mot de passe",max_length=30,required=True)
	email = forms.EmailField(label="email(facultatif)",max_length=50,required=False)
	grade = forms.ChoiceField(choices=LISTE_GRADE)
	etablissement = forms.ModelChoiceField(queryset=Etablissement.objects.order_by('nom'),empty_label="inconnu",required=False)
	matiere = forms.ModelMultipleChoiceField(label="Matière(s)",queryset=Matiere.objects.order_by('nom'))
	classe = forms.ModelMultipleChoiceField(label="Classe(s)",queryset=Classe.objects.order_by('annee','nom'),required=False)

	# validation du mot de passe
	def clean_motdepasse(self):
		user=User()
		if 'prenom' in self.cleaned_data:
			user.first_name=self.cleaned_data['prenom']
		if 'nom' in self.cleaned_data:
			user.last_name=self.cleaned_data['nom']
		data = self.cleaned_data['motdepasse']
		validate_password(data,user)
		return data

class EleveForm(forms.Form):
	nom = forms.CharField(label="Nom",max_length=30)
	prenom = forms.CharField(label="Prénom",max_length=30)
	motdepasse = forms.CharField(label="Mot de passe",max_length=30,required=False)
	ddn = forms.DateField(label="Date de naissance (pour ECTS, facultatif)", required=False,input_formats=['%d/%m/%Y','%j/%m/%Y','%d/%n/%Y','%j/%n/%Y'],widget=forms.TextInput(attrs={'placeholder': 'jj/mm/aaaa'}))
	ldn = forms.CharField(label="lieu de naissance (pour ECTS, facultatif)",required=False,max_length=50)
	ine = forms.CharField(label="N° étudiant INE (pour ECTS, facultatif)",required=False,max_length=11)
	email = forms.EmailField(label="Email(Facultatif)",max_length=50,required=False)
	photo = forms.ImageField(label="photo(jpg/png, 300x400)",required=False)
	classe = forms.ModelChoiceField(queryset=Classe.objects.order_by('annee','nom'),empty_label=None)
	lv1 = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=1).order_by('nom'),empty_label='----',required=False)
	lv2 = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=2).order_by('nom'),empty_label='----',required=False)

	def clean_motdepasse(self):
		user=User()
		if 'prenom' in self.cleaned_data:
			user.first_name=self.cleaned_data['prenom']
		if 'nom' in self.cleaned_data:
			user.last_name=self.cleaned_data['nom']
		data = self.cleaned_data['motdepasse']
		if data:
			validate_password(data,user)
		return data

	def clean_lv1(self):
		data = self.cleaned_data['lv1']
		if data is not None:
			if data not in self.cleaned_data['classe'].matieres.all():
				raise ValidationError("Cette langue ne fait pas partie des matières de cette classe")
		return data

	def clean_lv2(self):
		data = self.cleaned_data['lv2']
		if data is not None:
			if data not in self.cleaned_data['classe'].matieres.all():
				raise ValidationError("Cette langue ne fait pas partie des matières de cette classe")
		return data

	def clean_ine(self): # validation du numéro étudiant
		data = self.cleaned_data['ine']
		if data:
			if len(data) != 11:
				raise ValidationError("le numéro d'étudiant comporte 11 caractères")
			try:
				l=int(data[:-1])
				if l<=0 or not isinstance(l,int):
					raise ValidationError("les 10 premiers caractères doivent être des chiffres")
			except Exception:
				raise ValidationError("les 10 premiers caractères doivent être des chiffres")
			if not (65 <= ord(data[-1]) <= 90):
				raise ValidationError("le dernier caractère est une lettre ASCII majuscule")
		return data

class EleveFormMdp(forms.Form):
	nom = forms.CharField(label="Nom",max_length=30)
	prenom = forms.CharField(label="Prénom",max_length=30)
	motdepasse = forms.CharField(label="Mot de passe",max_length=30,required=True)
	email = forms.EmailField(label="Email(Facultatif)",max_length=50,required=False)
	ddn = forms.DateField(label="Date de naissance (pour ECTS, facultatif)", required=False,input_formats=['%d/%m/%Y','%j/%m/%Y','%d/%n/%Y','%j/%n/%Y'],widget=forms.TextInput(attrs={'placeholder': 'jj/mm/aaaa'}))
	ldn = forms.CharField(label="lieu de naissance (pour ECTS, facultatif)",required=False,max_length=50)
	ine = forms.CharField(label="N° étudiant INE (pour ECTS, facultatif)",required=False,max_length=11)
	photo = forms.ImageField(label="photo(jpg/png, 300x400)",required=False)
	classe = forms.ModelChoiceField(queryset=Classe.objects.order_by('annee','nom'),empty_label=None)
	lv1 = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=1).order_by('nom'),empty_label='----',required=False)
	lv2 = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=2).order_by('nom'),empty_label='----',required=False)

	def clean_lv1(self):
		data = self.cleaned_data['lv1']
		if data is not None:
			print(self.cleaned_data)
			if data not in self.cleaned_data['classe'].matieres.all():
				raise ValidationError("Cette langue ne fait pas partie des matières de cette classe")
		return data

	def clean_lv2(self):
		data = self.cleaned_data['lv2']
		if data is not None:
			if data not in self.cleaned_data['classe'].matieres.all():
				raise ValidationError("Cette langue ne fait pas partie des matières de cette classe")
		return data

	def clean_motdepasse(self):
		user=User()
		if 'prenom' in self.cleaned_data:
			user.first_name=self.cleaned_data['prenom']
		if 'nom' in self.cleaned_data:
			user.last_name=self.cleaned_data['nom']
		data = self.cleaned_data['motdepasse']
		validate_password(data,user)
		return data

	def clean_ine(self): # validation du numéro étudiant
		data = self.cleaned_data['ine']
		if data:
			if len(data) != 11:
				raise ValidationError("le numéro d'étudiant comporte 11 caractères")
			try:
				l=int(data[:-1])
				if l<=0 or not isinstance(l,int):
					raise ValidationError("les 10 premiers caractères doivent être des chiffres")
			except Exception:
				raise ValidationError("les 10 premiers caractères doivent être des chiffres")
			if not (65 <= ord(data[-1]) <= 90):
				raise ValidationError("le dernier caractère est une lettre ASCII majuscule")
		return data

class ProfForm(forms.Form):
	def __init__(self,classe, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.classe=classe
		for matiere in classe.matieres.all():
			query=Colleur.objects.filter(matieres=matiere,classes=classe,user__is_active=True).order_by('user__last_name','user__last_name')
			self.fields[str(matiere.pk)] = forms.ModelChoiceField(label=matiere,queryset=query,required=False)
		query2 = Colleur.objects.filter(classes=classe,user__is_active=True)
		self.fields['profprincipal'] = forms.ModelChoiceField(label="prof principal",queryset=query2,required=False)

	def clean(self):
		"""Vérifie que le prof principal est bien choisi parmi les profs de la classe"""
		if self.cleaned_data['profprincipal'] not in [self.cleaned_data[str(matiere.pk)] for matiere in self.classe.matieres.all()]:
			raise ValidationError("le professeur principal doit faire partie des professeurs de la classe")

	def save(self):
		"""Sauvegarde en base de données les données du formulaire"""
		matieres_avec_prof=[matiere for matiere in self.classe.matieres.all() if self.cleaned_data[str(matiere.pk)]] # liste des matieres
		colleurs_avec_prof=[self.cleaned_data[str(matiere.pk)] for matiere in self.classe.matieres.all() if self.cleaned_data[str(matiere.pk)]] # liste des colleurs
		# on efface les profs correspondants à la classe courante
		Prof.objects.filter(classe=self.classe).delete()
		# on crée les nouvelles entités profs
		Prof.objects.bulk_create([Prof(classe=self.classe,matiere=matiere,modifgroupe=conf.config.DEFAULT_MODIF_GROUPE,modifcolloscope=conf.config.DEFAULT_MODIF_COLLOSCOPE,colleur=colleur) for matiere,colleur in zip(matieres_avec_prof,colleurs_avec_prof)])
		# mise à jour du prof principal
		if self.cleaned_data['profprincipal']:
			self.classe.profprincipal=self.cleaned_data['profprincipal']
		else:
			self.classe.profprincipal = None
		self.classe.save()

class CustomMultipleChoiceField(forms.ModelMultipleChoiceField):
	def label_from_instance(*args,**kwargs):
		return ""

class SelectColleurForm(forms.Form):
	def __init__(self,matiere=None,classe=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		query = Colleur.objects
		if matiere:
			query = query.filter(matieres=matiere)
		if classe:
			query = query.filter(classes=classe)
		query=query.select_related('user','etablissement').prefetch_related('matieres','classes').order_by('user__last_name','user__first_name')
		self.fields['colleur'] = CustomMultipleChoiceField(queryset=query, required=True,widget = forms.CheckboxSelectMultiple)
		self.fields['colleur'].empty_label=None

class SelectEleveForm(forms.Form):
	def __init__(self,klasse=None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if klasse:
			query = Eleve.objects.filter(classe=klasse).select_related('user','classe').order_by('classe__nom','user__last_name','user__first_name')
		else:
			query=Eleve.objects.select_related('user','classe').order_by('classe__nom','user__last_name','user__first_name')
		self.fields['eleve'] = CustomMultipleChoiceField(queryset=query, required=True,widget = forms.CheckboxSelectMultiple)
		self.fields['eleve'].empty_label=None
		self.fields['klasse'] = forms.ModelChoiceField(queryset=Classe.objects.order_by('annee','nom'),required=False)
		self.fields['klasse'].empty_label=None
		self.fields['lv1'] = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=1).order_by('nom'),required=False)
		self.fields['lv2'] = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=2).order_by('nom'),required=False)

class ClasseSelectForm(forms.Form):
	query=Classe.objects.order_by('nom')
	classe=forms.ModelChoiceField(label="Classe",queryset=query, empty_label="Toutes",required=False)

class MatiereClasseSelectForm(forms.Form):
	matiere=forms.ModelChoiceField(label="Matière",queryset=Matiere.objects.order_by('nom'), empty_label="Toutes",required=False)
	classe=forms.ModelChoiceField(label="Classe",queryset=Classe.objects.order_by('nom'), empty_label="Toutes",required=False)

	def clean(self):
		if self.cleaned_data['classe'] is not None and self.cleaned_data['matiere'] is not None and self.cleaned_data['matiere'] not in self.cleaned_data['classe'].matieres.all():
			raise ValidationError("la classe %(classe)s n'a pas pour matière %(matiere)s",params={'classe':self.cleaned_data['classe'],'matiere':self.cleaned_data['matiere']})

class CsvForm(forms.Form):
	nom = forms.CharField(label="intitulé du champ nom",required=True,max_length=30)
	prenom = forms.CharField(label="intitulé du champ prénom",required=True,max_length=30)
	ddn = forms.CharField(label="intitulé du champ date de naissance (pour ECTS, facultatif)",required=False,max_length=30)
	ldn = forms.CharField(label="intitulé du champ lieu de naissance (pour ECTS, facultatif)",required=False,max_length=50)
	ine = forms.CharField(label="intitulé du champ numéro INE (pour ETCS, facultatif)",required=False,max_length=30)
	email = forms.CharField(label="intitulé du champ email(facultatif)",required=False,max_length=30)
	fichier = forms.FileField(label="Fichier csv",required=True)
	classe=forms.ModelChoiceField(label="Classe",queryset=Classe.objects.order_by('nom'), empty_label="Non définie",required=False) 




