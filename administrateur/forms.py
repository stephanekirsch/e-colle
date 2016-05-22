#-*- coding: utf-8 -*-
from django import forms
from accueil.models import Classe, Matiere, Etablissement, Semaine, Colleur, Eleve, JourFerie, User, Prof
from django.forms.extras.widgets import SelectDateWidget
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from ecolle.settings import DEFAULT_MODIF_COLLOSCOPE, DEFAULT_MODIF_GROUPE, RESOURCES_ROOT
from lxml import etree
from random import choice
from django.db.models import Func, F

class ColleurFormSetMdp(forms.BaseFormSet):
	def clean(self):
		""""Vérifie, dans le cas où les formulaires valident individuellement, que 2 colleurs n'ont pas le même identifiant 
		et insère les erreurs individuellement dans les champs identifiant"""
		if any(self.errors):
			# s'il y a déjà des erreurs de validation individuelles, on ne fait rien.
			return None
		identifiants = dict() # dictionnaire des identifiant successifs avec en valeur leur rang dans le formulaire
		errors=False
		for i,form in enumerate(self.forms):
			identifiant = form.cleaned_data['identifiant'] # on récupère l'identifiant
			if identifiant in identifiants: # s'il est déjà présent dans le formulaire, on indique l'erreur dans le champ.
				errors=True
				form._errors['identifiant']=forms.utils.ErrorList(['Identifiant déjà présent dans le formulaire'])
				if identifiants[identifiant] !=-1: # on indique l'erreur dans le premier champs présentant le doublon d'identifiant si ce n'est pas déjà fait
					self.forms[identifiants[identifiant]]._errors['identifiant']=forms.utils.ErrorList(['Identifiant déjà présent dans le formulaire'])
					identifiants[identifiant]=-1 # on passe le rang à -1 pour ne pas remettre une erreur inutilement par la suite.
			else:
				identifiants[identifiant]=i # on rajoute le couple {identifiant: rang} dans le dictionnaire identifiants
		if errors:
			raise ValidationError("Un même identifiant ne peut apparaître plusieurs fois dans le formulaire",code="uniqueness violation")

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
			user = User(username=form.cleaned_data['identifiant'],first_name=form.cleaned_data['prenom'],last_name=form.cleaned_data['nom'],email=form.cleaned_data['email'],colleur=colleur)
			user.set_password(form.cleaned_data['motdepasse'])
			user.save()		

class ColleurFormSet(ColleurFormSetMdp): # ColleurFormSet hérite de ColleurFormSetMdp pour profiter de sa méthode clean
	def __init__(self,chaine_colleurs=[],*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.chaine_colleurs=chaine_colleurs

	def clean(self):
		""""Vérifie, dans le cas où les formulaires valident individuellement, que 2 colleurs n'ont pas le même identifiant 
		et insère les erreurs individuellement dans les champs identifiant. Dans ce cas une ValidationError est levée.
		Si aucun erreur n'est rencontrée, vérifie ensuite s'il n'y a pas de doublon avec la base de donnée"""
		super().clean() # on vérifie qu'il n'y pas de doublon d'identifiant dans le formulaire
		# on vérifie maintenant qu'il ne va pas y avoir de doublons d'identifiants en BDD
		users=set() # la liste des pk des utilisateurs dont l'identifiant est modifié
		for colleur,form in zip(self.chaine_colleurs,self.forms):
			if form.cleaned_data['identifiant']!= colleur.user.username: # si l'identifiant change, on vérifie qu'il n'est pas déjà en base de donnée après enregistrement des colleurs précédents
				try: # on cherche si un utilisateur avec le même identifiant existe déjà en BDD
					user=User.objects.get(username=form.cleaned_data['identifiant']) 
				except Exception: # si on n'en trouve pas il n'y a pas de problème (il ne peut y en avoir un identique dans un formulaire précédent sans que super().clean(self) lève une exception)
					pass
				else: # sinon on regarde si cet identifiant va être modifié par un des formulaires précédents
					if user.pk not in users: # si ce n'est pas le cas, on insère une erreur
						form._errors['identifiant']=forms.utils.ErrorList(['Identifiant déjà pris par un autre colleur'])
				finally:
					users.add(colleur.user.pk) # on rajoute l'identifiant de l'utilisateur courant dans le set users
				
	def save(self):
		"""Sauvegarde (mise à jour) en BDD les colleurs/users du formulaire"""
		for colleur,form in zip(self.chaine_colleurs,self.forms):
			colleur.grade=form.cleaned_data['grade']
			colleur.etablissement=form.cleaned_data['etablissement']
			colleur.classes=form.cleaned_data['classe']
			colleur.matieres=form.cleaned_data['matiere']
			colleur.save()
			user=colleur.user
			user.username=form.cleaned_data['identifiant']
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
	tree=etree.parse(RESOURCES_ROOT+'classes.xml')
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
				query = Matiere.objects.annotate(nom_lower=Func(F('nom'), function='LOWER')).filter(nom_lower=matiere.get('nom').lower(),temps=int(matiere.get("temps")))
				if query.exists():
					matiere = query[0]
				else:
					matiere = Matiere(nom=matiere.get("nom"),temps=matiere.get("temps"),couleur=choice(list(zip(*Matiere.LISTE_COULEURS))[0]))
					matiere.save()
				listeMatieres.append(matiere)
			nouvelleClasse.matieres.add(*listeMatieres)
		else:
			super().save()

class MatiereForm(forms.ModelForm):
	class Meta:
		model = Matiere
		fields=['nom','couleur','temps']

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
	identifiant = forms.CharField(max_length=30)
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
		if 'first_name' in self.cleaned_data:
			user.first_name=self.cleaned_data['first_name']
		if 'last_name' in self.cleaned_data:
			user.last_name=self.cleaned_data['last_name']
		data = self.cleaned_data['motdepasse']
		if data:
			validate_password(data,user)
		return data

class ColleurFormMdp(forms.Form):
	LISTE_GRADE=enumerate(["autre","certifié","bi-admissible","agrégé","chaire supérieure"])
	nom = forms.CharField(max_length=30)
	prenom = forms.CharField(label="Prénom",max_length=30)
	identifiant = forms.CharField(max_length=30)
	motdepasse = forms.CharField(label="Mot de passe",max_length=30,required=True)
	email = forms.EmailField(label="email(facultatif)",max_length=50,required=False)
	grade = forms.ChoiceField(choices=LISTE_GRADE)
	etablissement = forms.ModelChoiceField(queryset=Etablissement.objects.order_by('nom'),empty_label="inconnu")
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

	# validation de l'unicité de l'identifiant (pour éviter une erreur lors de l'enregistrement)
	def clean_identifiant(self):
		data = self.cleaned_data['identifiant']
		if User.objects.filter(username=data).exists():
			raise ValidationError(
    		"l'identifiant %(value)s est déjà pris",
    		code='uniqueness violation',
    		params={'value': data},
			)
		return data

class EleveForm(forms.Form):
	nom = forms.CharField(label="Nom",max_length=30)
	prenom = forms.CharField(label="Prénom",max_length=30)
	motdepasse = forms.CharField(label="Mot de passe",max_length=30,required=False)
	email = forms.EmailField(label="Email(Facultatif)",max_length=50,required=False)
	photo = forms.ImageField(label="photo(jpg/png, 300x400)",required=False)
	classe = forms.ModelChoiceField(queryset=Classe.objects.order_by('annee','nom'),empty_label=None)

class EleveFormMdp(forms.Form):
	nom = forms.CharField(label="Nom",max_length=30)
	prenom = forms.CharField(label="Prénom",max_length=30)
	motdepasse = forms.CharField(label="Mot de passe",max_length=30,required=True)
	email = forms.EmailField(label="Email(Facultatif)",max_length=50,required=False)
	photo = forms.ImageField(label="photo(jpg/png, 300x400)",required=False)
	classe = forms.ModelChoiceField(queryset=Classe.objects.order_by('annee','nom'),empty_label=None)

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
		Prof.objects.bulk_create([Prof(classe=self.classe,matiere=matiere,modifgroupe=DEFAULT_MODIF_GROUPE,modifcolloscope=DEFAULT_MODIF_COLLOSCOPE,colleur=colleur) for matiere,colleur in zip(matieres_avec_prof,colleurs_avec_prof)])
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

class ClasseSelectForm(forms.Form):
	query=Classe.objects.order_by('nom')
	classe=forms.ModelChoiceField(label="Classe",queryset=query, empty_label="Toutes",required=False)

class MatiereClasseSelectForm(forms.Form):
	matiere=forms.ModelChoiceField(label="Matière",queryset=Matiere.objects.order_by('nom'), empty_label="Toutes",required=False)
	classe=forms.ModelChoiceField(label="Classe",queryset=Classe.objects.order_by('nom'), empty_label="Toutes",required=False)

class CsvForm(forms.Form):
	nom = forms.CharField(label="intitulé du champ nom",required=True,max_length=20)
	prenom = forms.CharField(label="intitulé du champ prénom",required=True,max_length=20)
	fichier = forms.FileField(label="Fichier csv",required=True)
	classe=forms.ModelChoiceField(label="Classe",queryset=Classe.objects.order_by('nom'), empty_label="Non définie",required=False) 




