#-*- coding: utf-8 -*-
from django import forms
from django.forms.widgets import Input
from accueil.models import Colleur, Groupe, Matiere, Destinataire, Message, User, Classe, Prof
from administrateur.forms import CustomMultipleChoiceField
from administrateur.forms import validate_password
from django.db.models import Q

class GroupeMultipleChoiceField(forms.ModelMultipleChoiceField):
	def label_from_instance(self,groupe,*args,**kwargs):
		return groupe.nom+": "+"/".join([str(eleve.user.last_name.upper()) for eleve in groupe.groupeeleve.all()])

class UserForm(forms.Form):
	email = forms.EmailField(label="Email",max_length=75,required=False)
	motdepasse = forms.CharField(label="Mot de passe",widget=forms.PasswordInput,required=False)
	
	def clean_motdepasse(self):
		data = self.cleaned_data['motdepasse']
		if data:
			validate_password(data)
		return data

class ColleurMultipleChoiceField(forms.ModelMultipleChoiceField):
	def __init__(self,classe,matiere=False,*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.classe=classe
		self.matiere=matiere

	def label_from_instance(self,colleur,*args,**kwargs):
		chaine = str(colleur)
		if not self.matiere:
			chaine += " ("+ " et ".join([str(mat).title() for mat in Matiere.objects.filter(matiereprof__colleur=colleur,matiereprof__classe=self.classe)]) +")"
		return chaine

class UserProfprincipalForm(forms.Form):
	def __init__(self,colleur,classes,*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.fields['email']=forms.EmailField(label="Email",max_length=75)
		self.fields['motdepasse']=forms.CharField(label="Mot de passe",widget=forms.PasswordInput,required=False)
		for classe in classes:
			self.fields["{}_groupe".format(classe.pk)] = ColleurMultipleChoiceField(classe,label="Droits de modifier les groupes de {}".format(classe.nom.upper()),queryset=Colleur.objects.filter(colleurprof__classe=classe,user__is_active=True).select_related('user').exclude(pk=colleur.pk),widget=forms.CheckboxSelectMultiple,required=False)
			self.fields["{}_colloscope".format(classe.pk)] = ColleurMultipleChoiceField(classe,label="Droits de modifier le colloscope de {}".format(classe.nom.upper()),queryset=Colleur.objects.filter(colleurprof__classe=classe,user__is_active=True).select_related('user').exclude(pk=colleur.pk),widget=forms.CheckboxSelectMultiple,required=False)

	def clean_motdepasse(self):
		data = self.cleaned_data['motdepasse']
		if data:
			validate_password(data)
		return data


class SelectMessageForm(forms.Form):
	def __init__(self,user,recu=True,*args, **kwargs):
		super().__init__(*args, **kwargs)
		if recu:
			query=Destinataire.objects.filter(user=user).select_related('message','user').order_by('-message__date')
		else:
			query=Message.objects.filter(auteur=user,hasAuteur=True).order_by('-date')
		self.fields['message'] = CustomMultipleChoiceField(queryset=query, required=True,widget = forms.CheckboxSelectMultiple)
		self.fields['message'].empty_label=None

class ReponseForm(forms.Form):
	def __init__(self,destinataire,*args, **kwargs):
		super().__init__(*args,**kwargs)
		self.fields['destinataire'] = forms.CharField(label="Destinataire",initial=str(destinataire.message.auteur),required=False)
		self.fields['destinataire'].widget.attrs={'disabled':True}
		self.fields['titre'] = forms.CharField(label="titre",max_length=100,required=True)
		self.fields['titre'].widget.attrs={'size':50}
		self.fields['corps'] = forms.CharField(label="corps du message",widget=forms.Textarea,required=True,max_length=2000)
		self.fields['corps'].widget.attrs={'cols':60,'rows':15}

class EcrireForm(forms.Form):
	def __init__(self,user,*args, **kwargs):
		super().__init__(*args, **kwargs)
		self.champs = []
		if user.colleur:
			classes = user.colleur.classes.all()
			classesprof = user.colleur.colleurprof.all()
			matieres = user.colleur.matieres.all()
			for classe in classes:
				listematieres=[]
				listecolleurs=[]
				listeprofs=False
				matieresprof = classesprof.filter(classe=classe).exists()
				prof=False
				if matieresprof:
					query = Colleur.objects.filter(colleurprof__classe=classe).exclude(pk=user.colleur.pk).distinct().order_by('user__last_name')
				else:
					query = Colleur.objects.filter(colleurprof__classe=classe,colleurprof__matiere__in=matieres).distinct().order_by('user__last_name')
				self.fields['classeprof_{}'.format(classe.pk)] = ColleurMultipleChoiceField(classe,False,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
				listeprofs = self['classeprof_{}'.format(classe.pk)]
				self.fields['matiereprof_{}'.format(classe.pk)]=forms.BooleanField(label="Profs",required=False)
				prof=self['matiereprof_{}'.format(classe.pk)]
				self.fields['colleurs_{}'.format(classe.pk)]=forms.BooleanField(label="Colleurs",required=False)
				colleur = self['colleurs_{}'.format(classe.pk)]
				for matiere in Matiere.objects.filter(matiereprof__colleur=user.colleur,matiereprof__classe=classe):
					self.fields['matiere_{}_{}'.format(classe.pk,matiere.pk)]=forms.BooleanField(label=matiere.nom.title(),required=False)
					listecolleurs.append(self['matiere_{}_{}'.format(classe.pk,matiere.pk)])
					query = Colleur.objects.filter(classes=classe,matieres=matiere,user__is_active=True).exclude(pk=user.colleur.pk).select_related('user').order_by('user__last_name')
					self.fields['classematiere_{}_{}'.format(classe.pk,matiere.pk)] = ColleurMultipleChoiceField(classe,True,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
					listematieres.append(self['classematiere_{}_{}'.format(classe.pk,matiere.pk)])
				self.fields['matieregroupe_{}'.format(classe.pk)]=forms.BooleanField(label="Élèves",required=False)
				query2 = Groupe.objects.filter(groupeeleve__classe=classe).prefetch_related('groupeeleve__user').distinct()
				self.fields['classegroupe_{}'.format(classe.pk)] = GroupeMultipleChoiceField(queryset=query2,widget=forms.CheckboxSelectMultiple,required=False)
				colleurs = zip(listecolleurs,listematieres) if listecolleurs else False
				self.champs.append((classe,prof,listeprofs,colleur,colleurs,self['matieregroupe_{}'.format(classe.pk)],self['classegroupe_{}'.format(classe.pk)]))
		elif user.username=="Secrétariat" or user.username=="admin":
			classes = Classe.objects.all()
			for classe in classes:
				listematieres=[]
				listecolleurs=[]
				listeprofs=False
				prof=False
				query = Colleur.objects.filter(colleurprof__classe=classe).distinct().order_by('user__last_name')
				self.fields['classeprof_{}'.format(classe.pk)] = ColleurMultipleChoiceField(classe,False,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
				listeprofs = self['classeprof_{}'.format(classe.pk)]
				self.fields['matiereprof_{}'.format(classe.pk)]=forms.BooleanField(label="Profs",required=False)
				prof=self['matiereprof_{}'.format(classe.pk)]
				self.fields['colleurs_{}'.format(classe.pk)]=forms.BooleanField(label="Colleurs",required=False)
				colleur = self['colleurs_{}'.format(classe.pk)]
				for matiere in classe.matieres.all():
					self.fields['matiere_{}_{}'.format(classe.pk,matiere.pk)]=forms.BooleanField(label=matiere.nom.title(),required=False)
					listecolleurs.append(self['matiere_{}_{}'.format(classe.pk,matiere.pk)])
					query = Colleur.objects.filter(classes=classe,matieres=matiere,user__is_active=True).select_related('user').order_by('user__last_name')
					self.fields['classematiere_{}_{}'.format(classe.pk,matiere.pk)] = ColleurMultipleChoiceField(classe,True,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
					listematieres.append(self['classematiere_{}_{}'.format(classe.pk,matiere.pk)])
				self.fields['matieregroupe_{}'.format(classe.pk)]=forms.BooleanField(label="Élèves",required=False)
				query2 = Groupe.objects.filter(groupeeleve__classe=classe).prefetch_related('groupeeleve__user').distinct()
				self.fields['classegroupe_{}'.format(classe.pk)] = GroupeMultipleChoiceField(queryset=query2,widget=forms.CheckboxSelectMultiple,required=False)
				colleurs = zip(listecolleurs,listematieres) if listecolleurs else False
				self.champs.append((classe,prof,listeprofs,colleur,colleurs,self['matieregroupe_{}'.format(classe.pk)],self['classegroupe_{}'.format(classe.pk)]))
		self.colspan = len(self.champs)
		self.colspansubmit = self.colspan+1
		nb = classes.count()
		self.rowspan,self.reste = (nb+1)>>1 ,nb&1
		self.fields['titre'] = forms.CharField(label="titre",max_length=100,required=True)
		self.fields['titre'].widget.attrs={'size':50}
		self.fields['corps'] = forms.CharField(label="corps du message",widget=forms.Textarea,required=True,max_length=2000)
		self.fields['corps'].widget.attrs={'cols':60,'rows':15}
