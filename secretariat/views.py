#-*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from administrateur.forms import AdminConnexionForm, SelectColleurForm, MatiereClasseSelectForm
from colleur.forms import SemaineForm, ECTSForm, CreneauForm, ColleForm, GroupeForm
from secretariat.forms import MoisForm, RamassageForm, MatiereClasseSemaineSelectForm, SelectClasseSemaineForm, DispoForm, DispoFormSet, FrequenceForm, ColleurgroupeForm, ColleurgroupeFormSet, PlanificationForm
from django.forms.formsets import formset_factory
from accueil.models import Note, Semaine, Matiere, Etablissement, Colleur, Ramassage, Classe, Eleve, Groupe, Creneau, Colle, mois, NoteECTS, JourFerie, Frequence, Colleurgroupe
from mixte.mixte import mixteajaxcompat, mixteajaxcolloscope, mixteajaxcolloscopeeleve, mixteajaxmajcolleur, mixteajaxcolloscopeeffacer, mixteajaxcolloscopemulticonfirm
from django.db.models import Count, F
from datetime import date, timedelta
from django.http import Http404, HttpResponse
from django.db.models import Avg
from pdf.pdf import Pdf, easyPdf, creditsects, attestationects
from reportlab.platypus import Table, TableStyle
from unidecode import unidecode
from lxml import etree
import csv
import json
from planification.planification import planif
conf=__import__('ecolle.config')

def is_secret(user):
	"""Renvoie True si l'utilisateur est le secrétariat, False sinon"""
	return user.is_authenticated() and user.username=="Secrétariat"

def is_secret_ects(user):
	"""Renvoie True si l'utilisateur est le secrétariat et ECTS activé, False sinon"""
	return is_secret(user) and conf.config.ECTS

def connec(request):
	"""Renvoie la vue de la page de connexion du secrétariat. Si le secrétariat est déjà connecté, redirige vers la page d'accueil du secrétariat"""
	if is_secret(request.user):
		return redirect('action_secret')
	error = False
	form = AdminConnexionForm(request.POST or None, initial={'username':"Secrétariat"})
	if form.is_valid():
		password = form.cleaned_data['password']
		user = authenticate(username="Secrétariat",password=password)
		if user:
			login(request,user)
			return redirect('action_secret')
		else:
			error = True
	form.fields['username'].widget.attrs['readonly'] = True
	return render(request,'secretariat/home.html',{'form':form,'error':error})

@user_passes_test(is_secret, login_url='login_secret')
def action(request):
	"""Renvoie la vue de la page d'accueil du secrétariat"""
	return render(request,"secretariat/action.html",{'classes':Classe.objects.all()})

@user_passes_test(is_secret, login_url='login_secret')
def resultats(request):
	"""Renvoie la vue de la page de consultation des résultats des classes"""
	form = MatiereClasseSemaineSelectForm(request.POST or None)
	if request.method=="POST":
		if form.is_valid():
			classe = form.cleaned_data['classe']
			matiere = form.cleaned_data['matiere']
			semin = form.cleaned_data['semin']
			semax = form.cleaned_data['semax']
			request.session['classe'] = classe.pk
			request.session['matiere'] = matiere.pk
			request.session['semin'] = semin.pk
			request.session['semax'] = semax.pk
			return redirect('resultats_secret')
		classe=matiere=semin=semax=semaines=generateur=None
	else:	
		try:
			classe = Classe.objects.get(pk=request.session['classe'])
			matiere = Matiere.objects.get(pk=request.session['matiere'])
			semin = Semaine.objects.get(pk=request.session['semin'])
			semax = Semaine.objects.get(pk=request.session['semax'])
		except Exception:
			classe=matiere=semin=semax=semaines=generateur=None
			form = MatiereClasseSemaineSelectForm(request.POST or None)
		else:
			generateur = Note.objects.classe2resultat(matiere,classe,semin,semax)
			semaines = next(generateur)
			form = MatiereClasseSemaineSelectForm(initial = {'classe':classe,'matiere':matiere,'semin':semin,'semax':semax})		
	return render(request,"secretariat/resultats.html",{'form':form,'classe':classe,'matiere':matiere,'semaines':semaines,'notes':generateur, 'semin':semin,'semax':semax,'classes':Classe.objects.all()})

@user_passes_test(is_secret, login_url='login_secret')
def resultatcsv(request,id_classe,id_matiere,id_semin,id_semax):
	"""Renvoie le fichier CSV des résultats de la classe dont l'id est id_classe, dans la matière dont l'id est id_matiere
	entre les semaines dont l'id est id_semin et id_semax"""
	classe=get_object_or_404(Classe,pk=id_classe)
	matiere = get_object_or_404(Matiere,pk=id_matiere)
	semin = get_object_or_404(Semaine,pk=id_semin)
	semax = get_object_or_404(Semaine,pk=id_semax)
	generateur = Note.objects.classe2resultat(matiere,classe,semin,semax)
	semaines = next(generateur)
	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename="resultats_{}_{}.csv"'.format(classe.nom,matiere.nom)
	writer = csv.writer(response)
	writer.writerow(['Élève','rang','moyenne']+['S{}'.format(semaine.numero) for semaine in semaines])
	notation = {i:str(i) for i in range(21)}
	notation[21]="n.n."
	notation[22]="abs"
	for note in generateur:
		writer.writerow([note['eleve'],note['rang'],note['moyenne']]+["|".join([notation[note['note']] for note in value]) for value in note['semaine']])
	return response

@user_passes_test(is_secret, login_url='login_secret')
def colloscope(request,id_classe):
	"""Renvoie la vue de la page du colloscope de la classe dont l'id est id_classe"""
	classe=get_object_or_404(Classe,pk=id_classe)
	semaines=Semaine.objects.all()
	try:
		semin=semaines[0]
	except Exception:
		raise Http404
	try:
		semax=semaines[semaines.count()-1]
	except Exception:
		raise Http404
	return colloscope2(request,id_classe,semin.pk,semax.pk)

@user_passes_test(is_secret, login_url='login_secret')
def colloscope2(request,id_classe,id_semin,id_semax):
	"""Renvoie la vue de la page du colloscope de la classe dont l'id est id_classe entre les semaines dont l'id est id_semin et id_semax"""
	classe=get_object_or_404(Classe,pk=id_classe)
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	form=SemaineForm(request.POST or None,initial={'semin':semin,'semax':semax})
	if form.is_valid():
		return redirect('colloscope2_secret',id_classe,form.cleaned_data['semin'].pk,form.cleaned_data['semax'].pk)
	jours,creneaux,colles,semaines=Colle.objects.classe2colloscope(classe,semin,semax)
	return render(request,'mixte/colloscope.html',
	{'semin':semin,'semax':semax,'form':form,'classe':classe,'jours':jours,'dictgroupes':classe.dictGroupes(),'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'classes':Classe.objects.all(),'dictColleurs':classe.dictColleurs(semin,semax),'isprof':conf.config.MODIF_SECRETARIAT_COLLOSCOPE})

@user_passes_test(is_secret, login_url='login_secret')
def colloscopePdf(request,id_classe,id_semin,id_semax):
	"""Renvoie le fichier PDF du colloscope de la classe dont l'id est id_classe, entre les semaines d'id id_semin et id_semax"""
	classe=get_object_or_404(Classe,pk=id_classe)
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	return Pdf(classe,semin,semax)

@user_passes_test(is_secret, login_url='accueil')
def colloscopeModif(request,id_classe,id_semin,id_semax,creneaumodif=None):
	"""Renvoie la vue de la page de modification du colloscope de la classe dont l'id est id_classe,
	dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	classe=get_object_or_404(Classe,pk=id_classe)
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	form1=SemaineForm(request.POST or None,initial={'semin':semin,'semax':semax})
	if form1.is_valid():
		return redirect('colloscopemodif_secret',id_classe,form1.cleaned_data['semin'].pk,form1.cleaned_data['semax'].pk)
	form2=ColleForm(classe,None)
	jours,creneaux,colles,semaines = Colle.objects.classe2colloscope(classe,semin,semax,True)
	creneau=creneaumodif if creneaumodif else Creneau(classe=classe)
	form=CreneauForm(request.POST or None,instance=creneau)
	if form.is_valid():
		if creneaumodif:
			form.save()
		else:
			if Creneau.objects.filter(classe=classe,jour=form.cleaned_data['jour'],heure=form.cleaned_data['heure']).exists():
				messages.error(request,"Il y a déjà un créneau ce jour à cette heure, utiliser la fonction dupliquer")
			else:
				form.save()
		return redirect('colloscopemodif_secret',classe.pk,semin.pk,semax.pk)
	matieres = list(classe.matieres.filter(colleur__classes=classe).values_list('pk','nom','couleur','temps').annotate(nb=Count("colleur")))
	colleurs = list(Classe.objects.filter(pk=classe.pk,matieres__colleur__classes=classe).values_list('matieres__colleur__pk','matieres__colleur__user__username','matieres__colleur__user__first_name','matieres__colleur__user__last_name').order_by("matieres__nom","matieres__colleur__user__last_name","matieres__colleur__user__first_name"))
	groupes = Groupe.objects.filter(classe=classe)
	matieresgroupes = [[groupe for groupe in groupes if groupe.haslangue(matiere)] for matiere in classe.matieres.filter(colleur__classes=classe)]
	listeColleurs = []
	for x in matieres:
		listeColleurs.append(colleurs[:x[4]])
		del colleurs[:x[4]]
	largeur=str(650+42*creneaux.count())+'px'
	hauteur=str(27*(len(matieres)+classe.classeeleve.count()+Colleur.objects.filter(classes=classe).count()))+'px'
	return render(request,'mixte/colloscopeModif.html',
	{'semin':semin,'semax':semax,'form1':form1,'form':form,'form2':form2,'largeur':largeur,'hauteur':hauteur,'groupes':groupes,'matieres':zip(matieres,listeColleurs,matieresgroupes),'creneau':creneaumodif\
	,'classe':classe,'jours':jours,'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'dictColleurs':classe.dictColleurs(semin,semax),'dictGroupes':json.dumps(classe.dictGroupes(False)),'dictEleves':json.dumps(classe.dictElevespk())})

@user_passes_test(is_secret, login_url='accueil')
def creneauSuppr(request,id_creneau,id_semin,id_semax):
	"""Essaie de supprimer le créneau dont l'id est id_creneau puis redirige vers la page de modification du colloscope
	dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	try:
		creneau.delete()
	except Exception:
		messages.error(request,"Vous ne pouvez pas effacer un créneau qui contient des colles")
	return redirect('colloscopemodif_secret',creneau.classe.pk,id_semin,id_semax)

@user_passes_test(is_secret, login_url='accueil')
def creneauModif(request,id_creneau,id_semin,id_semax):
	"""Renvoie la vue de la page de modification du creneau dont l'id est id_creneau"""
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	return colloscopeModif(request,creneau.classe.pk,id_semin,id_semax,creneaumodif=creneau)

@user_passes_test(is_secret, login_url='accueil')
def creneauDupli(request,id_creneau,id_semin,id_semax):
	"""Renvoie la vue de la page de duplication du creneau dont l'id est id_creneau"""
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	creneau.pk=None
	creneau.salle=None
	creneau.save()
	return redirect('colloscopemodif_secret',creneau.classe.pk,id_semin,id_semax)

@user_passes_test(is_secret, login_url='accueil')
def ajaxcompat(request,id_classe):
	"""Renvoie ue chaîne de caractères récapitulant les incompatibilités du colloscope de la classe dont l'id est id_classe"""
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	classe=get_object_or_404(Classe,pk=id_classe)
	return mixteajaxcompat(classe)

@user_passes_test(is_secret, login_url='accueil')
def ajaxmajcolleur(request, id_matiere, id_classe):
	"""Renvoie la liste des colleurs de la classe dont l'id est id_classe et de la matière dont l'id est id_matiere, au format json"""
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	classe=get_object_or_404(Classe,pk=id_classe)
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	return mixteajaxmajcolleur(matiere,classe)
	

@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscope(request, id_matiere, id_colleur, id_groupe, id_semaine, id_creneau):
	"""Ajoute la colle propre au quintuplet (matière,colleur,groupe,semaine,créneau) et renvoie le username du colleur
	en effaçant au préalable toute colle déjà existante sur ce couple créneau/semaine"""
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	colleur=get_object_or_404(Colleur,pk=id_colleur)
	groupe=get_object_or_404(Groupe,pk=id_groupe)
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	return mixteajaxcolloscope(matiere,colleur,groupe,semaine,creneau)
	

@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscopeeleve(request, id_matiere, id_colleur, id_eleve, id_semaine, id_creneau, login):
	"""Ajoute la colle propre au quintuplet (matière,colleur,eleve,semaine,créneau) et renvoie le username du colleur
	en effaçant au préalable toute colle déjà existante sur ce couple créneau/semaine"""
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	colleur=get_object_or_404(Colleur,pk=id_colleur)
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	return mixteajaxcolloscopeeleve(matiere,colleur, id_eleve,semaine,creneau,login)

@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscopeeffacer(request,id_semaine, id_creneau):
	"""Efface la colle sur le créneau dont l'id est id_creneau et la semaine sont l'id est id_semaine
	puis renvoie la chaine de caractères "efface" """
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	return mixteajaxcolloscopeeffacer(semaine,creneau)

@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscopemulti(request, id_matiere, id_colleur, id_groupe, id_eleve, id_semaine, id_creneau, duree, frequence, permutation):
	"""Compte le nombre de colles présente sur les couples créneau/semaine sur le créneau dont l'id est id_creneau
	et les semaines dont le numéro est compris entre celui de la semaine d'id id_semaine et ce dernier + duree
	et dont le numéro est congru à celui de la semaine d'id id_semaine modulo frequence
	S'il n'y en a aucune, ajoute les colles sur les couples créneau/semaine précédents, avec le colleur dont l'id est id_colleur
	le groupe démarre au groupe dont l'id est id_groupe puis va de permutation en permutation, et la matière dont l'id est id_matière"""
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	colleur=get_object_or_404(Colleur,pk=id_colleur)
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	frequence = int(frequence)
	modulo = int(semaine.numero)%frequence
	ecrase = Colle.objects.filter(creneau = creneau,semaine__numero__range=(semaine.numero,semaine.numero+int(duree)-1)).annotate(semaine_mod = F('semaine__numero') % frequence).filter(semaine_mod=modulo).count()
	nbferies = JourFerie.objects.recupFerie(creneau.jour,semaine,duree,frequence,modulo)
	if not(ecrase and nbferies[0]):
		return HttpResponse("{}_{}".format(ecrase,nbferies[0]))
	else:
		return ajaxcolloscopemulticonfirm(request, id_matiere, id_colleur, id_groupe, id_eleve, id_semaine, id_creneau, duree, frequence, permutation)

@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscopemulticonfirm(request, id_matiere, id_colleur, id_groupe, id_eleve, id_semaine, id_creneau, duree, frequence, permutation):
	"""ajoute les colles sur les couples créneau/semaine sur le créneau dont l'id est id_creneau
	et les semaines dont le numéro est compris entre celui de la semaine d'id id_semaine et ce dernier + duree
	et dont le numéro est congru à celui de la semaine d'id id_semaine modulo frequence, avec le colleur dont l'id est id_colleur
	le groupe démarre au groupe dont l'id est id_groupe puis va de permutation en permutation, et la matière dont l'id est id_matière"""
	if not conf.config.MODIF_SECRETARIAT_COLLOSCOPE:
		return HttpResponseForbidden("Accès non autorisé")
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	colleur=get_object_or_404(Colleur,pk=id_colleur)
	groupe=None if matiere.temps!=20 else get_object_or_404(Groupe,pk=id_groupe)
	eleve=None if matiere.temps!=30 else get_object_or_404(Eleve,pk=id_eleve)
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	return mixteajaxcolloscopemulticonfirm(matiere,colleur,groupe,eleve,semaine,creneau,duree, frequence, permutation)

@user_passes_test(is_secret, login_url='login_secret')
def planification(request):
	return render(request,"secretariat/planification.html")

@user_passes_test(is_secret, login_url='login_secret')
def dispo(request):
	"""Renvoie la vue de la page de gestion des disponibilités des colleurs"""
	if "selectmatiere" in request.POST:
		form = MatiereClasseSelectForm(request.POST)
	else:
		try:
			matiere = Matiere.objects.get(pk=request.session['matiere'])
		except Exception:
			matiere = None
		try:
			classe = Classe.objects.get(pk=request.session['classe'])
		except Exception:
			classe = None
		form = MatiereClasseSelectForm(initial = {'matiere':matiere,'classe':classe})
	if form.is_valid():
		matiere = form.cleaned_data['matiere']
		request.session['matiere'] = None if not matiere else matiere.pk
		classe = form.cleaned_data['classe']
		request.session['classe'] = None if not classe else classe.pk
	else:
		try:
			matiere = Matiere.objects.get(pk=request.session['matiere'])
		except Exception:
			matiere = None
		try:
			classe = Classe.objects.get(pk=request.session['classe'])
		except Exception:
			classe = None
	form2 = SelectColleurForm(matiere,classe,request.POST if "modifier" in request.POST else None)
	if form2.is_valid():
		return redirect('dispo_modif', "-".join([str(colleur.pk) for colleur in form2.cleaned_data['colleur']]))
	colleurs = Colleur.objects.select_related('user').prefetch_related('dispos').order_by('user__last_name','user__first_name')
	return render(request,"secretariat/dispo.html",{'form':form,'form2':form2})

@user_passes_test(is_secret, login_url='login_secret')
def dispomodif(request,chaine_colleurs):
	"""Renvoie la vue de la page de modification des disponibilités des colleurs dont l'id fait partie de chaine_colleurs"""
	listeColleurs = Colleur.objects.filter(pk__in=[int(i) for i in chaine_colleurs.split("-")]).order_by('user__last_name','user__first_name').select_related('user')
	Dispoformset = formset_factory(DispoForm,extra=0,max_num=listeColleurs.count(),formset=DispoFormSet)
	if request.method == 'POST':
		formset = Dispoformset(listeColleurs,request.POST)
		if formset.is_valid():
			formset.save()
			return redirect('dispo')
	else:
		formset = Dispoformset(listeColleurs,initial=[{'dispo':[ 96*dispo.jour+dispo.heure for dispo in colleur.dispos.all()]} for colleur in listeColleurs])	
	return render(request,'secretariat/dispomodif.html',{'formset':formset})

@user_passes_test(is_secret, login_url='login_secret')
def frequence(request):
	"""Renvoie la vue de la page de gestion des fréquences des colles par matière/classe"""
	frequences = []
	for classe in Classe.objects.all():
		frequences.append((classe,[(matiere,Frequence.objects.filter(classe=classe,matiere=matiere).first()) for matiere in classe.matieres.all()]))
	return render(request,"secretariat/frequence.html",{'listefrequences':frequences})

@user_passes_test(is_secret, login_url='login_secret')
def frequencemodif(request,id_classe):
	classe=get_object_or_404(Classe,pk=id_classe)
	initial = dict()
	for matiere in Matiere.objects.filter(matieresclasse=classe,temps=20).order_by('nom','precision'):
		frequence = Frequence.objects.filter(matiere=matiere,classe=classe).first()
		if frequence is not None:
			initial[str(matiere.pk)] = frequence.frequence
			initial[str(matiere.pk)+"_"] = frequence.repartition
	form=FrequenceForm(classe,request.POST or None,initial=initial)
	if form.is_valid():
		form.save()
		return redirect('frequence')
	return render(request,'secretariat/frequencemodif.html',{'form':form,'classe':classe})

@user_passes_test(is_secret, login_url='login_secret')
def colles(request):
	classes = Colleurgroupe.objects.liste()
	return render(request,"secretariat/colles.html",{'classes':classes})

@user_passes_test(is_secret, login_url='login_secret')
def collesmodif(request,id_classe):
	classe = get_object_or_404(Classe,pk=id_classe)
	Colleurgroupeformset = formset_factory(ColleurgroupeForm,extra=0,max_num=classe.matieres.filter(temps=20).count(),formset=ColleurgroupeFormSet)
	if request.method == 'POST':
		formset = Colleurgroupeformset(classe,request.POST)
		if formset.is_valid():
			formset.save()
			return redirect('colles')
	else:
		initial=[]
		for matiere in classe.matieres.filter(temps=20):
			groupes = dict()
			for colleur in Colleur.objects.filter(classes=classe,matieres=matiere):
				groupe = Colleurgroupe.objects.filter(classe=classe,matiere=matiere,colleur=colleur).first()
				if groupe:
					groupes[str(colleur.pk)] = groupe.nbgroupes
			initial.append(groupes)
		formset = Colleurgroupeformset(classe,initial=initial)	
	return render(request,"secretariat/collesmodif.html",{'formset':formset,'classe':classe})

@user_passes_test(is_secret, login_url='login_secret')
def edt(request):
	form = PlanificationForm(request.POST or None)
	if form.is_valid():
		succes = planif(form.cleaned_data['semin'],form.cleaned_data['semax'],form.cleaned_data['classes'])
	return render(request,'secretariat/edt.html',{'form':form})

@user_passes_test(is_secret, login_url='login_secret')
def recapitulatif(request):
	"""Renvoie la vue de la page de récapitulatif des heures de colle"""
	moisMin,moisMax=mois()
	form = MoisForm(moisMin,moisMax,request.POST or None)
	if form.is_valid():
		moisMin=form.cleaned_data['moisMin']
		moisMax=form.cleaned_data['moisMax']
	listeDecompte,effectifs=Ramassage.objects.decompte(moisMin,moisMax)
	return render(request,"secretariat/recapitulatif.html",{'form':form,'decompte':listeDecompte,'effectifs':effectifs})

@user_passes_test(is_secret, login_url='login_secret')
def ramassage(request):
	"""Renvoie la vue de la page de ramassage des heures de colle"""
	form = RamassageForm(request.POST or None)
	if form.is_valid():
		form.save()
		return redirect('ramassage')
	ramassages=Ramassage.objects.all()
	return render(request,"secretariat/ramassage.html",{'form':form,'ramassages':ramassages})

@user_passes_test(is_secret, login_url='login_secret')
def ramassageSuppr(request,id_ramassage):
	"""Essaie d'effacer le ramassage dont l'id est id_ramassage, puis redirige vers la page de gestion des ramassages"""
	ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
	ramassage.delete()
	return redirect('ramassage')

@user_passes_test(is_secret, login_url='login_secret')
def ramassagePdf(request,id_ramassage):
	"""Renvoie le fichier PDF du ramassage correspondant au ramassage dont l'id est id_ramassage"""
	ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
	LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
	response = HttpResponse(content_type='application/pdf')
	debut=ramassage.moisDebut
	fin=ramassage.moisFin
	listeDecompte,effectifs=Ramassage.objects.decompte(debut,fin)
	nomfichier="ramassage{}_{}-{}_{}.pdf".format(debut.month,debut.year,fin.month,fin.year)
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	pdf = easyPdf(titre="Ramassage des colles de {} {} à {} {}".format(LISTE_MOIS[debut.month],debut.year,LISTE_MOIS[fin.month],fin.year),marge_x=30,marge_y=30)
	largeurcel=(pdf.format[0]-2*pdf.marge_x)/(9+len(effectifs))
	hauteurcel=30
	nbKolleurs=sum([z for x,y,z in listeDecompte])
	nbPages = -(-nbKolleurs//23)
	pdf.debutDePage()
	LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
										,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
										,('VALIGN',(0,0),(-1,-1),'MIDDLE')
										,('ALIGN',(0,0),(-1,-1),'CENTRE')
										,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
										,('SIZE',(0,0),(-1,-1),8)])
	data = [["Matière","Établissement","Grade","Colleur"]+["{}è. ann.\n{}".format(annee,effectif) for annee,effectif in effectifs]]+[[""]*(4+len(effectifs)) for i in range(min(23,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
	ligneMat=ligneEtab=ligneGrade=ligneColleur=1
	resteMat=resteEtab=resteGrade=0
	for matiere, listeEtabs, nbEtabs in listeDecompte:
		data[ligneMat][0]=matiere.title()
		if nbEtabs>1:
			LIST_STYLE.add('SPAN',(0,ligneMat),(0,min(ligneMat+nbEtabs-1,23)))
		ligneMat+=nbEtabs
		for etablissement, listeGrades, nbGrades in listeEtabs:
			data[ligneEtab][1]='Inconnu' if not etablissement else etablissement.title()
			if nbGrades>1:
				LIST_STYLE.add('SPAN',(1,ligneEtab),(1,min(ligneEtab+nbGrades-1,23)))
			ligneEtab+=nbGrades
			for grade, listeColleurs, nbColleurs in listeGrades:
				data[ligneGrade][2]=grade
				if nbColleurs>1:
					LIST_STYLE.add('SPAN',(2,ligneGrade),(2,min(ligneGrade+nbColleurs-1,23)))
				ligneGrade+=nbColleurs
				for colleur, decomptes in listeColleurs:
					data[ligneColleur][3]=colleur
					for i in range(len(effectifs)):
						data[ligneColleur][i+4]="{}h{:02d}".format(decomptes[i]//60,decomptes[i]%60)
					ligneColleur+=1
					if ligneColleur==24 and nbKolleurs>23: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
						t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel]+[largeurcel]*len(effectifs),rowHeights=min((1+nbKolleurs),24)*[hauteurcel])
						t.setStyle(LIST_STYLE)
						w,h=t.wrapOn(pdf,0,0)
						t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
						pdf.finDePage()
						# on redémarre sur une nouvelle page
						pdf.debutDePage()
						LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
										,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
										,('VALIGN',(0,0),(-1,-1),'MIDDLE')
										,('ALIGN',(0,0),(-1,-1),'CENTRE')
										,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
										,('SIZE',(0,0),(-1,-1),8)])
						nbKolleurs-=23
						data = [["Matière","Établissement","Grade","Colleur"]+["{}è. ann.\n{}".format(annee,effectif) for annee,effectif in effectifs]]+[[""]*(4+len(effectifs)) for i in range(min(23,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
						ligneEtab-=23
						ligneGrade-=23
						ligneMat-=23
						ligneColleur=1
						if ligneMat>1:
							data[1][0]=matiere.title()
							if ligneMat>2:
								LIST_STYLE.add('SPAN',(0,1),(0,min(ligneMat-1,23)))
							if ligneEtab>=1:
								data[1][1]='Inconnu' if not etablissement else etablissement.title()
								if ligneEtab>=2:
									LIST_STYLE.add('SPAN',(1,1),(1,min(ligneEtab,23)))
								if ligneGrade>=1:
									data[1][2]=grade
									if ligneGrade>=2:
										LIST_STYLE.add('SPAN',(2,1),(2,min(ligneGrade,23)))
	t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel]+[largeurcel]*len(effectifs),rowHeights=min((1+nbKolleurs),24)*[hauteurcel])
	t.setStyle(LIST_STYLE)
	w,h=t.wrapOn(pdf,0,0)
	t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
	pdf.finDePage()
	pdf.save()
	fichier = pdf.buffer.getvalue()
	pdf.buffer.close()
	response.write(fichier)
	return response

@user_passes_test(is_secret, login_url='accueil')
def groupe(request,id_classe):
	"""Renvoie la vue de la page de gestion des groupes de la classe dont l'id est id_classe"""
	if not conf.config.MODIF_SECRETARIAT_GROUPE:
		return HttpResponseForbidden("Accès non autorisé")
	classe=get_object_or_404(Classe,pk=id_classe)
	groupes = Groupe.objects.filter(classe=classe).prefetch_related('groupeeleve__user')
	form = GroupeForm(classe,None,request.POST or None)
	if form.is_valid():
		form.save()
		return redirect('groupe_secret', classe.pk)
	return render(request,"mixte/groupe.html",{'classe':classe,'groupes':groupes,'form':form,'hide':json.dumps([(eleve.id,"" if not eleve.lv1 else eleve.lv1.pk,"" if not eleve.lv2 else eleve.lv2.pk) for eleve in form.fields['eleve0'].queryset])})

@user_passes_test(is_secret, login_url='accueil')
def groupeSuppr(request,id_groupe):
	"""Essaie de supprimer la groupe dont l'id est id_groupe, puis redirige vers la page de gestion des groupes"""
	if not conf.config.MODIF_SECRETARIAT_GROUPE:
		return HttpResponseForbidden("Accès non autorisé")
	groupe=get_object_or_404(Groupe,pk=id_groupe)
	try:
		groupe.delete()
	except Exception:
		messages.error(request,"Impossible de supprimer le groupe car il est présent dans le colloscope")
	return redirect('groupe_secret',groupe.classe.pk)

@user_passes_test(is_secret, login_url='accueil')
def groupeModif(request,id_groupe):
	"""Renvoie la vue de la page de modification du groupe dont l'id est id_groupe"""
	if not conf.config.MODIF_SECRETARIAT_GROUPE:
		return HttpResponseForbidden("Accès non autorisé")
	groupe=get_object_or_404(Groupe,pk=id_groupe)
	initial = {"eleve{}".format(i):eleve for i,eleve in enumerate(groupe.groupeeleve.all())}
	initial['nom']=groupe.nom
	form = GroupeForm(groupe.classe,groupe,request.POST or None, initial=initial)
	if form.is_valid():
		form.save()
		return redirect('groupe_secret', groupe.classe.pk)
	return render(request,'mixte/groupeModif.html',{'form':form,'groupe':groupe,'hide':json.dumps([(eleve.id,"" if not eleve.lv1 else eleve.lv1.pk,"" if not eleve.lv2 else eleve.lv2.pk) for eleve in form.fields['eleve0'].queryset])})

@user_passes_test(is_secret_ects, login_url='login_secret')
def ectscredits(request,id_classe,form=None):
	classe =get_object_or_404(Classe,pk=id_classe)
	eleves = Eleve.objects.filter(classe=classe).order_by('user__last_name','user__first_name')
	if not form:
		form=ECTSForm(classe,request.POST or None)
	credits,total = NoteECTS.objects.credits(classe)
	return render(request,'mixte/ectscredits.html',{'classe':classe,'credits':credits,'form':form,'total':total,"nbeleves":eleves.order_by().count()})

@user_passes_test(is_secret_ects, login_url='login_secret')
def ficheectspdf(request,id_eleve):
	eleve = get_object_or_404(Eleve,pk=id_eleve)
	return creditsects(request,eleve,eleve.classe)

@user_passes_test(is_secret_ects, login_url='login_secret')
def attestationectspdf(request,id_eleve):
	eleve = get_object_or_404(Eleve,pk=id_eleve)
	return attestationects(request,eleve,eleve.classe)

@user_passes_test(is_secret_ects, login_url='login_secret')
def ficheectsclassepdf(request,id_classe):
	classe = get_object_or_404(Classe,pk=id_classe)
	return creditsects(request,None,classe)

@user_passes_test(is_secret_ects, login_url='login_secret')
def attestationectsclassepdf(request,id_classe):
	classe = get_object_or_404(Classe,pk=id_classe)
	return attestationects(request,None,classe)