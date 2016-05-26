#-*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from eleve.forms import EleveConnexionForm, MatiereForm
from colleur.forms import SemaineForm
from accueil.models import Classe, Note, Programme, Colle, Semaine, Groupe
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Min, Max, Avg, StdDev, Count
from datetime import date, timedelta
from pdf.pdf import Pdf
from ecolle.settings import MEDIA_URL, MATHJAX, IMAGEMAGICK
from django.http import Http404

def is_eleve(user):
	"""Renvoie True si l'utilisateur est un élève, False sinon"""
	if user.is_authenticated():
		return bool(user.eleve)
	return False

def connec(request, id_classe):
	"""Renvoie la vue de la page de connexion des élèves. Si l'élève est déjà connecté, redirige vers la page d'accueil des élèves"""
	classe=get_object_or_404(Classe,pk=id_classe)
	if is_eleve(request.user):
		return redirect('action_eleve')
	error = False
	form = EleveConnexionForm(classe,request.POST or None)
	if form.is_valid():
		username=form.cleaned_data['eleve'].user.username
		user = authenticate(username=username,password=form.cleaned_data['password'])
		if user:
			login(request,user)
			return redirect('action_eleve')
		else:
			error = True
	return render(request,'eleve/home.html',{'form':form, 'classe':classe, 'error':error})

@user_passes_test(is_eleve, login_url='accueil')
def action(request):
	"""Renvoie la vue de la page d'accueil des élèves"""
	return render(request,"eleve/action.html")

@user_passes_test(is_eleve, login_url='accueil')
def bilan(request):
	"""Renvoie la vue de la page de bilan"""
	eleve = request.user.eleve
	form=SemaineForm(request.POST or None)
	if form.is_valid():
		semin=form.cleaned_data['semin']
		semax=form.cleaned_data['semax']
	else:
		semin=False
	matieres = Note.objects.filter(eleve=eleve).exclude(note__gt=20)
	if semin:
		matieres=matieres.filter(semaine__lundi__range=(semin.lundi,semax.lundi))
	matieres=matieres.values_list('matiere__pk').order_by('matiere__nom').distinct()
	moyenne = Note.objects.filter(eleve=eleve,matiere__pk__in=matieres).exclude(note__gt=20)
	moyenne_classe = Note.objects.filter(matiere__pk__in=matieres,classe=eleve.classe,eleve__isnull=False).exclude(note__gt=20) 
	if semin:
		moyenne=moyenne.filter(semaine__lundi__range=[semin.lundi,semax.lundi])
		moyenne_classe = moyenne_classe.filter(semaine__lundi__range=[semin.lundi,semax.lundi])
	moyenne = list(moyenne.values('matiere__pk','matiere__nom','matiere__couleur').annotate(Avg('note'),Min('note'),Max('note'),Count('note'),StdDev('note')).order_by('matiere__nom'))
	moyenne_classe = moyenne_classe.values('matiere__pk').annotate(Avg('note')).order_by('matiere__nom')
	rangs=[]
	for i,matiere in enumerate(matieres):
		rang=Note.objects.exclude(note__gt=20).filter(classe=eleve.classe,eleve__isnull=False,matiere__pk=matiere[0])
		if semin:
			rang=rang.filter(semaine__lundi__range=[semin.lundi,semax.lundi])
		if moyenne[i]['note__avg']:
			rang=rang.values('eleve').annotate(Avg('note')).filter(note__avg__gt=moyenne[i]['note__avg']+0.0001).count()+1
		else:
			rang=""
		rangs.append(rang)
	return render(request,'eleve/bilan.html',{'form':form,'moyennes':zip(moyenne,moyenne_classe,rangs)})

@user_passes_test(is_eleve, login_url='accueil')
def note(request):
	"""Renvoie la vue de la page de consultation des notes"""
	form=MatiereForm(request.user.eleve.classe,request.POST or None)
	if form.is_valid():
		matiere=form.cleaned_data['matiere']
	else:
		matiere=None
	eleve = request.user.eleve
	return render(request,'eleve/note.html',{'form':form,'matiere':matiere,'notes':Note.objects.noteEleve(eleve,matiere),'latex':MATHJAX})

@user_passes_test(is_eleve, login_url='accueil')
def programme(request):
	"""Renvoie la vue de la page de consultation des programmes"""
	form=MatiereForm(request.user.eleve.classe,request.POST or None)
	matiere=planning=None
	if form.is_valid():
		matiere=form.cleaned_data['matiere']
	eleve = request.user.eleve
	programmes = Programme.objects.filter(classe=eleve.classe)
	if matiere:
		programmes=programmes.filter(matiere=matiere)
	programmes=programmes.values('matiere__couleur','matiere__nom','semaine__numero','titre','fichier','detail').order_by('-semaine__lundi','matiere__nom')
	return render(request,'eleve/programme.html',{'form':form,'matiere':matiere,'programmes':programmes,'media_url':MEDIA_URL,'latex':MATHJAX,'jpeg':IMAGEMAGICK})

@user_passes_test(is_eleve, login_url='accueil')
def colloscope(request):
	"""Renvoie la vue de la page de consultation du colloscope"""
	classe=request.user.eleve.classe
	if classe is None:
		raise Http404
	semaines=Semaine.objects.all()
	try:
		semin=semaines[0]
	except Exception:
		raise Http404
	try:
		semax=semaines[semaines.count()-1]
	except Exception:
		raise Http404
	form=SemaineForm(request.POST or None)
	if form.is_valid():
		semin=form.cleaned_data['semin']
		semax=form.cleaned_data['semax']
	listegroupes = dict()
	for groupe in Groupe.objects.filter(classe=classe):
		elevegroupe="; ".join([eleve['user__first_name'].title()+' '+eleve['user__last_name'].upper() for eleve in groupe.groupeeleve.values('user__first_name','user__last_name')])
		listegroupes[groupe.pk] = [groupe.nom,elevegroupe]
	jours,creneaux,colles,semaines = Colle.objects.classe2colloscope(classe,semin,semax)
	return render(request,'eleve/colloscope.html',
	{'semin':semin,'semax':semax,'form':form,'classe':classe,'jours':jours,'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'listegroupes':listegroupes,'dictColleurs':classe.dictColleurs(semin,semax)})

@user_passes_test(is_eleve, login_url='accueil')
def agenda(request):
	"""Renvoie la page de la vue de consultation de l'agenda"""
	jour=date.today()
	semaine=jour+timedelta(days=-jour.weekday())
	semainemin=semaine+timedelta(days=-21)
	eleve=request.user.eleve
	return render(request,"eleve/agenda.html",{'colles':Colle.objects.agendaEleve(eleve,semainemin),'media_url':MEDIA_URL,'jour':jour,'semaine':semaine,'latex':MATHJAX})

@user_passes_test(is_eleve, login_url='accueil')
def colloscopePdf(request,id_semin,id_semax):
	"""Renvoie le fichier PDF du colloscope de la classe de l'élève, entre les semaines d'id id_semin et id_semax"""
	classe=request.user.eleve.classe
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	if not classe:
		raise Http404
	return Pdf(classe,semin,semax)
