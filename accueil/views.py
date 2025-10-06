#-*- coding: utf-8 -*-
from django.http import HttpResponseForbidden, Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from accueil.models import Classe, Matiere, Colleur, Message, Destinataire, Eleve, Config, Prof
from accueil.forms import UserForm, UserProfprincipalForm, UserProfForm, SelectMessageForm, EcrireForm, ReponseForm
from django.contrib import messages as messagees
from ecolle.settings import IP_FILTRE_ADMIN, IP_FILTRE_ADRESSES
import re
import qrcode as qr
from django.db.models import Q
from io import BytesIO

def home(request):
	"""Renvoie la vue d'accueil ou, si l'utilisateur est déjà identifié, redirige vers la section adéquate"""
	user=request.user
	if user.is_authenticated:
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
	if not user.is_authenticated:
		return HttpResponseForbidden("Vous devez être connecté pour accéder à cette page")
	profprincipal = bool(user.colleur and Classe.objects.filter(profprincipal=user.colleur))
	if profprincipal:
		classes = Classe.objects.filter(profprincipal=user.colleur)
		initial = {'email':user.email}
		for classe in classes:
			initial["{}_groupe".format(classe.pk)] = Colleur.objects.filter(colleurprof__classe=classe,colleurprof__modifgroupe=True)
			initial["{}_colloscope".format(classe.pk)] = Colleur.objects.filter(colleurprof__classe=classe,colleurprof__modifcolloscope=True)
		form = UserProfprincipalForm(user.colleur,classes,request.POST or None,instance = user, initial = initial)
		if form.is_valid():
			form.save()
			return redirect('accueil')
	elif Prof.objects.filter(colleur=user.colleur).exists():
		form = UserProfForm(user.colleur,request.POST or None,instance = user,initial = {'email':user.email})
		if form.is_valid():
			form.save()
			return redirect('accueil')
	else:
		form=UserForm(request.POST or None,instance = user)
		if form.is_valid():
			form.save()
			return redirect('accueil')
	return render(request,"accueil/profil.html",{'form':form})

@login_required(login_url='accueil')
def messages(request):
	"""Renvoie vers la vue des messages"""
	form = SelectMessageForm(request.user,request.POST or None)
	if form.is_valid():
		form.save()
		return redirect('messages')
	peut_composer = True
	if request.user.eleve:
		peut_composer = Config.objects.get_config().message_eleves
	return render(request,"accueil/messages.html",{'form':form,'peut_composer':peut_composer,'nonvide':form.fields['message'].queryset.exists()})

@login_required(login_url='accueil')
def message(request,id_message):
	"""Renvoie vers la vue du message dont l'id est id_message"""
	message = Message.objects.filter(pk=id_message).filter(Q(auteur = request.user, hasAuteur = True) | Q(messagerecu__user = request.user))
	if not message.exists():
		raise Http404("Message non trouvé")
	message = message.first()
	repondre = True
	envoye = False
	if message.auteur == request.user: # si c'est un message envoyé
		envoye = True
		if request.user.eleve: # on peut répondre, sauf si on est élève et que les élèves n'ont le droit que de répondre
			repondre = Config.objects.get_config().message_eleves
	else: # si c'est un message reçu
		destinataire = Destinataire.objects.get(message = message,user=request.user)
		if not destinataire.lu: # on met à jour  le destinataire
			message.luPar += str(request.user) + "; "
			message.save()
			destinataire.lu=True
			destinataire.save()
		if request.user.eleve and destinataire.reponses and not Config.objects.get_config().message_eleves:
			repondre = False
		if message.auteur.username in ['admin','Secrétariat']:
			repondre = False
	return render(request,"accueil/message.html",{'message':message,'repondre':repondre,'envoye':envoye})

@login_required(login_url='accueil')
def ecrire(request):
	"""Renvoie vers la vue d'écriture d'un message """
	if request.user.eleve and not Config.objects.get_config().message_eleves:
		return HttpResponseForbidden("Vous n'avez pas le droit d'écrire une message")
	message = Message(auteur=request.user)
	form=EcrireForm(request.user,request.POST or None,request.FILES or None, instance = message)
	if form.is_valid():
		form.save()
		messagees.error(request, "Message envoyé")
		return redirect('messages')
	return render(request,"accueil/ecrire.html",{'form':form})

@login_required(login_url='accueil')
def repondre(request,message_id):
	"""Renvoie vers la vue de réponse au message dont l'id est message_id"""
	message = get_object_or_404(Message, pk=message_id)
	if message.auteur == request.user: # on ne peut que "répondre à tous" à un message qu'on a envoyé
		raise Http404
	destinataire = get_object_or_404(Destinataire,message=message,user=request.user)
	if request.user.eleve and destinataire.reponses and not Config.objects.get_config().message_eleves or message.auteur.username in ['admin','Secrétariat']:
		return HttpResponseForbidden("Vous n'avez pas le droit de répondre")
	reponse = Message(auteur=request.user, listedestinataires=str(message.auteur), titre = "Re: "+ message.titre, corps = (">"+message.corps.strip().replace("\n","\n>")+"\n"))
	form = ReponseForm(message, False, request.user, request.POST or None, request.FILES or None, initial = {'destinataire': reponse.listedestinataires }, instance = reponse)
	if form.is_valid():
		form.save()
		messagees.error(request, "Message envoyé")
		destinataire.reponses +=1
		destinataire.save()
		return redirect('messages')
	return render(request,"accueil/repondre.html",{'form':form,'message':message})

@login_required(login_url='accueil')
def repondreatous(request,message_id):
	"""Renvoie vers la vue de réponse au message dont l'id est message_id"""
	message = Message.objects.filter(pk=message_id).filter(Q(auteur = request.user, hasAuteur = True) | Q(messagerecu__user = request.user))
	if not message.exists():
		raise Http404("Message non trouvé")
	message = message.first()
	destinataires  = list(message.messagerecu.all())
	if message.auteur == request.user: # si on répond à un message qu'on a envoyé
		if request.user.eleve and not Config.objects.get_config().message_eleves:
			return HttpResponseForbidden("Vous n'avez pas le droit de répondre")
	else:
		desti = get_object_or_404(Destinataire,message=message,user=request.user)
		if request.user.eleve and desti.reponses and not Config.objects.get_config().message_eleves:
			return HttpResponseForbidden("Vous n'avez pas le droit de répondre")
		destinataires.append(Destinataire(user=message.auteur,message=None))
	listedestinataires = "; ".join([str(desti.user) for desti in destinataires])
	reponse = Message(auteur=request.user , listedestinataires=listedestinataires, titre = "Re: "+ message.titre, corps = (">"+message.corps.strip().replace("\n","\n>")+"\n"))
	form = ReponseForm(message, destinataires, request.user, request.POST or None, request.FILES or None, initial = {"destinataire": listedestinataires}, instance = reponse)
	if form.is_valid():
		form.save()
		messagees.error(request, "Message envoyé")
		if message.auteur != request.user:
			desti.reponses +=1
			desti.save()
		return redirect('messages')
	return render(request,"accueil/repondre.html",{'form':form,'message':message})


@login_required(login_url='accueil')
def qrcode(request):
	return render(request,"accueil/qrcode.html")

@login_required(login_url='accueil')
def qrcodepng(request):
	url = request.build_absolute_uri('/')
	img = qr.make(url)
	buffer = BytesIO()
	img.save(buffer,format="PNG")
	response = HttpResponse(content_type='image/png')
	response.write(buffer.getvalue())
	buffer.close()
	return response