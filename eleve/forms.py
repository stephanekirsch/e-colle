#-*- coding: utf-8 -*-
from django import forms
from accueil.models import Matiere, DevoirRendu, Planche

class EleveConnexionForm(forms.Form):
	username = forms.CharField(label="Identifiant")
	password = forms.CharField(label="Mot de passe",widget=forms.PasswordInput)

class MatiereForm(forms.Form):
	def __init__(self, classe, *args, planches=False, **kwargs):
		super().__init__(*args, **kwargs)
		if planches:
			query=Matiere.objects.filter(matieresclasse=classe,planche=True).distinct()
		else:
			query=Matiere.objects.filter(matieresclasse=classe).distinct()
		self.fields['matiere']=forms.ModelChoiceField(label="Matière",queryset=query, empty_label="Toutes",required=False)

class CopieForm(forms.ModelForm):
	class Meta:
		model = DevoirRendu
		fields = ['fichier']

	def save(self, *args, **kwargs):
		if self.cleaned_data['fichier'] in (False, None): # si on efface la copie rendue, ou si on ne soumet aucun fichier
			if self.instance.id:
				self.instance.delete()
		else: # sinon on applique la sauvegarde classique
			super().save()

class PlancheForm(forms.ModelForm):
	class Meta:
		model = Planche
		fields=['commentaire']

	def __init__(self, eleve, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.eleve = eleve

	def save(self):
		self.instance.eleve = self.eleve
		super().save()