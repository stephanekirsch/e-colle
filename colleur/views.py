#-*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from colleur.forms import ColleurConnexionForm, NoteForm, ProgrammeForm, GroupeForm, NoteGroupeForm, CreneauForm, SemaineForm, ColleForm, EleveForm, MatiereECTSForm, SelectEleveForm, NoteEleveForm, NoteEleveFormSet, ECTSForm
from accueil.models import Colleur, Matiere, Prof, Classe, Note, Eleve, Semaine, Programme, Groupe, Creneau, Colle, JourFerie, MatiereECTS, NoteECTS
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import F, Count, Avg, Min, Max, StdDev, Sum
from datetime import date, timedelta
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.forms.formsets import formset_factory
from copy import copy
from pdf.pdf import Pdf, easyPdf, FlowTextRectangle
from reportlab.platypus import Table, TableStyle, Image, Frame, Paragraph
from reportlab.lib.styles import ParagraphStyle
import os
import json
import csv
from lxml import etree
from ecolle.settings import MEDIA_ROOT, MEDIA_URL, MATHJAX, IMAGEMAGICK, RESOURCES_ROOT, NOM_ADRESSE_ETABLISSEMENT, VILLE, NOM_ETABLISSEMENT, ACADEMIE

def is_colleur(user):
	"""Renvoie True si l'utilisateur est authentifié et est un colleur, False sinon"""
	if user.is_authenticated() and user.is_active:
		return bool(user.colleur)
	return False

def is_prof(user,matiere,classe):
	"""Renvoie True si l'utilisateur est un prof de la classe classe et dans la matière matière, False sinon"""
	if matiere==None:
		return Prof.objects.filter(classe=classe,colleur=user.colleur).exists()
	else:
		return Prof.objects.filter(classe=classe,matiere=matiere,colleur=user.colleur).exists()

def modifgroupe(colleur,classe):
	"""Renvoie True si colleur a les drois en modification des groupes dans la classe classe, False sinon"""
	return classe.profprincipal==colleur or (colleur in Colleur.objects.filter(colleurprof__classe=classe,colleurprof__modifgroupe=True))

def modifcolloscope(colleur,classe):
	"""Renvoie True si colleur a les drois en modification du colloscope dans la classe classe, False sinon"""
	return classe.profprincipal==colleur or (colleur in Colleur.objects.filter(colleurprof__classe=classe,colleurprof__modifcolloscope=True))

def is_profprincipal(user,classe=False):
	"""Renvoie True si user est professeur principal de la classe classe, False sinon"""
	if classe:
		return classe.profprincipal == user.colleur
	else:
		return bool(user.colleur.classeprofprincipal.all())

def connec(request, id_matiere):
	"""Renvoie la vue de la page de connexion des colleurs. Si le colleur est déjà connecté, redirige vers la page d'accueil des colleurs"""
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	if is_colleur(request.user):
		return redirect('action_colleur')
	error = False
	form = ColleurConnexionForm(matiere,request.POST or None)
	if form.is_valid():
		username=form.cleaned_data['colleur'].user.username
		user = authenticate(username=username,password=form.cleaned_data['password'])
		if user is not None and user.is_active:
			login(request,user)
			request.session['matiere']=matiere.pk
			return redirect('action_colleur')
		else:
			error = True
	return render(request,'colleur/home.html',{'form':form, 'matiere':matiere,'error':error})

@user_passes_test(is_colleur, login_url='accueil')
def changemat(request,id_mat):
	"""La matière courante du colleur devient la matière dont l'id est id_mat, puis redirige vers la page d'accueil des colleurs"""
	matiere=get_object_or_404(Matiere,pk=id_mat,colleur=request.user.colleur)
	request.session['matiere']=matiere.pk
	return redirect('action_colleur')

@user_passes_test(is_colleur, login_url='accueil')
def action(request):
	"""Renvoie la vue de la page d'accueil des colleurs"""
	return render(request,"colleur/action.html")

@user_passes_test(is_colleur, login_url='accueil')
def note(request,id_classe):
	"""Renvoie la vue de la page de gestion des notes"""
	classe=get_object_or_404(Classe,pk=id_classe)
	colleur=request.user.colleur
	matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=request.user.colleur)
	if classe not in colleur.classes.all() or matiere.pk not in classe.matierespk():
		raise Http404
	groupes = Groupe.objects.filter(classe=classe).values('nom','pk').annotate(nb=Count('groupeeleve'))
	nom_groupes = []
	eleves_groupes = list(Eleve.objects.filter(classe=classe,groupe__isnull=False).values('pk','user__first_name','user__last_name').order_by('groupe__nom','user__last_name','user__first_name'))
	for value in groupes:
		nom_groupes.append((value['nom'],value['pk'],value['nb'],[("{} {}".format(x['user__first_name'].title(),x['user__last_name'].upper()),x['pk']) for x in eleves_groupes[:value['nb']]]))
		del eleves_groupes[:value['nb']]
	eleves=Eleve.objects.filter(classe=classe,groupe__isnull=True).values('pk','user__first_name','user__last_name').order_by('user__last_name','user__first_name')
	modulo = eleves.count() % 3
	return render(request,"colleur/note.html",{'notes':Note.objects.listeNotes(classe,matiere,colleur),'classe':classe,'eleves':eleves,'groupes':nom_groupes,'modulo':modulo,'latex':MATHJAX})

@user_passes_test(is_colleur, login_url='accueil')
def noteEleve(request,id_eleve,id_classe,colle=None):
	"""Renvoie la vue de la page de notation de l'élève dont l'id est id_eleve et dont la classe a pour id id_classe"""
	# on renseigne aussi la classe dans l'éventualité d'un élève fictif(None) qui n'a pas de classe
	try:
		eleve=Eleve.objects.get(pk=id_eleve)
	except Exception:
		eleve=None
	colleur=request.user.colleur
	matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
	if eleve is not None and eleve.classe not in colleur.classes.all():
		raise Http404
	try:
		classe=eleve.classe
	except Exception:
		classe=Classe.objects.get(pk=id_classe)
	if matiere.pk not in classe.matierespk():
		raise Http404
	note=Note(matiere=matiere,colleur=colleur,eleve=eleve,classe=classe)
	if colle:
		note.semaine=colle.semaine
		note.jour=colle.creneau.jour
		note.heure=colle.creneau.heure
	form=NoteForm(request.POST or None,instance=note)
	if form.is_valid():
		form.save()
		return redirect('note_colleur',classe.pk)
	return render(request,"colleur/noteEleve.html",{'eleve':eleve,'form':form,'classe':classe,'matiere':matiere})

@user_passes_test(is_colleur, login_url='accueil')
def noteGroupe(request,id_groupe,colle=None):
	"""Renvoie la vue de la page de notation de du groupe dont l'id est id_groupe.
	Si colle est renseigné, les champs semaine/jour/heure sont préremplis avec ceux de la colle"""
	groupe=get_object_or_404(Groupe,pk=id_groupe)
	colleur=request.user.colleur
	if groupe.classe not in colleur.classes.all():
		raise Http404
	if colle:
		matiere=colle.matiere
		form=NoteGroupeForm(groupe,matiere,colleur,request.POST or None, initial={'semaine':colle.semaine,'jour':colle.creneau.jour,'heure':colle.creneau.heure})
	else:
		matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
		form=NoteGroupeForm(groupe,matiere,colleur,request.POST or None)
	eleves=list(groupe.groupeeleve.all().select_related('user'))
	eleves+=[None]*(3-len(eleves))
	if form.is_valid():
		form.save()
		return redirect('note_colleur', groupe.classe.pk)
	return render(request,"colleur/noteGroupe.html",{'form':form,'groupe':groupe,'eleves':eleves,'matiere':matiere})

@user_passes_test(is_colleur, login_url='accueil')
def noteModif(request,id_note):
	"""Renvoie la vue de la page de modifcation de la note dont l'id est id_note"""
	note=get_object_or_404(Note,pk=id_note)
	colleur=request.user.colleur
	if note.colleur != colleur:
		messages.error(request,"Vous n'êtes pas le colleur de cette colle")
		return redirect('action_colleur')
	elif note.matiere.pk != request.session['matiere']:
		messages.error(request,"Ce n'est pas la bonne matière")
		return redirect('action_colleur')
	form = NoteForm(request.POST or None, instance=note)
	if form.is_valid():
		form.save()
		return redirect('note_colleur', note.classe.pk)
	return render(request,"colleur/noteEleve.html",{'eleve':note.eleve,'form':form,'classe':note.classe,'matiere':note.matiere})

@user_passes_test(is_colleur, login_url='accueil')
def noteSuppr(request,id_note):
	"""Essaie de supprimer la note dont l'id est id_note puis redirige vers la page de gestion des notes"""
	note=get_object_or_404(Note,pk=id_note)
	if note.colleur != request.user.colleur:
		messages.error(request,"Vous n'êtes pas le colleur de cette colle")
		return redirect('action_colleur')
	elif note.matiere.pk != request.session['matiere']:
		messages.error(request,"Ce n'est pas la bonne matière")
		return redirect('action_colleur')
	note.delete()
	return redirect('note_colleur', note.classe.pk)

@user_passes_test(is_colleur, login_url='accueil')
def resultat(request,id_classe):
	"""Renvoie la vue de la page des résultats de la classe dont l'id est id_classe"""
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
	return redirect('resultat2_colleur',id_classe,semin.pk,semax.pk)

@user_passes_test(is_colleur, login_url='accueil')
def resultat2(request,id_classe,id_semin,id_semax):
	"""Renvoie la vue de la page des résultats de la classe dont l'id est id_classe, entre les semaine dont l'id est id_semin et id_semax"""
	classe=get_object_or_404(Classe,pk=id_classe)
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	if classe not in request.user.colleur.classes.all():
		raise Http404
	form=SemaineForm(request.POST or None,initial={'semin':semin,'semax':semax})
	if form.is_valid():
		return redirect('resultat2_colleur',id_classe,form.cleaned_data['semin'].pk,form.cleaned_data['semax'].pk)
	matiere = get_object_or_404(Matiere,pk=request.session['matiere'])
	generateur = Note.objects.classe2resultat(matiere,classe,semin,semax)
	semaines = next(generateur)
	isprof = is_prof(request.user,matiere,classe)
	stat_colleurs = Note.objects.filter(classe=classe,matiere=matiere,semaine__lundi__range=(semin.lundi,semax.lundi)).exclude(note__gt=20).values('colleur__user__first_name','colleur__user__last_name').distinct().annotate(moy=Avg('note'),minimum=Min('note'),maximum=Max('note'),ecarttype=StdDev('note')) if isprof else False
	return render(request,"colleur/resultat.html",{'form':form,'classe':classe,'semaines':semaines,'matiere':matiere,'notes':generateur,'isprof':isprof,'semin':semin,'semax':semax,'stats':stat_colleurs,'latex':MATHJAX})

@user_passes_test(is_colleur, login_url='accueil')
def resultatcsv(request,id_classe,id_semin,id_semax):
	"""Renvoie le fichier csv des résultats de la classe dont l'id est id_classe, entre les semaine dont l'id est id_semin et id_semax"""
	classe=get_object_or_404(Classe,pk=id_classe)
	if classe not in request.user.colleur.classes.all():
		raise Http404
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	matiere = get_object_or_404(Matiere,pk=request.session['matiere'])
	generateur = Note.objects.classe2resultat(matiere,classe,semin,semax)
	semaines = next(generateur)
	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename="resultats_{}_{}_s{}-s{}.csv"'.format(classe.nom,matiere.nom,semin.numero,semax.numero)
	writer = csv.writer(response)
	writer.writerow(['Élève','rang','moyenne']+['S{}'.format(semaine.numero) for semaine in semaines])
	notation = {i:str(i) for i in range(21)}
	notation[21]="n.n."
	notation[22]="abs"
	for note in generateur:
		writer.writerow([note['eleve'],note['rang'],note['moyenne']]+["|".join([notation[note['note']] for note in value]) for value in note['semaine']])
	return response

@user_passes_test(is_colleur, login_url='accueil')
def programme(request,id_classe):
	"""Renvoie la vue de la page de gestion des programmes de la classe dont l'id est id_classe"""
	classe=get_object_or_404(Classe,pk=id_classe)
	colleur=request.user.colleur
	matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
	if classe not in request.user.colleur.classes.all() or matiere.pk not in classe.matierespk():
		raise Http404
	programmes=Programme.objects.filter(classe=classe,matiere=matiere).select_related('semaine').order_by('-semaine__lundi')
	isprof=False
	if is_prof(request.user,matiere,classe):
		isprof=True
		programme=Programme(matiere=matiere,classe=classe)
		form = ProgrammeForm(request.POST or None,request.FILES or None,instance=programme)
		if form.is_valid():
			form.save()
			return redirect('programme_colleur',classe.pk)
	else:
		form=False
	return render(request,"colleur/programme.html",{'programmes':programmes,'classe':classe,'matiere':matiere,'form':form,'isprof':isprof,'latex':MATHJAX,'jpeg':IMAGEMAGICK})

@user_passes_test(is_colleur, login_url='accueil')
def programmeSuppr(request,id_programme):
	"""Essaie de supprimer le programme dont l'id est id_classe puis redirige vers la page de gestion des programmes"""
	programme=get_object_or_404(Programme,pk=id_programme)
	if not is_prof(request.user,programme.matiere,programme.classe):
		raise Http404
	programme.delete()
	return redirect('programme_colleur', programme.classe.pk)

@user_passes_test(is_colleur, login_url='accueil')
def programmeModif(request,id_programme):
	"""Renvoie la vue de la page de modification du programme dont l'id est id_programme"""
	programme=get_object_or_404(Programme,pk=id_programme)
	if not is_prof(request.user,programme.matiere,programme.classe):
		raise Http404
	form=ProgrammeForm(request.POST or None,request.FILES or None, instance=programme)
	oldfile=MEDIA_ROOT+programme.fichier.name if programme.fichier else False
	if form.is_valid():
		if request.FILES and oldfile:
			if os.path.isfile(oldfile):
				os.remove(oldfile)
			nomimage=oldfile.replace('programme','image').replace('pdf','jpg')
			if os.path.isfile(nomimage):
				os.remove(nomimage)
		form.save()
		return redirect('programme_colleur', programme.classe.pk)
	return render(request,"colleur/programmeModif.html",{'programme':programme,'form':form})

@user_passes_test(is_colleur, login_url='accueil')
def groupe(request,id_classe):
	"""Renvoie la vue de la page de gestion des groupes de la classe dont l'id est id_classe"""
	classe=get_object_or_404(Classe,pk=id_classe)
	if not modifgroupe(request.user.colleur,classe):
		return HttpResponseForbidden("Accès non autorisé")
	groupes = Groupe.objects.filter(classe=classe).prefetch_related('groupeeleve__user')
	form = GroupeForm(classe,None,request.POST or None)
	if form.is_valid():
		form.save()
		return redirect('groupe_colleur', classe.pk)
	return render(request,"colleur/groupe.html",{'classe':classe,'groupes':groupes,'form':form})

@user_passes_test(is_colleur, login_url='accueil')
def groupeSuppr(request,id_groupe):
	"""Essaie de supprimer la groupe dont l'id est id_groupe, puis redirige vers la page de gestion des groupes"""
	groupe=get_object_or_404(Groupe,pk=id_groupe)
	colleur=request.user.colleur
	matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
	if not modifgroupe(request.user.colleur,groupe.classe):
		return HttpResponseForbidden("Accès non autorisé")
	else:
		groupe.delete()
	return redirect('groupe_colleur',groupe.classe.pk)

@user_passes_test(is_colleur, login_url='accueil')
def groupeModif(request,id_groupe):
	"""Renvoie la vue de la page de modification du groupe dont l'id est id_groupe"""
	groupe=get_object_or_404(Groupe,pk=id_groupe)
	colleur=request.user.colleur
	matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
	if not modifgroupe(request.user.colleur,groupe.classe):
		return HttpResponseForbidden("Accès non autorisé")
	initial = {"eleve{}".format(i):eleve for i,eleve in enumerate(groupe.groupeeleve.all())}
	initial['nom']=groupe.nom
	form = GroupeForm(groupe.classe,groupe,request.POST or None, initial=initial)
	if form.is_valid():
		form.save()
		return redirect('groupe_colleur', groupe.classe.pk)
	return render(request,'colleur/groupeModif.html',{'form':form,'groupe':groupe})

@user_passes_test(is_colleur, login_url='accueil')
def colloscope(request,id_classe):
	"""Renvoie la vue de la page de gestion du colloscope de la classe dont l'id est id_classe"""
	classe=get_object_or_404(Classe,pk=id_classe)
	semaines=list(Semaine.objects.all())
	try:
		semin=semaines[0]
	except Exception:
		raise Http404
	try:
		semax=semaines[-1]
	except Exception:
		raise Http404
	return colloscope2(request,id_classe,semin.pk,semax.pk)

@user_passes_test(is_colleur, login_url='accueil')
def colloscope2(request,id_classe,id_semin,id_semax):
	"""Renvoie la vue de la page de gestion du colloscope de la classe dont l'id est id_classe,
	dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
	classe=get_object_or_404(Classe,pk=id_classe)
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	if classe not in request.user.colleur.classes.all():
		raise Http404
	form=SemaineForm(request.POST or None,initial={'semin':semin,'semax':semax})
	if form.is_valid():
		return redirect('colloscope2_colleur',id_classe,form.cleaned_data['semin'].pk,form.cleaned_data['semax'].pk)
	groupes = Groupe.objects.filter(classe=classe).values('nom','pk').annotate(nb=Count('groupeeleve'))
	nom_groupes = []
	eleves_groupes = list(Eleve.objects.filter(classe=classe,groupe__isnull=False).values('pk','user__first_name','user__last_name').order_by('groupe__nom','user__last_name','user__first_name'))
	for value in groupes:
		nom_groupes.append((value['pk'],(value['nom'],"; ".join(["{} {}".format(x['user__first_name'].title(),x['user__last_name'].upper()) for x in eleves_groupes[:value['nb']]]))))
		del eleves_groupes[:value['nb']]
	listegroupes = dict(nom_groupes)
	jours,creneaux,colles,semaines=Colle.objects.classe2colloscope(classe,semin,semax)
	return render(request,'colleur/colloscope.html',
	{'semin':semin,'semax':semax,'form':form,'isprof':modifcolloscope(request.user.colleur,classe),'classe':classe,'jours':jours,'listegroupes':listegroupes,'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'dictColleurs':classe.dictColleurs(semin,semax)})

@user_passes_test(is_colleur, login_url='accueil')
def colloscopeModif(request,id_classe,id_semin,id_semax,creneaumodif=None):
	"""Renvoie la vue de la page de modification du colloscope de la classe dont l'id est id_classe,
	dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
	classe=get_object_or_404(Classe,pk=id_classe)
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	colleur=request.user.colleur
	matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
	if not modifcolloscope(request.user.colleur,classe):
		return HttpResponseForbidden("Accès non autorisé")
	form1=SemaineForm(request.POST or None,initial={'semin':semin,'semax':semax})
	if form1.is_valid():
		return redirect('colloscopemodif_colleur',id_classe,form1.cleaned_data['semin'].pk,form1.cleaned_data['semax'].pk)
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
		return redirect('colloscopemodif_colleur',classe.pk,semin.pk,semax.pk)
	matieres = list(classe.matieres.filter(colleur__classes=classe).values_list('pk','nom','couleur','temps').annotate(nb=Count("colleur")))
	colleurs = list(Classe.objects.filter(pk=classe.pk,matieres__colleur__classes=classe).values_list('matieres__colleur__pk','matieres__colleur__user__username','matieres__colleur__user__first_name','matieres__colleur__user__last_name').order_by("matieres__nom","matieres__colleur__user__last_name","matieres__colleur__user__first_name"))
	listeColleurs = []
	for x in matieres:
		listeColleurs.append(colleurs[:x[4]])
		del colleurs[:x[4]]
	groupes = Groupe.objects.filter(classe=classe)
	largeur=str(650+42*creneaux.count())+'px'
	hauteur=str(27*(len(matieres)+classe.classeeleve.count()+Colleur.objects.filter(classes=classe).count()))+'px'
	return render(request,'colleur/colloscopeModif.html',
	{'semin':semin,'semax':semax,'form1':form1,'form':form,'form2':form2,'largeur':largeur,'hauteur':hauteur,'groupes':groupes,'matieres':zip(matieres,listeColleurs),'creneau':creneaumodif\
	,'classe':classe,'jours':jours,'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'dictColleurs':classe.dictColleurs(semin,semax)})

@user_passes_test(is_colleur, login_url='accueil')
def creneauSuppr(request,id_creneau,id_semin,id_semax):
	"""Essaie de supprimer le créneau dont l'id est id_creneau puis redirige vers la page de modification du colloscope
	dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	if not modifcolloscope(request.user.colleur,creneau.classe):
		return HttpResponseForbidden("Accès non autorisé")
	try:
		creneau.delete()
	except Exception:
		messages.error(request,"Vous ne pouvez pas effacer un créneau qui contient des colles")
	return redirect('colloscopemodif_colleur',creneau.classe.pk,id_semin,id_semax)

@user_passes_test(is_colleur, login_url='accueil')
def creneauModif(request,id_creneau,id_semin,id_semax):
	"""Renvoie la vue de la page de modification du creneau dont l'id est id_creneau"""
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	if not modifcolloscope(request.user.colleur,creneau.classe):
		return HttpResponseForbidden("Accès non autorisé")
	return colloscopeModif(request,creneau.classe.pk,id_semin,id_semax,creneaumodif=creneau)

@user_passes_test(is_colleur, login_url='accueil')
def creneauDupli(request,id_creneau,id_semin,id_semax):
	"""Renvoie la vue de la page de duplication du creneau dont l'id est id_creneau"""
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	if not modifcolloscope(request.user.colleur,creneau.classe):
		return HttpResponseForbidden("Accès non autorisé")
	creneau.pk=None
	creneau.salle=None
	creneau.save()
	return redirect('colloscopemodif_colleur',creneau.classe.pk,id_semin,id_semax)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcompat(request,id_classe):
	"""Renvoie ue chaîne de caractères récapitulant les incompatibilités du colloscope de la classe dont l'id est id_classe"""
	LISTE_JOURS=['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
	classe=get_object_or_404(Classe,pk=id_classe)
	colleurs = Colle.objects.filter(groupe__classe=classe).values('colleur__user__first_name','colleur__user__last_name','semaine__numero','creneau__jour','creneau__heure').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','creneau__jour','creneau__heure','colleur__user__last_name','colleur__user__first_name')
	colleurs="\n".join(["le colleur {} {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['colleur__user__first_name'].title(),valeur['colleur__user__last_name'].upper(),valeur['nbcolles'],valeur['semaine__numero'],LISTE_JOURS[valeur['creneau__jour']],valeur['creneau__heure']//4,15*(valeur['creneau__heure']%4)) for valeur in colleurs])
	eleves = Colle.objects.filter(groupe__classe=classe).values('groupe__nom','semaine__numero','creneau__jour','creneau__heure').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','creneau__jour','creneau__heure','groupe__nom')
	eleves="\n".join(["le groupe {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['groupe__nom'].title(),valeur['nbcolles'],valeur['semaine__numero'],LISTE_JOURS[valeur['creneau__jour']],valeur['creneau__heure']//4,15*(valeur['creneau__heure']%4)) for valeur in eleves])
	elevesolo = Colle.objects.compatEleve(id_classe)
	elevesolo = "\n".join(["l'élève {} {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['prenom'].title(),valeur['nom'].upper(),valeur['nbcolles'],valeur['numero'],LISTE_JOURS[valeur['jour']],valeur['heure']//4,15*(valeur['heure']%4)) for valeur in elevesolo])
	groupes=Colle.objects.filter(groupe__classe=classe).values('groupe__nom','matiere__nom','semaine__numero').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','matiere__nom','groupe__nom')
	groupes = "\n".join(["le groupe {} a {} colles de {} en semaine {}".format(valeur['groupe__nom'].title(),valeur['nbcolles'],valeur['matiere__nom'].title(),valeur['semaine__numero']) for valeur in groupes])
	reponse=colleurs+"\n\n"*int(bool(colleurs))+eleves+"\n\n"*int(bool(eleves))+elevesolo+"\n\n"*int(bool(elevesolo))+groupes
	if not reponse:
		reponse="aucune incompatibilité dans le colloscope"
	return HttpResponse(reponse)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxmajcolleur(request, id_matiere, id_classe):
	"""Renvoie la liste des colleurs de la classe dont l'id est id_classe et de la matière dont l'id est id_matiere, au format json"""
	classe=get_object_or_404(Classe,pk=id_classe)
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	if not modifcolloscope(request.user.colleur,classe):
		return HttpResponseForbidden("Accès non autorisé")
	colleurs=Colleur.objects.filter(matieres=matiere,classes=classe).values('id','user__first_name','user__last_name','user__username').order_by('user__first_name','user__last_name')
	colleurs=[{'nom': value['user__first_name'].title()+" "+value['user__last_name'].upper()+' ('+classe.dictColleurs()[value['id']]+')','id':value['id']} for value in colleurs]
	return HttpResponse(json.dumps([matiere.temps]+colleurs))

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcolloscope(request, id_matiere, id_colleur, id_groupe, id_semaine, id_creneau):
	"""Ajoute la colle propre au quintuplet (matière,colleur,groupe,semaine,créneau) et renvoie le username du colleur
	en effaçant au préalable toute colle déjà existante sur ce couple créneau/semaine"""
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	colleur=get_object_or_404(Colleur,pk=id_colleur)
	groupe=get_object_or_404(Groupe,pk=id_groupe)
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	if not modifcolloscope(request.user.colleur,creneau.classe) or matiere not in colleur.matieres.all() or matiere not in creneau.classe.matieres.all():
		return HttpResponseForbidden("Accès non autorisé")
	Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
	feries = [dic['date'] for dic in JourFerie.objects.all().values('date')]
	if semaine.lundi+timedelta(days=creneau.jour) in feries:
		return HttpResponse("jour férié")
	Colle(semaine=semaine,creneau=creneau,groupe=groupe,colleur=colleur,matiere=matiere).save()
	return HttpResponse(creneau.classe.dictColleurs()[colleur.pk]+':'+groupe.nom)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcolloscopeeleve(request, id_matiere, id_colleur, id_eleve, id_semaine, id_creneau, login):
	"""Ajoute la colle propre au quintuplet (matière,colleur,eleve,semaine,créneau) et renvoie le username du colleur
	en effaçant au préalable toute colle déjà existante sur ce couple créneau/semaine"""
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	colleur=get_object_or_404(Colleur,pk=id_colleur)
	try:
		eleve = Eleve.objects.get(pk=id_eleve)
	except Exception:
		if matiere.temps == 60:
			eleve = None
		else:
			raise Http404
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	if not modifcolloscope(request.user.colleur,creneau.classe) or matiere not in colleur.matieres.all() or matiere not in creneau.classe.matieres.all():
		return HttpResponseForbidden("Accès non autorisé")
	Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
	feries = [dic['date'] for dic in JourFerie.objects.all().values('date')]
	if semaine.lundi+timedelta(days=creneau.jour) in feries:
		return HttpResponse("jour férié")
	colle=Colle(semaine=semaine,creneau=creneau,colleur=colleur,eleve=eleve,matiere=matiere)
	if eleve is None:
		colle.classe=creneau.classe
		colle.save()
		return HttpResponse(creneau.classe.dictColleurs()[colleur.pk]+':')
	else:
		colle.save()
		return HttpResponse(creneau.classe.dictColleurs()[colleur.pk]+':'+login)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcolloscopeeffacer(request,id_semaine, id_creneau):
	"""Efface la colle sur le créneau dont l'id est id_creneau et la semaine sont l'id est id_semaine
	puis renvoie la chaine de caractères "efface" """
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	if not modifcolloscope(request.user.colleur,creneau.classe):
		return HttpResponseForbidden("Accès non autorisé")
	Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
	return HttpResponse("efface")

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcolloscopemulti(request, id_matiere, id_colleur, id_groupe, id_eleve, id_semaine, id_creneau, duree, frequence, permutation):
	"""Compte le nombre de colles présente sur les couples créneau/semaine sur le créneau dont l'id est id_creneau
	et les semaines dont le numéro est compris entre celui de la semaine d'id id_semaine et ce dernier + duree
	et dont le numéro est congru à celui de la semaine d'id id_semaine modulo frequence
	S'il n'y en a aucune, ajoute les colles sur les couples créneau/semaine précédents, avec le colleur dont l'id est id_colleur
	le groupe démarre au groupe dont l'id est id_groupe puis va de permutation en permutation, et la matière dont l'id est id_matière"""
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	colleur=get_object_or_404(Colleur,pk=id_colleur)
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	if not modifcolloscope(request.user.colleur,creneau.classe) or matiere not in colleur.matieres.all() or matiere not in creneau.classe.matieres.all():
		return HttpResponseForbidden("Accès non autorisé")
	frequence = int(frequence)
	modulo = int(semaine.numero)%frequence
	ecrase = Colle.objects.filter(creneau = creneau,semaine__numero__range=(semaine.numero,semaine.numero+int(duree)-1)).annotate(semaine_mod = F('semaine__numero') % frequence).filter(semaine_mod=modulo).count()
	nbferies = JourFerie.objects.recupFerie(creneau.jour,semaine,duree,frequence,modulo)
	if not(ecrase and nbferies[0]):
		return HttpResponse("{}_{}".format(ecrase,nbferies[0]))
	else:
		return ajaxcolloscopemulticonfirm(request, id_matiere, id_colleur, id_groupe, id_eleve, id_semaine, id_creneau, duree, frequence, permutation)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcolloscopemulticonfirm(request, id_matiere, id_colleur, id_groupe, id_eleve, id_semaine, id_creneau, duree, frequence, permutation):
	"""ajoute les colles sur les couples créneau/semaine sur le créneau dont l'id est id_creneau
	et les semaines dont le numéro est compris entre celui de la semaine d'id id_semaine et ce dernier + duree
	et dont le numéro est congru à celui de la semaine d'id id_semaine modulo frequence, avec le colleur dont l'id est id_colleur
	le groupe démarre au groupe dont l'id est id_groupe puis va de permutation en permutation, et la matière dont l'id est id_matière"""
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	colleur=get_object_or_404(Colleur,pk=id_colleur)
	groupe=None if matiere.temps!=20 else get_object_or_404(Groupe,pk=id_groupe)
	eleve=None if matiere.temps!=30 else get_object_or_404(Eleve,pk=id_eleve)
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	if not modifcolloscope(request.user.colleur,creneau.classe) or matiere not in colleur.matieres.all() or matiere not in creneau.classe.matieres.all():
		return HttpResponseForbidden("Accès non autorisé")
	numsemaine=semaine.numero
	if matiere.temps == 20:
		groupeseleves=list(Groupe.objects.filter(classe=creneau.classe).order_by('nom'))
		rang=groupeseleves.index(groupe)
	elif matiere.temps == 30:
		groupeseleves=list(Eleve.objects.filter(classe=creneau.classe))
		rang=groupeseleves.index(eleve)
	i=0
	creneaux={'creneau':creneau.pk,'couleur':matiere.couleur,'colleur':colleur.user.username}
	creneaux['semgroupe']=[]
	feries = [dic['date'] for dic in JourFerie.objects.all().values('date')]
	if matiere.temps == 20:
		for numero in range(numsemaine,numsemaine+int(duree),int(frequence)):
			try:
				semainecolle=Semaine.objects.get(numero=numero)
				if semainecolle.lundi + timedelta(days = creneau.jour) not in feries:
					Colle.objects.filter(creneau=creneau,semaine=semainecolle).delete()
					groupe=groupeseleves[(rang+i*int(permutation))%len(groupeseleves)]
					Colle(creneau=creneau,colleur=colleur,matiere=matiere,groupe=groupe,semaine=semainecolle).save()
					creneaux['semgroupe'].append({'semaine':semainecolle.pk,'groupe':groupe.nom})
			except Exception:
				pass
			i+=1
	elif matiere.temps == 30:
		for numero in range(numsemaine,numsemaine+int(duree),int(frequence)):
			try:
				semainecolle=Semaine.objects.get(numero=numero)
				if semainecolle.lundi + timedelta(days = creneau.jour) not in feries:
					Colle.objects.filter(creneau=creneau,semaine=semainecolle).delete()
					eleve=groupeseleves[(rang+i*int(permutation))%len(groupeseleves)]
					Colle(creneau=creneau,colleur=colleur,matiere=matiere,eleve=eleve,semaine=semainecolle).save()
					creneaux['semgroupe'].append({'semaine':semainecolle.pk,'groupe':creneau.classe.dictEleves()[eleve.pk]})
			except Exception:
				pass
			i+=1
	return HttpResponse(json.dumps(creneaux))

@user_passes_test(is_colleur, login_url='accueil')
def agenda(request):
	"""Renvoie la vue de la page de l'agenda"""
	jour=date.today()
	semaine=jour+timedelta(days=-jour.weekday())
	semainemin=semaine+timedelta(days=-21)
	groupes,colles = Colle.objects.agenda(request.user.colleur,semainemin)
	return render(request,"colleur/agenda.html",{'colles':colles,'groupes':groupes,'media_url':MEDIA_URL,'jour':jour,'semaine':semaine,'latex':MATHJAX})

@user_passes_test(is_colleur, login_url='accueil')
def colleNote(request,id_colle):
	"""Récupère la colle dont l'id est id_colle puis redirige vers la page de notation des groupes sur la colle concernée"""
	colle=get_object_or_404(Colle,pk=id_colle,colleur=request.user.colleur,matiere__in=request.user.colleur.matieres.all()) # on récupère la colle
	request.session['matiere']=colle.matiere.pk # on met à jour la matière courante
	return noteGroupe(request,colle.groupe.pk,colle)

@user_passes_test(is_colleur, login_url='accueil')
def colleNoteEleve(request,id_colle):
	"""Récupère la colle dont l'id est id_colle puis redirige vers la page de notation de l'élève sur la colle concernée"""
	colle=get_object_or_404(Colle,pk=id_colle,colleur=request.user.colleur,matiere__in=request.user.colleur.matieres.all())
	request.session['matiere']=colle.matiere.pk # on met à jour la matière courante
	return noteEleve(request,colle.eleve.pk,colle.eleve.classe.pk,colle)

@user_passes_test(is_colleur, login_url='accueil')
def decompte(request):
	"""Renvoie la vue de la page du décompte des colles"""
	colleur=request.user.colleur
	matieres=colleur.matieres.order_by().values_list('nom',flat=True).distinct()
	classes=colleur.classes.all()
	listematieres=[]
	for matiere in matieres:
		listemois = Note.objects.filter(colleur=colleur,matiere__nom__iexact=matiere).dates('date_colle','month').distinct()
		listeclasses=[]
		for classe in classes:
			nbcolles=[]
			for mois in listemois:
				nbcolles.append(Note.objects.filter(colleur=colleur,matiere__nom__iexact=matiere,classe=classe,date_colle__month=mois.month,date_colle__year=mois.year).aggregate(temps=Sum('matiere__temps')))
			total=Note.objects.filter(colleur=colleur,matiere__nom__iexact=matiere,classe=classe).aggregate(temps=Sum('matiere__temps'))
			listeclasses.append((classe,nbcolles,total))
		listematieres.append((matiere,listeclasses,listemois))
		listematieres.sort(key=lambda x:x[0])
	return render(request,"colleur/decompte.html",{'listematieres':listematieres})

@user_passes_test(is_colleur, login_url='accueil')
def colloscopePdf(request,id_classe,id_semin,id_semax):
	"""Renvoie le fichier PDF du colloscope de la classe dont l'id est id_classe, entre les semaines d'id id_semin et id_semax"""
	classe=get_object_or_404(Classe,pk=id_classe)
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	if classe not in request.user.colleur.classes.all():
		raise Http404
	return Pdf(classe,semin,semax)

@user_passes_test(is_colleur, login_url='accueil')
def eleves(request,id_classe):
	"""Renvoie la vue de la page de gestion des élèves"""
	classe = get_object_or_404(Classe,pk=id_classe)
	if not is_profprincipal(request.user,classe):
		return HttpResponseForbidden("Accès non autorisé")
	try:
		eleve = Eleve.objects.get(pk=request.session['eleve'])
	except Exception:
		eleve = None
	try:
		semin = Semaine.objects.get(pk=request.session['semin'])
		semax = Semaine.objects.get(pk=request.session['semax'])
	except Exception:
		try:
			semaines = list(Semaine.objects.all())
			semin,semax = semaines[0],semaines[-1]
		except Exception:
			semin=semax=None
	if request.method == 'POST':
		 if 'semaines' in request.POST:
		 	form2 = SemaineForm(request.POST)
		 	form = EleveForm(classe, initial = {"eleve":eleve})
		 	if form2.is_valid():
		 		request.session['semin'] = form2.cleaned_data['semin'].pk
		 		request.session['semax'] = form2.cleaned_data['semax'].pk
		 		return redirect('eleves_colleur',classe.pk)
		 elif 'eleveselect' in request.POST:
		 	form2 = SemaineForm(initial = {'semin':semin,'semax':semax})
		 	form = EleveForm(classe,request.POST) 
		 	if form.is_valid():
		 		request.session['eleve'] = form.cleaned_data['eleve'].pk
		 		return redirect('eleves_colleur',classe.pk)
	else:
		form = EleveForm(classe, initial = {"eleve":eleve})
		form2 = SemaineForm(initial = {'semin':semin,'semax':semax})
	if eleve and semin and semax:
		semaines = Note.objects.filter(eleve=eleve,semaine__lundi__range=(semin.lundi,semax.lundi)).values('semaine','semaine__numero').distinct().order_by('semaine__lundi')
		matieres = classe.matieres.all().order_by('nom')
		matierenote=[]
		for matiere in matieres:
			moyenne = Note.objects.filter(eleve=eleve,semaine__lundi__range=(semin.lundi,semax.lundi),matiere=matiere).exclude(note__gt=20).aggregate(moy=Avg('note'))
			if moyenne['moy']:
				rang=Note.objects.exclude(note__gt=20).filter(classe=classe,eleve__isnull=False,matiere=matiere,semaine__lundi__range=(semin.lundi,semax.lundi)).values('eleve').annotate(Avg('note')).filter(note__avg__gt=moyenne['moy']+0.001).count()+1
			else:
				rang=""
			notes = []
			for semaine in semaines:
				note = Note.objects.filter(eleve=eleve,matiere=matiere,semaine__pk=semaine['semaine']).select_related('colleur__user')
				notes.append(note)
			matierenote.append((matiere,moyenne,rang,notes))
	else:
		semaines = matierenote = None
	return render(request,'colleur/eleves.html',{'eleve':eleve,'semin':semin,'semax':semax,'form':form,'form2':form2,'matierenote':matierenote,'semaines':semaines,'latex':MATHJAX})

@user_passes_test(is_colleur, login_url='accueil')
def ectsmatieres(request,id_classe):
	"""Renvoie la vue de la page de gestion des matières ects de la classe"""
	classe = get_object_or_404(Classe,pk=id_classe)
	if not is_profprincipal(request.user,classe):
		return HttpResponseForbidden("Accès non autorisé")
	matieresECTS = MatiereECTS.objects.filter(classe=classe).prefetch_related('profs').order_by('nom','precision')
	newMatiere = MatiereECTS(classe=classe)
	form = MatiereECTSForm(request.POST or None,instance=newMatiere)
	form.fields['profs'].queryset=Colleur.objects.filter(classes=classe,colleurprof__classe=classe).order_by('user__last_name','user__first_name')
	if form.is_valid():
		form.save()
		return redirect('ects_matieres',classe.pk)
	return render(request,'colleur/ectsmatieres.html',{'classe':classe,'matieresECTS':matieresECTS,'form':form})

@user_passes_test(is_colleur, login_url='accueil')
def ectsmatieremodif(request,id_matiere):
	"""Renvoie la vue de la page de modification des matières ects de la classe"""
	matiere = get_object_or_404(MatiereECTS,pk=id_matiere)
	if not is_profprincipal(request.user,matiere.classe):
		return HttpResponseForbidden("Accès non autorisé")
	form = MatiereECTSForm(request.POST or None,instance=matiere)
	form.fields['profs'].queryset=Colleur.objects.filter(classes=matiere.classe,colleurprof__classe=matiere.classe).order_by('user__last_name','user__first_name')
	if form.is_valid():
		form.save()
		return redirect('ects_matieres',matiere.classe.pk)
	return render(request,'colleur/ectsmatieremodif.html',{'matiere':matiere,'form':form})

@user_passes_test(is_colleur, login_url='accueil')
def ectsmatieresuppr(request,id_matiere):
	"""Supprime la matière ects dont l'id est id_matiere puis renvoie la page des matières ECTS"""
	matiere = get_object_or_404(MatiereECTS,pk=id_matiere)
	if not is_profprincipal(request.user,matiere.classe):
		return HttpResponseForbidden("Accès non autorisé")
	if not is_profprincipal(request.user,matiere.classe):
		return HttpResponseForbidden("Accès non autorisé")
	try:
		matiere.delete()
	except Exception:
		messages.error(request,"Impossible de l'effacer (des élèves y ont des notes)")
	return redirect('ects_matieres',matiere.classe.pk)

@user_passes_test(is_colleur, login_url='accueil')
def ectsnotes(request,id_classe):
	"""Renvoie la vue de la page de gestion des matières ects de la classe"""
	classe = get_object_or_404(Classe,pk=id_classe)
	matieres = MatiereECTS.objects.filter(classe=classe,profs=request.user.colleur).order_by('nom','precision')
	nbmatieres= matieres.count()
	if not matieres.exists():
		return HttpResponseForbidden("Vous n'êtes pas habilité à attribuer des crédits ECTS aux élèves de cette classe")
	listNotes = list("ABCDEF")
	listeNotes = NoteECTS.objects.note(classe,matieres)
	form = SelectEleveForm(classe,request.POST or None)
	if form.is_valid():
		for matiere in matieres:
			if str(matiere.pk) in request.POST:
				return redirect('ects_notes_modif',matiere.pk,"-".join([str(eleve.pk) for eleve in form.cleaned_data['eleve']]))
	nbsemestres=[]
	for matiere in matieres:
		nbsemestres.append(int(matiere.semestre1 is not None)+int(matiere.semestre2 is not None))
	return render(request,'colleur/ectsnotes.html',{'classe':classe,'matieres':matieres,'listeNotes':listeNotes,'listNotes':listNotes,'form':form,'nbsemestres':nbsemestres})

@user_passes_test(is_colleur, login_url='accueil')
def ectsnotesmodif(request,id_matiere,chaine_eleves):
	"""Renvoie la vue de la page de modification des notes ECTS des élèves sélectionnés, dont l'id fait partie de chaine_eleves, dans la matiere dont l"id est id_matiere"""
	matiere = get_object_or_404(MatiereECTS,pk=id_matiere,profs=request.user.colleur)
	listeEleves = Eleve.objects.filter(pk__in=[int(i) for i in chaine_eleves.split("-")],classe=matiere.classe).order_by('user__last_name','user__first_name').select_related('user')
	NoteEleveformset = formset_factory(NoteEleveForm,extra=0,max_num=listeEleves.count(),formset=NoteEleveFormSet)
	if request.method == 'POST':
		formset = NoteEleveformset(listeEleves,matiere,request.POST)
		if formset.is_valid():
			formset.save()
			return redirect('ects_notes',matiere.classe.pk)
	else:
		initial = NoteECTS.objects.noteEleves(matiere,listeEleves)
		formset = NoteEleveformset(listeEleves,matiere,initial=initial)
	nbsemestres = 1+int(matiere.semestre1 is not None)+int(matiere.semestre2 is not None)
	return render(request,'colleur/ectsnotesmodif.html',{'formset':formset,'matiere':matiere,'nbsemestres':nbsemestres})

@user_passes_test(is_colleur, login_url='accueil')
def ectscredits(request,id_classe,form=None):
	classe =get_object_or_404(Classe,pk=id_classe)
	if not is_profprincipal(request.user,classe):
		return HttpResponseForbidden("Accès non autorisé")
	eleves = Eleve.objects.filter(classe=classe).order_by('user__last_name','user__first_name')
	if not form:
		form=ECTSForm(classe,request.POST or None)
	return render(request,'colleur/ectscredits.html',{'classe':classe,'credits':NoteECTS.objects.credits(classe),'form':form})

@user_passes_test(is_colleur, login_url='accueil')
def ficheectspdf(request,id_eleve):
	eleve = get_object_or_404(Eleve,pk=id_eleve)
	if not is_profprincipal(request.user,eleve.classe):
		return HttpResponseForbidden("Accès non autorisé")
	if request.method=="POST":
		form=ECTSForm(eleve.classe,request.POST)
		if form.is_valid():
			datedujour = form.cleaned_data['date'].strftime('%d/%m/%Y')
			filiere,annee = form.cleaned_data['classe'].split("_")
			signataire = form.cleaned_data['signature']
			etoile = form.cleaned_data['etoile']
			tree=etree.parse(RESOURCES_ROOT+'classes.xml')
			classe=tree.xpath("/classes/classe[@nom='{}'][@annee='{}']".format(filiere,annee)).pop()
			domaine = classe.get("domaine")
			branche = classe.get("type").lower()
			precision = classe.get("precision")
		else:
			return ectscredits(request,eleve.classe.pk,form)
	else:
		datedujour = date.today().strftime('%d/%m/%Y')
		filiere = eleve.classe.nom
		signataire = 'Proviseur'
		etoile = False
		domaine = branche = precision = ""
	LIST_NOTES="ABCDEF"
	response = HttpResponse(content_type='application/pdf')
	nomfichier="ECTS_{}_{}_{}.pdf".format(eleve.classe.nom.upper(),eleve.user.first_name,eleve.user.last_name)
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	pdf = easyPdf()
	cm = pdf.format[0]/21
	pdf.marge_x = cm # 1cm de marge gauche/droite
	pdf.marge_y = 1.5*cm # 1,5cm de marge haut/bas
	I = Image(RESOURCES_ROOT+'marianne.jpg')
	I.drawHeight = 1.8*cm
	I.drawWidth = 3*cm
	pdf.y = pdf.format[1]-pdf.marge_y-1.8*cm
	I.drawOn(pdf,9*cm,pdf.y)
	pdf.y -= 10
	pdf.setFont("Times-Roman",7)
	pdf.drawCentredString(10.5*cm,pdf.y, "MINISTÈRE DE L'ÉDUCATION NATIONALE")
	pdf.y -= 8
	pdf.drawCentredString(10.5*cm,pdf.y, "DE l'ENSEIGNEMENT SUPÉRIEUR ET DE LA RECHERCHE")
	pdf.y -= 12
	pdf.setFont("Helvetica-Bold",11)
	pdf.drawCentredString(10.5*cm,pdf.y,"CLASSES PRÉPARATOIRES AUX GRANDES ÉCOLES")
	pdf.y -= 12
	pdf.setFont("Helvetica",11)
	pdf.drawCentredString(10.5*cm,pdf.y,"ANNEXE DESCRIPTIVE DE LA FORMATION")
	style=ParagraphStyle(name='normal',fontSize=9,leading=11,spaceAfter=5)
	styleResume=ParagraphStyle(name='resume',fontSize=9,leading=11,spaceAfter=0)
	styleTitre=ParagraphStyle(name='titre',fontSize=12,leading=13,fontName="Helvetica-Bold",borderColor='black',borderPadding=(0,0,2,0),borderWidth=1,backColor='#DDDDDD',spaceAfter=2)
	story=[]
	texte="1. Information sur l'étudiant"
	p=Paragraph(texte,styleTitre)
	story.append(p)
	texte="<b><i>1.1. Nom:</i></b> {}<br/><b><i>1.2. Prénom:</i></b> {}<br/><b><i>1.3. Date de Naissance:</i></b> {}<br/><b><i>1.4. N° INE:</i></b> {}".format(eleve.user.last_name.upper(),eleve.user.first_name.title(),"" if not eleve.ddn else eleve.ddn.strftime('%d/%m/%Y'),eleve.ine)
	p=Paragraph(texte,style)
	story.append(p)
	texte="2. Information sur la formation"
	p=Paragraph(texte,styleTitre)
	story.append(p)
	texte="""<b><i>2.1. Nom de la formation:</i></b><br/>
	Classe préparatoire {} {} {}<br/>
	<b><i>2.2. Principaux domaines d’étude:</i></b><br/>
	{}<br/>
	<b><i>2.3. Nom et statut de l’institution gérant la formation:</i></b><br/>
	Ministère de l’enseignement supérieur et de la recherche
	Classes préparatoires aux grandes écoles<br/>
	<b><i>2.4. Nom et statut de l’établissement dispensant la formation:</i></b><br/>
	{}<br/>
	<b><i>2.5. Langue de formation:</i></b> français""".format(branche,filiere,"("+precision+")" if precision else "",domaine,NOM_ADRESSE_ETABLISSEMENT.replace("\n","<br/>").replace("\r","<br/>").replace("<br/><br/>","<br/>"))
	p=Paragraph(texte,style)
	story.append(p)
	texte="3. Information sur le niveau de la formation"
	p=Paragraph(texte,styleTitre)
	story.append(p)
	texte="""<b><i>3.1. Niveau de la formation:</i></b><br/>
	Située au sein des études menant au grade de licence.<br/>
	Niveau bac + 2 / 120 crédits ECTS<br/>
	<b><i>3.2. Durée officielle du programme de formation:</i></b><br/>
	La durée du programme est de 2 ans.<br/>
	<b><i>3.3. Conditions d’accès:</i></b><br/>
	Entrée sélective après le baccalauréat s’effectuant dans le cadre d’une procédure nationale d’admission.<br/>
	Cf: <a href="http://www.admission-postbac.fr" color="blue">http://www.admission-postbac.fr</a>"""
	p=Paragraph(texte,style)
	story.append(p)
	texte="""4. Information sur les contenus et les résultats obtenus"""
	p=Paragraph(texte,styleTitre)
	story.append(p)
	texte="""<b><i>4.1. Organisation des études:</i></b><br/>
	Plein temps, contrôle continu écrit et oral<br/>
	<b><i>4.2. Exigences du programme:</i></b><br/>
	La formation dispensée a pour objet de donner aux étudiants une compréhension approfondie des disciplines enseignées et une appréhension de leurs caractéristiques générales. Elle prend en compte leurs évolutions, leurs applications et la préparation à des démarches de recherche.
	Elle est définie par des programmes nationaux.<br/>
	<b><i>4.3. Précisions sur le programme:</i></b><br/>
	Voir relevé au verso et catalogue de cours<br/>
	<b><i>4.4. Échelle d’évaluation:</i></b><br/>
	L’évaluation prend en compte l’ensemble des travaux des étudiants. La qualité du travail, des résultats obtenus et des compétences acquises est exprimée par une mention conformément au tableau ci-dessous."""
	p=Paragraph(texte,styleResume)
	story.append(p)
	data = [["A","Très Bien","C","Assez Bien","E","Passable"],["B","Bien","D","Convenable","F","Insuffisant"]]
	LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),.2,(0,0,0))
										,('VALIGN',(0,0),(-1,-1),'MIDDLE')
										,('ALIGN',(0,0),(-1,-1),'CENTRE')
										,('FACE',(0,0),(-1,-1),'Helvetica')
										,('SIZE',(0,0),(-1,-1),8)
										,('BACKGROUND',(0,0),(-1,-1),(.9,.9,.9))])
	t=Table(data,colWidths=[.8*cm,2*cm,.8*cm,2*cm,.8*cm,2*cm],rowHeights=[12]*2)
	t.setStyle(LIST_STYLE)
	story.append(t)
	texte="""<b><i>4.5. Classification de la formation:</i></b><br/>
	Une mention globale, portant sur l’ensemble du parcours et s’exprimant dans la même échelle qu’en 4.4 figure à la fin du relevé."""
	p=Paragraph(texte,style)
	story.append(p)
	fl = Frame(cm, 1.5*cm, 9*cm, 23*cm , showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
	fl.addFromList(story,pdf)
	story=[]
	texte="5. Information sur la fonction de la qualification"
	p=Paragraph(texte,styleTitre)
	story.append(p)
	texte="""<b><i>5.1. Accès à un niveau d’études supérieur:</i></b><br/>
	Accès par concours aux grandes écoles.<br/>
	Accès, par validation de parcours, à tout type d’établissement d’enseignement supérieur.<br/>
	<b><i>5.2. Statut  professionnel (si applicable):</i></b><br/>
	Sans objet"""
	p=Paragraph(texte,style)
	story.append(p)
	texte="6. Informations complémentaires"
	p=Paragraph(texte,styleTitre)
	story.append(p)
	texte="""<b><i>6.1. Informations complémentaires:</i></b><br/>
	Catalogue des cours et arrêtés ministériels définissant les programmes consultables sur :<br/>
	<a href="http://www.enseignementsup-recherche.gouv.fr/" color="blue">http://www.enseignementsup-recherche.gouv.fr/</a><br/>
	<b><i>6.2. Autres sources d’information:</i></b><br/>
	Pour toute information sur le dispositif CPGE consulter :<br/>
	<a href="http://www.enseignementsup-recherche.gouv.fr/" color="blue">http://www.enseignementsup-recherche.gouv.fr/</a>"""
	p=Paragraph(texte,style)
	story.append(p)
	texte="7. Certification de l’attestation"
	p=Paragraph(texte,styleTitre)
	story.append(p)
	texte="""<b><i>7.1. Date:</i></b> {}<br/>
	<b><i>7.2. Signature:</i></b><br/><br/><br/><br/>
	<b><i>7.3. Fonction:</i></b> {}<br/>
	<b><i>7.4. Tampon ou cachet officiel:</i></b><br/><br/><br/><br/><br/><br/>""".format(datedujour,signataire)
	p=Paragraph(texte,style)
	story.append(p)
	texte="8. Informations sur le système national d’enseignement supérieur"
	p=Paragraph(texte,styleTitre)
	story.append(p)
	p=Paragraph("<br/> <br/>",style)
	story.append(p)
	data = [["8","D","","Université","",""],["7","D","","Université","",""],["6","D","","Université","",""],\
	["5","M","","Université ou grande école","",""],["4","M","","Université ou grande école","",""],["3","L","ATS","Université ou grande école","",""],\
	["2","L","STS-IUT","","Université","CPGE"],["1","L","STS-IUT","","Université","CPGE"],["0","Bac","Enseignement secondaire","","",""]]
	LIST_STYLE = TableStyle([('GRID',(0,0),(1,4),.8,(0,0,0))
								,('GRID',(3,0),(5,4),.8,(0,0,0))
								,('GRID',(0,5),(5,8),.8,(0,0,0))
								,('VALIGN',(0,0),(-1,-1),'MIDDLE')
								,('ALIGN',(0,0),(-1,-1),'CENTRE')
								,('FACE',(0,0),(-1,-1),'Helvetica-Bold')
								,('SIZE',(0,0),(-1,-1),8)
								,('BACKGROUND',(0,0),(-1,-1),(1,1,1))
								,('SPAN',(3,0),(5,0))
								,('SPAN',(3,1),(5,1))
								,('SPAN',(3,2),(5,2))
								,('SPAN',(3,3),(5,3))
								,('SPAN',(3,4),(5,4))
								,('SPAN',(3,5),(5,5))
								,('SPAN',(2,6),(3,6))
								,('SPAN',(2,7),(3,7))
								,('SPAN',(2,8),(5,8))
								,('BACKGROUND',(3,0),(5,2),'#FABF8F')
								,('BACKGROUND',(3,3),(5,4),'#FBD4B4')
								,('BACKGROUND',(2,5),(2,5),'#76923C')
								,('BACKGROUND',(3,5),(5,5),'#FDE9D9')
								,('BACKGROUND',(4,6),(4,7),'#FDE9D9')
								,('BACKGROUND',(2,6),(3,7),'#D6E3BC')
								,('BACKGROUND',(5,6),(5,7),'#FF9900')])
	t=Table(data,colWidths=[.84*cm,.91*cm,.75*cm,1.4*cm,2.5*cm,2.5*cm],rowHeights=[.8*cm]*9)
	t.setStyle(LIST_STYLE)
	story.append(t)
	fr = Frame(11*cm, 1.5*cm, 9*cm, 23*cm , showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
	fr.addFromList(story,pdf)
	pdf.showPage()
	pdf.y = pdf.format[1]-pdf.marge_y-12
	pdf.setFont('Helvetica-Bold',12)
	pdf.drawCentredString(10.5*cm,pdf.y,"RELEVÉ DE RÉSULTATS (classe {})".format(filiere + ('*' if etoile and eleve.classe.annee == 2 else '')))
	sem1,sem2 = NoteECTS.objects.notePDF(eleve)
	data=[["ENSEIGNEMENTS","Crédits ECTS","Mention"],["Premier semestre","",""]]
	sp=0 # variable qui va contenir la somme pondérée des notes en vue du calcul de la mention globale
	coeff = 0 # somme des coeffs pour vérifier si on en a 60 au total
	for note in sem1:
		data.append([note[0] + ("" if not note[1] else " ({})".format(note[1])),note[2],LIST_NOTES[note[4]]])
		sp+=note[2]*note[4]
		if note[4] !=5:
			coeff+=note[2]
	data.append(["Deuxième semestre","",""])
	for note in sem2:
		data.append([note[0] + ("" if not note[1] else " ({})".format(note[1])),note[3],LIST_NOTES[note[4]]])
		sp+=note[3]*note[4]
		coeff+=note[3]
	LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),.8,(0,0,0))
								,('SPAN',(0,1),(2,1))
								,('SPAN',(0,2+len(sem1)),(2,2+len(sem1)))
								,('FACE',(0,0),(-1,-1),'Helvetica-Bold')
								,('SIZE',(0,0),(-1,-1),8)
								,('SIZE',(0,1),(2,1),9)
								,('SIZE',(0,2+len(sem1)),(2,2+len(sem1)),9)
								,('SIZE',(0,0),(2,0),10)
								,('VALIGN',(0,0),(-1,-1),'MIDDLE')
								,('ALIGN',(0,2),(0,-1),'LEFT')
								,('ALIGN',(1,0),(2,-1),'CENTRE')
								,('ALIGN',(0,0),(2,1),'CENTRE')
								,('ALIGN',(0,2+len(sem1)),(2,2+len(sem1)),'CENTRE')
								,('BACKGROUND',(0,1),(2,1),'#DDDDDD')
								,('BACKGROUND',(0,2+len(sem1)),(2,2+len(sem1)),'#DDDDDD')])
	t=Table(data,colWidths=[13*cm,2.8*cm,2.5*cm],rowHeights=[.8*cm]*(3+len(sem1)+len(sem2)))
	t.setStyle(LIST_STYLE)
	w,h=t.wrapOn(pdf,0,0)
	pdf.y-=h+5
	pdf.x=(pdf.format[0]-w)/2
	t.drawOn(pdf,pdf.x,pdf.y)
	pdf.y-=20
	pdf.setFont('Helvetica-Bold',10)
	if coeff == 60:
		pdf.drawString(pdf.x,pdf.y,"Mention globale: {}".format(LIST_NOTES[int(sp/60+.5)]))
	else:
		pdf.setFillColor((1,0,0))
		pdf.drawString(pdf.x,pdf.y,"Pas de mention, il manque {} crédits".format(60-coeff))
		pdf.setFillColor((0,0,0))
	pdf.drawRightString(pdf.format[0]-pdf.x-15,pdf.y,"Cachet et signature")
	pdf.save()
	fichier = pdf.buffer.getvalue()
	pdf.buffer.close()
	response.write(fichier)
	return response


@user_passes_test(is_colleur, login_url='accueil')
def attestationectspdf(request,id_eleve):
	eleve = get_object_or_404(Eleve,pk=id_eleve)
	if not is_profprincipal(request.user,eleve.classe):
		return HttpResponseForbidden("Accès non autorisé")
	if request.method=="POST":
		form=ECTSForm(eleve.classe,request.POST)
		if form.is_valid():
			datedujour = form.cleaned_data['date'].strftime('%d/%m/%Y')
			filiere = form.cleaned_data['classe'].split("_")[0]
			signataire = form.cleaned_data['signature']
			annee = form.cleaned_data['anneescolaire']
			etoile = form.cleaned_data['etoile']
		else:
			return ectscredits(request,eleve.classe.pk,form)
	else:
		datedujour = date.today().strftime('%d/%m/%Y')
		filiere = eleve.classe.nom
		signataire = 'Proviseur'
		annee = date.today().year
		etoile = False
	annee = "{}-{}".format(int(annee)-1,annee)
	LIST_NOTES="ABCDEF"
	response = HttpResponse(content_type='application/pdf')
	nomfichier="ATTESTATION_{}_{}_{}.pdf".format(eleve.classe.nom.upper(),eleve.user.first_name,eleve.user.last_name)
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	pdf = easyPdf()
	cm = pdf.format[0]/21
	pdf.marge_x = cm # 1cm de marge gauche/droite
	pdf.marge_y = 1.5*cm # 1,5cm de marge haut/bas
	I = Image(MEDIA_ROOT+'../resources/marianne.jpg')
	I.drawHeight = 1.8*cm
	I.drawWidth = 3*cm
	pdf.y = pdf.format[1]-pdf.marge_y-1.8*cm
	I.drawOn(pdf,9*cm,pdf.y)
	pdf.y -= 10
	pdf.setFont("Times-Roman",7)
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "MINISTÈRE DE L'ÉDUCATION NATIONALE")
	pdf.y -= 8
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "DE l'ENSEIGNEMENT SUPÉRIEUR ET DE LA RECHERCHE")
	pdf.y -= 30
	pdf.setFont('Helvetica-Bold',14)
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "ATTESTATION DU PARCOURS DE FORMATION")
	pdf.y -= 30
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "EN")
	pdf.y -= 30
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "CLASSE PRÉPARATOIRE AUX GRANDES ÉCOLES")
	pdf.y -= 40
	pdf.setFont("Helvetica-Oblique",11)
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "Le recteur de l'académie de {}, Chancelier des universités,".format(ACADEMIE))
	pdf.y -= 15
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "atteste que")
	pdf.y -= 40
	pdf.setFont("Helvetica",12)
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "{}".format(eleve))
	pdf.y -= 50
	pdf.setFont("Helvetica",11)
	pdf.drawString(2*cm,pdf.y, "né(e) le {}".format(eleve.ddn.strftime('%d/%m/%Y')))
	pdf.y -= 15
	pdf.drawString(2*cm,pdf.y, "n° INE: {}".format(eleve.ine))
	pdf.y -= 50
	pdf.setFont("Helvetica-Oblique",11)
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "a accompli un parcours de formation dans la filière {}".format(filiere + ('*' if etoile and eleve.classe.annee==2 else '')))
	pdf.y -= 50
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "Valeur du parcours en crédits du système ECTS :")
	pdf.setFont("Helvetica-Bold",16)
	pdf.drawString(15*cm,pdf.y,"60")
	pdf.y -= 50
	pdf.setFont("Helvetica-Oblique",11)
	pdf.drawCentredString(pdf.format[0]/2,pdf.y, "Mention globale obtenue :")
	pdf.setFillColor((1,0,0))
	pdf.setFont("Helvetica-Bold",13)
	pdf.drawCentredString(13*cm,pdf.y, "ABCDEF"[NoteECTS.objects.moyenneECTS(eleve)])
	pdf.y -= 50
	pdf.setFillColor((0,0,0))
	pdf.setFont("Helvetica",11)
	pdf.drawString(2*cm,pdf.y,"Année académique: {}".format(annee))
	pdf.y -= 15
	pdf.drawString(2*cm,pdf.y,NOM_ETABLISSEMENT)
	pdf.y -= 30
	pdf.drawCentredString(pdf.format[0]/2,pdf.y,"Fait à {},".format(VILLE))
	pdf.y -= 15
	pdf.drawString(15*cm,pdf.y,"le {}".format(datedujour))
	pdf.y -= 15
	pdf.drawString(15*cm,pdf.y,"Pour le recteur,")
	pdf.y -= 15
	pdf.drawString(15*cm,pdf.y,"Le {}".format(signataire.lower()))
	pdf.setFont("Helvetica-Oblique",9)
	pdf.y=3*cm
	pdf.drawCentredString(pdf.format[0]/2,pdf.y,"Attestation délivrée en application des dispositions de l’article 8 du décret n° 94-1015")
	pdf.y-=12
	pdf.drawCentredString(pdf.format[0]/2,pdf.y,"du 23 novembre 1994 modifié par le décret n° 2007-692 du 3 mai 2007")
	pdf.y-=12
	pdf.drawCentredString(pdf.format[0]/2,pdf.y,"Le descriptif de la formation figure dans l’annexe jointe.")
	pdf.save()
	fichier = pdf.buffer.getvalue()
	pdf.buffer.close()
	response.write(fichier)
	return response


