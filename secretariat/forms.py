#-*- coding: utf-8 -*-
from django import forms
from accueil.models import Note, Matiere, Classe, Semaine, Ramassage, Creneau, Colleur, Groupe #, Dispo, Frequence, Colleurgroupe
from administrateur.forms import CustomMultipleChoiceField
from django.db.models import Min, Max
from datetime import date, timedelta
from django.core.exceptions import ValidationError
# from fractions import Fraction

class RamassageForm(forms.ModelForm):
	class Meta:
		model = Ramassage
		fields=['moisDebut','moisFin']

	def clean(self):
		"""Vérifie que moisDebut est antérieur à mois Fin, ainsi que l'unicité du couple moisDebut/moisFin"""
		if self.cleaned_data['moisDebut'] > self.cleaned_data['moisFin']:
			raise ValidationError('le mois de début doit être antérieur au mois de fin')
		if Ramassage.objects.filter(moisDebut=self.cleaned_data['moisDebut'],moisFin=self.cleaned_data['moisFin']).exists():
			raise ValidationError('Ce ramassage existe déjà',code="uniqueness violation")

class MoisForm(forms.Form):
	def __init__(self,moisMin,moisMax, *args, **kwargs):
		super().__init__(*args, **kwargs)
		LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
		nbMois=12*(moisMax.year-moisMin.year)+moisMax.month-moisMin.month+1
		ListeMoisMin=[False]*nbMois
		ListeMoisMax=[False]*nbMois
		for i in range(nbMois):
			mois=date(moisMin.year+(moisMin.month+i-1)//12,(moisMin.month+i-1)%12+1,1)
			ListeMoisMin[i]=(mois,"{} {}".format(LISTE_MOIS[mois.month],mois.year))
			if mois.month==12:
				ListeMoisMax[i]=(date(mois.year,12,31),"{} {}".format(LISTE_MOIS[12],mois.year))
			else:
				ListeMoisMax[i]=(date(mois.year,mois.month+1,1)-timedelta(days=1),ListeMoisMin[i][1])
		self.fields['moisMin']=forms.ChoiceField(choices=ListeMoisMin,initial=ListeMoisMin[0][0])
		self.fields['moisMax']=forms.ChoiceField(choices=ListeMoisMax,initial=ListeMoisMax[nbMois-1][0])

class MatiereClasseSelectForm(forms.Form):
	matiere=forms.ModelChoiceField(label="Matière",queryset=Matiere.objects.order_by('nom'),required=True,empty_label=None)
	classe=forms.ModelChoiceField(label="Classe",queryset=Classe.objects.order_by('nom'),required=True,empty_label=None)

class MatiereClasseSemaineSelectForm(forms.Form):
	matiere=forms.ModelChoiceField(label="Matière",queryset=Matiere.objects.order_by('nom'),required=True,empty_label=None)
	classe=forms.ModelChoiceField(label="Classe",queryset=Classe.objects.order_by('nom'),required=True,empty_label=None)
	try:
		query=Semaine.objects.order_by('lundi')
		semin=forms.ModelChoiceField(queryset=query, empty_label=None,initial=query[0],required=True)
		semax=forms.ModelChoiceField(queryset=query, empty_label=None,initial=query[query.count()-1],required=True)
	except Exception:
		semin=forms.ModelChoiceField(queryset=Semaine.objects.none(), empty_label=None,required=True)
		semax=forms.ModelChoiceField(queryset=Semaine.objects.none(), empty_label=None,required=True)

	def clean(self):
		if self.cleaned_data['matiere'] not in self.cleaned_data['classe'].matieres.all():
			raise ValidationError("la classe %(classe)s n'a pas pour matière %(matiere)s",params={'classe':self.cleaned_data['classe'],'matiere':self.cleaned_data['matiere']})

class SelectClasseSemaineForm(forms.Form):
	classes = forms.ModelMultipleChoiceField(queryset=Classe.objects.all(),label="classes",widget=forms.CheckboxSelectMultiple,required=True)
	query=Semaine.objects.all()
	try:
		semin = forms.ModelChoiceField(queryset=query,label="semaine de départ",initial=query[0])
		semax = forms.ModelChoiceField(queryset=query,label="semaine de fin",initial=query[len(query)-1])
	except Exception:
		semin = forms.ModelChoiceField(queryset=query,label="semaine de départ")
		semax = forms.ModelChoiceField(queryset=query,label="semaine de fin")

# class DispoForm(forms.Form):
# 	def __init__(self,colleur,*args,**kwargs):
# 		super().__init__(*args,**kwargs)
# 		self.colleur=colleur
# 		LISTE_JOURS=["lundi","mardi","mercredi","jeudi","vendredi","samedi"]
# 		creneaux =  [(96*x+y,"{} {}h{:02d}".format(LISTE_JOURS[x],y//4,15*(y%4))) for x,y in sorted({(creneau.jour,creneau.heure) for creneau in Creneau.objects.filter(classe__in=colleur.classes.all())})]
# 		self.fields['dispo'] = forms.MultipleChoiceField(label=str(colleur),choices=creneaux,widget=forms.CheckboxSelectMultiple,required=False)

# class DispoFormSet(forms.BaseFormSet):
# 	def __init__(self,chaine_colleurs,*args,**kwargs):
# 		super().__init__(*args,**kwargs)
# 		self.chaine_colleurs=chaine_colleurs

# 	def get_form_kwargs(self,index):
# 		if index is None:
# 			return None
# 		return {'colleur':self.chaine_colleurs[index]}
				
# 	def save(self):
# 		"""Sauvegarde (mise à jour) en BDD les dispos du formulaire"""
# 		for form in self:
# 			listedispo=[]
# 			for dispo in form.cleaned_data['dispo']:
# 				dispo=int(dispo)
# 				newdispo, created = Dispo.objects.get_or_create(jour=dispo//96,heure=dispo%96)
# 				listedispo.append(newdispo)
# 			form.colleur.dispos = listedispo

# class FrequenceForm(forms.Form):
# 	def __init__(self,classe, *args, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		self.classe=classe
# 		self.champs=[]
# 		for matiere in Matiere.objects.filter(matieresclasse=classe,temps=20).order_by('nom'):
# 			LISTE_CHOIX = [(None,"-----------")]+[(i,"{} colle par semaine".format(Fraction(i,24))) for i in (24,18,16,12,8,6,3)]
# 			self.fields[str(matiere.pk)] = forms.ChoiceField(label=str(matiere),choices=LISTE_CHOIX,required=False)
# 			self.fields[str(matiere.pk)+"_"] = forms.BooleanField(required=False)
# 			self.fields[str(matiere.pk)+"-"] = forms.ChoiceField(label=str(matiere),choices=zip(range(1,9),range(1,9)),required=False)

# 	def save(self):
# 		"""Sauvegarde en base de données les données du formulaire"""
# 		matieres_avec_frequence=[matiere for matiere in Matiere.objects.filter(matieresclasse=self.classe,temps=20).order_by('nom','precision') if self.cleaned_data[str(matiere.pk)]] # liste des matieres
# 		print(matieres_avec_frequence)
# 		# on efface les frequences correspondants à la classe courante
# 		Frequence.objects.filter(classe=self.classe).delete()
# 		# on crée les nouvelles entités Fréquence
# 		Frequence.objects.bulk_create([Frequence(classe=self.classe,matiere=matiere,frequence=self.cleaned_data[str(matiere.pk)],repartition=self.cleaned_data[str(matiere.pk)+"_"],premiere=self.cleaned_data[str(matiere.pk)+"-"]) for matiere in matieres_avec_frequence])

# class ColleurgroupeForm(forms.Form):
# 	def __init__(self,classe,matiere,*args,**kwargs):
# 		super().__init__(*args,**kwargs)
# 		self.classe=classe
# 		self.matiere = matiere
# 		self.nbgroupes = Groupe.objects.filter(classe=classe).count()
# 		self.nbcolleurs = Colleur.objects.filter(classes=classe,matieres=matiere).count()
# 		if matiere in classe.matieres.all():
# 			for colleur in Colleur.objects.filter(classes=classe,matieres=matiere):
# 				self.fields[str(colleur.pk)] = forms.ChoiceField(label=str(colleur),choices=enumerate(range(self.nbgroupes+1)))
# 	def save(self):
# 		# on efface les éventuelles entités précédentes
# 		Colleurgroupe.objects.filter(matiere=self.matiere,classe=self.classe).delete()
# 		# on insère les nouvelles en une fois
# 		Colleurgroupe.objects.bulk_create([Colleurgroupe(classe=self.classe,matiere=self.matiere,colleur=colleur,nbgroupes=self.cleaned_data[str(colleur.pk)]) for colleur in Colleur.objects.filter(classes=self.classe,matieres=self.matiere) if int(self.cleaned_data[str(colleur.pk)])])

# class ColleurgroupeFormSet(forms.BaseFormSet):
# 	def __init__(self,classe,*args,**kwargs):
# 		super().__init__(*args,**kwargs)
# 		self.classe=classe
# 		self.matieres=list(classe.matieres.filter(temps=20))

# 	def get_form_kwargs(self,index):
# 		if index is None:
# 			return None
# 		return {'classe':self.classe,'matiere':self.matieres[index]}

# 	def save(self):
# 		for form in self:
# 			form.save()

# class PlanificationForm(forms.Form):
# 	try:
# 		query=Semaine.objects.order_by('lundi')
# 		semin=forms.ModelChoiceField(label="Semaine de début",queryset=query, empty_label=None,initial=query[0],required=True)
# 		semax=forms.ModelChoiceField(label="Semaine de fin",queryset=query, empty_label=None,initial=query[query.count()-1],required=True)
# 	except Exception:
# 		semin=forms.ModelChoiceField(label="Semaine de début",queryset=Semaine.objects.none(), empty_label=None,required=True)
# 		semax=forms.ModelChoiceField(label="Semaine de fin",queryset=Semaine.objects.none(), empty_label=None,required=True)
# 	classes = forms.ModelMultipleChoiceField(label="classes",queryset=Classe.objects.all(),required=True)

# 	def clean(self):
# 		if self.cleaned_data['semin'].lundi>self.cleaned_data['semax'].lundi:
# 			raise ValidationError('La semaine de début doit être antérieure à celle de fin')
