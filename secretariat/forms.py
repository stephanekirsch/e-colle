#-*- coding: utf-8 -*-
from django import forms
from accueil.models import Note, Matiere, Classe, Semaine, Ramassage, Creneau, Colleur, Groupe 
from django.db.models import Min, Max
from datetime import date, timedelta
from django.core.exceptions import ValidationError

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