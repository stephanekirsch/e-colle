#-*- coding: utf-8 -*-
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from accueil.models import Classe, Matiere, User, Colleur, Prof, Message, Destinataire, Eleve
from accueil.forms import UserForm, UserProfprincipalForm, SelectMessageForm, EcrireForm, ReponseForm
from django.contrib import messages as messagees
from ecolle.settings import IP_FILTRE_ADMIN, IP_FILTRE_ADRESSES
import re

def home(request):
	"""Renvoie la vue d'accueil ou, si l'utilisateur est déjà identifié, redirige vers la section adéquate"""
	user=request.user
	if user.is_authenticated():
		if user.username=="admin":
			return redirect('action_admin')
		elif user.username=="Secrétariat":
			return redirect('action_secret')
		elif user.colleur:
			return redirect('action_colleur')
		elif user.eleve:
			return redirect('action_eleve')
	classes=Classe.objects.all()
	matieres=list(Matiere.objects.all())
	for i in range(len(matieres)-1,0,-1):
		if matieres[i].nom.lower() == matieres[i-1].nom.lower():
			matieres.pop(i)
	show_admin=True
	if IP_FILTRE_ADMIN:
		show_admin=False
		user_ip = request.META['REMOTE_ADDR']
		for ip in IP_FILTRE_ADRESSES:
			authenticated_by_ip = re.compile(ip).match(user_ip)
			if authenticated_by_ip:
				show_admin = True
				break
	return render(request,'accueil/home.html',{'classes':classes,'matieres':matieres,'show_admin':show_admin})

def deconnexion(request):
	"""Déconnecte l'utilisateur courant et redirige vers la page d'accueil"""
	logout(request)
	return redirect('accueil')

@login_required(login_url='accueil')
def profil(request):
	"""Renvoie la vue du profil où on peut modifier son email et/ou son mot de passe"""
	user=request.user
	if not user.is_authenticated():
		return HttpResponseForbidden("Vous devez être connecté pour accéder à cette page")
	profprincipal = bool(user.colleur and Classe.objects.filter(profprincipal=user.colleur))
	if profprincipal:
		classes = Classe.objects.filter(profprincipal=user.colleur)
		initial = {'email':user.email}
		for classe in classes:
			initial["{}_groupe".format(classe.pk)] = Colleur.objects.filter(colleurprof__classe=classe,colleurprof__modifgroupe=True)
			initial["{}_colloscope".format(classe.pk)] = Colleur.objects.filter(colleurprof__classe=classe,colleurprof__modifcolloscope=True)
		form = UserProfprincipalForm(user.colleur,classes,request.POST or None,initial=initial)
		if form.is_valid():
			user.email=form.cleaned_data['email']
			if form.cleaned_data['motdepasse']:
				user.set_password(form.cleaned_data['motdepasse'])
			user.save()
			for classe in classes:
				for matiere in classe.matieres.all():
					prof = Prof.objects.filter(classe=classe,matiere=matiere)
					if prof and prof[0].colleur in form.cleaned_data["{}_groupe".format(classe.pk)]:
						prof.update(modifgroupe=True)
					else:
						prof.update(modifgroupe=False)
					if prof and prof[0].colleur in form.cleaned_data["{}_colloscope".format(classe.pk)]:
						prof.update(modifcolloscope=True)
					else:
						prof.update(modifcolloscope=False)
			return redirect('accueil')
	else:
		form=UserForm(request.POST or None,initial={'email':user.email})
		if form.is_valid():
			user.email=form.cleaned_data['email']
			if form.cleaned_data['motdepasse']:
				user.set_password(form.cleaned_data['motdepasse'])
			user.save()
			return redirect('accueil')
	return render(request,"accueil/profil.html",{'form':form})

@login_required(login_url='accueil')
def messages(request):
	"""Renvoie vers la vue des messages"""
	form = SelectMessageForm(request.user,True,request.POST or None)
	if form.is_valid():
		for destinataire in form.cleaned_data['message']:
			if not destinataire.message.hasAuteur and destinataire.message.messagerecu.all().count()<=1:
				destinataire.message.delete()
		form.cleaned_data['message'].delete()
		return redirect('messages')
	return render(request,"accueil/messages.html",{'form':form,'nonvide':form.fields['message'].queryset.exists()})

@login_required(login_url='accueil')
def messagesenvoyes(request):
	"""Renvoie vers la vue des messages envoyés"""
	form = SelectMessageForm(request.user,False,request.POST or None)
	if form.is_valid():
		form.cleaned_data['message'].update(hasAuteur=False)
		for message in form.cleaned_data['message']:
			if not message.messagerecu.all().count():
				message.delete()
		return redirect('messagesenvoyes')
	return render(request,"accueil/messagesenvoyes.html",{'form':form,'nonvide':form.fields['message'].queryset.exists()})

@login_required(login_url='accueil')
def message(request,id_message):
	"""Renvoie vers la vue du message dont l'id est id_message"""
	mesage = Destinataire.objects.filter(user=request.user,pk=id_message).select_related('message','user')
	if not mesage:
		raise Http404("Message non trouvé")
	if not mesage[0].lu:
		mesage[0].message.luPar=mesage[0].message.luPar + str(request.user)+"; "
		mesage[0].message.save()
		mesage.update(lu=True)
	repondre = False
	if mesage[0].message.auteur.username not in ['admin','Secrétariat']:
		if request.user.colleur or (request.user.eleve and not mesage[0].reponses):
			repondre = True
	return render(request,"accueil/message.html",{'mesage':mesage[0],'repondre':repondre})

@login_required(login_url='accueil')
def messageenvoye(request,id_message):
	"""Renvoie vers la vue du message envoyé dont l'id est id_message"""
	mesage = Message.objects.filter(auteur=request.user,pk=id_message)
	if not mesage:
		raise Http404
	listelus = "; ".join(list(Destinataire.objects.filter(message=mesage,lu=True)))
	return render(request,"accueil/messageenvoye.html",{'mesage':mesage[0]})

@login_required(login_url='accueil')
def ecrire(request):
	"""Renvoie vers la vue d'écriture d'un message """
	if request.user.eleve:
		return HttpResponseForbidden
	form=EcrireForm(request.user,request.POST or None)
	if form.is_valid():
		destinataires = set()
		for key,value in form.cleaned_data.items():
			cle = key.split('_')[0]
			if cle == 'classematiere' or cle == 'classeprof':
				destinataires |= {colleur.user for colleur in value}
			elif cle == 'classegroupe':
				destinataires |= {eleve.user for eleve in Eleve.objects.filter(groupe__in=value)}
			elif cle == 'classeeleve':
				destinataires |= {eleve.user for eleve in value}
		if not destinataires:
			messagees.error(request, "Il faut au moins un destinataire")
		else:
			message = Message(auteur=request.user,listedestinataires="; ".join(["{} {}".format(destinataire.first_name.title(),destinataire.last_name.upper()) for destinataire in destinataires]),titre=form.cleaned_data['titre'],corps=form.cleaned_data['corps'])
			message.save()
			for personne in destinataires:
				Destinataire(user=personne,message=message).save()
			messagees.error(request, "Message envoyé")
			return redirect('messages')
	return render(request,"accueil/ecrire.html",{'form':form})

@login_required(login_url='accueil')
def repondre(request,destinataire_id):
	"""Renvoie vers la vue de réponse au message dont le destinataire est destinataire_id"""
	destinataire = get_object_or_404(Destinataire,pk=destinataire_id)
	if destinataire.user  != request.user:
		raise Http404
	repondre = False
	if destinataire.message.auteur.username not in ['admin','Secrétariat']:
		if request.user.colleur or (request.user.eleve and not destinataire.reponses):
			repondre = True
	if not repondre:
		return HttpResponseForbidden("Vous n'avez pas le droit de répondre")
	form = ReponseForm(destinataire,request.POST or None)
	if form.is_valid():
		message = Message(auteur=request.user,listedestinataires=str(destinataire.message.auteur),titre=form.cleaned_data['titre'],corps=form.cleaned_data['corps'])
		message.save()
		Destinataire(user=destinataire.message.auteur,message=message).save()
		destinataire.reponses+=1
		destinataire.save()
		messagees.error(request, "Message envoyé")
		return redirect('messages')
	return render(request,"accueil/repondre.html",{'form':form,'destinataire':destinataire})
