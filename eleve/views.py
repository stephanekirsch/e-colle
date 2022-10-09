#-*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from eleve.forms import EleveConnexionForm, MatiereForm, CopieForm
from colleur.forms import SemaineForm
from accueil.models import Note, Programme, Colle, Semaine, Groupe, Devoir, DevoirRendu, TD, Cours, Document, Config
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Max
from datetime import date, datetime
from pdf.pdf import Pdf
from ecolle.settings import MEDIA_URL, IMAGEMAGICK, MEDIA_ROOT
from django.http import Http404, HttpResponseForbidden
import os

def is_eleve(user):
	"""Renvoie True si l'utilisateur est un élève, False sinon"""
	if user.is_authenticated:
		return bool(user.eleve)
	return False

def connec(request):
	"""Renvoie la vue de la page de connexion des élèves. Si l'élève est déjà connecté, redirige vers la page d'accueil des élèves"""
	if is_eleve(request.user):
		return redirect('action_eleve')
	error = False
	form = EleveConnexionForm(request.POST or None)
	if form.is_valid():
		user = authenticate(username=form.cleaned_data['username'],password=form.cleaned_data['password'])
		if user and user.is_active and user.eleve:
			login(request,user)
			return redirect('action_eleve')
		else:
			error = True
	return render(request,'eleve/home.html',{'form':form, 'error':error})

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
		semin=semax=False
	return render(request,'eleve/bilan.html',{'form':form,'moyennes':Note.objects.bilanEleve(eleve,semin,semax)})

@user_passes_test(is_eleve, login_url='accueil')
def note(request):
	"""Renvoie la vue de la page de consultation des notes"""
	form=MatiereForm(request.user.eleve.classe,request.POST or None)
	if form.is_valid():
		matiere=form.cleaned_data['matiere']
	else:
		matiere=None
	eleve = request.user.eleve
	return render(request,'eleve/note.html',{'form':form,'matiere':matiere,'notes':Note.objects.noteEleve(eleve,matiere)})

@user_passes_test(is_eleve, login_url='accueil')
def programme(request):
	"""Renvoie la vue de la page de consultation des programmes"""
	form=MatiereForm(request.user.eleve.classe,request.POST or None)
	matiere=None
	if form.is_valid():
		matiere=form.cleaned_data['matiere']
	eleve = request.user.eleve
	programmes = Programme.objects.filter(classe=eleve.classe)
	if matiere:
		programmes=programmes.filter(matiere=matiere)
	programmes = programmes.annotate(semainemax=Max('semaine')).select_related('matiere').order_by('-semainemax','matiere__nom')
	#programmes=programmes.values('matiere__couleur','matiere__nom','semaine__numero','titre','fichier','detail').order_by('-semaine__lundi','matiere__nom')
	return render(request,'eleve/programme.html',{'form':form,'matiere':matiere,'programmes':programmes,'media_url':MEDIA_URL,'jpeg':IMAGEMAGICK})

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
	semestre2 = Config.objects.get_config().semestre2
	semestres = classe.semestres and semestre2 <= semax.numero
	dictGroupes2 = classe.dictGroupes(True, 2) if semestres else False
	if not semestres:
		semestre2 = 1000
	return render(request,'eleve/colloscope.html',
	{'semin':semin,'semax':semax,'semestre2': semestre2, 'dictgroupes':classe.dictGroupes(), 'dictgroupes2': dictGroupes2, 'form':form,'classe':classe,'jours':jours,'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'listegroupes':listegroupes,'dictColleurs':classe.dictColleurs(semin,semax)})

@user_passes_test(is_eleve, login_url='accueil')
def agenda(request):
	"""Renvoie la page de la vue de consultation de l'agenda"""
	jour=date.today()
	eleve=request.user.eleve
	return render(request,"eleve/agenda.html",{'colles':Colle.objects.agendaEleve(eleve),'media_url':MEDIA_URL,'jour':jour})

@user_passes_test(is_eleve, login_url='accueil')
def colloscopePdf(request,id_semin,id_semax):
	"""Renvoie le fichier PDF du colloscope de la classe de l'élève, entre les semaines d'id id_semin et id_semax"""
	classe=request.user.eleve.classe
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	if not classe:
		raise Http404
	return Pdf(classe,semin,semax)

@user_passes_test(is_eleve, login_url='accueil')
def devoirs(request):
	"""renvoie la page des devoirs de la classe de l'élève"""
	classe=request.user.eleve.classe
	form=MatiereForm(classe,request.POST or None)
	matiere=None
	if form.is_valid():
		matiere=form.cleaned_data['matiere']
	devoirs = Devoir.objects.devoirsEleves(request.user.eleve, matiere)
	hui = date.today()
	heure = datetime.time(datetime.today())
	return render(request,"eleve/devoirs.html", {'form': form, 'classe':classe, 'devoirs':devoirs, 'matiere': matiere, 'hui': hui, "heure": heure})

@user_passes_test(is_eleve, login_url='accueil')
def depotCopie(request, id_devoir):
	"""envoie vers un formulaire pour deposer sa copie pour le devoir dont l'id est id_devoir"""
	devoir = get_object_or_404(Devoir, pk=id_devoir)
	a_rendre = datetime.combine(devoir.a_rendre_jour, devoir.a_rendre_heure)
	rendu = DevoirRendu.objects.filter(eleve = request.user.eleve, devoir = devoir)
	oldfile = False
	if rendu.exists():
		# on vérifie que la date pour rendre le devoir n'est pas déjà passée:
		hui = date.today()
		heure = datetime.time(datetime.today())
		if not(devoir.a_rendre_jour > hui or devoir.a_rendre_jour == hui and devoir.a_rendre_heure > heure):
			return HttpResponseForbidden("Vous avez déjà rendu votre devoir et la date limite est passée")
		copie = rendu.first()
		oldfile=os.path.join(MEDIA_ROOT,copie.fichier.name) 
	else:
		copie = DevoirRendu(eleve = request.user.eleve, devoir = devoir)
	form=CopieForm(request.POST or None,request.FILES or None, instance=copie)
	if form.is_valid():
		if (request.FILES or form.cleaned_data['fichier'] is False) and oldfile:
			if os.path.isfile(oldfile):
				os.remove(oldfile)
		form.save()
		return redirect("eleve_devoirs")
	return render(request, "eleve/renducopie.html", {'form': form, 'devoir': devoir})

@user_passes_test(is_eleve, login_url='accueil')
def tds(request):
	"""renvoie la page des tds de la classe de l'élève"""
	classe=request.user.eleve.classe
	form=MatiereForm(classe,request.POST or None)
	matiere=None
	if form.is_valid():
		matiere=form.cleaned_data['matiere']
	tds = TD.objects.filter(classe = classe)
	if matiere is not None:
		tds = tds.filter(matiere = matiere)
	tds = tds.order_by('-date_affichage')
	return render(request,"eleve/tds.html", {'form': form, 'classe':classe, 'tds':tds, 'matiere': matiere})

@user_passes_test(is_eleve, login_url='accueil')
def cours(request):
	"""renvoie la page des cours de la classe de l'élève"""
	classe=request.user.eleve.classe
	form=MatiereForm(classe,request.POST or None)
	matiere=None
	if form.is_valid():
		matiere=form.cleaned_data['matiere']
	cours = Cours.objects.filter(classe = classe)
	if matiere is not None:
		cours = cours.filter(matiere = matiere)
	cours = cours.order_by('-date_affichage')
	return render(request,"eleve/cours.html", {'form': form, 'classe':classe, 'cours':cours, 'matiere': matiere})

@user_passes_test(is_eleve, login_url='accueil')
def autre(request):
	"""renvoie la page des documents de la classe de l'élève"""
	classe=request.user.eleve.classe
	form=MatiereForm(classe,request.POST or None)
	matiere=None
	if form.is_valid():
		matiere=form.cleaned_data['matiere']
	docs = Document.objects.filter(classe = classe)
	if matiere is not None:
		docs = docs.filter(matiere = matiere)
	docs = docs.order_by('-date_affichage')
	return render(request,"eleve/autre.html", {'form': form, 'classe':classe, 'docs':docs, 'matiere': matiere})