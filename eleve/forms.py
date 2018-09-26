#-*- coding: utf-8 -*-
from django import forms
from accueil.models import Eleve, Matiere, User

class EleveConnexionForm(forms.Form):
	username = forms.CharField(label="Identifiant")
	password = forms.CharField(label="Mot de passe",widget=forms.PasswordInput)

class MatiereForm(forms.Form):
	def __init__(self, classe, *args, **kwargs):
		super().__init__(*args, **kwargs)
		query=Matiere.objects.filter(matieresclasse=classe).distinct()
		self.fields['matiere']=forms.ModelChoiceField(label="Matière",queryset=query, empty_label="Toutes",required=False)