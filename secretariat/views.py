#-*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from administrateur.forms import AdminConnexionForm
from colleur.forms import SemaineForm, ECTSForm
from secretariat.forms import MoisForm, RamassageForm, MatiereClasseSelectForm, MatiereClasseSemaineSelectForm
from accueil.models import Note, Semaine, Matiere, Etablissement, Colleur, Ramassage, Classe, Eleve, Groupe, Creneau, Colle, mois, NoteECTS
from django.db.models import Count
from datetime import date, timedelta
from django.http import Http404, HttpResponse
from django.db.models import Avg
from pdf.pdf import Pdf, easyPdf, creditsects, attestationects
from reportlab.platypus import Table, TableStyle
from unidecode import unidecode
from lxml import etree
from ecolle.settings import RESOURCES_ROOT
import csv

def is_secret(user):
	"""Renvoie True si l'utilisateur est le secrétariat, False sinon"""
	return user.is_authenticated() and user.username=="Secrétariat"

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
	try:
		classe = Classe.objects.get(pk=request.session['classe'])
		matiere = Matiere.objects.get(pk=request.session['matiere'])
		semin = Semaine.objects.get(pk=request.session['semin'])
		semax = Semaine.objects.get(pk=request.session['semax'])
	except Exception:
		classe=matiere=semin=semax=semaines=generateur=None
		form = MatiereClasseSemaineSelectForm()
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

def classe2resultat(matiere,classe,semin,semax):
	"""Renvoie les résultats de la classe classe, dans la matière matière entre le semaine semin et semax"""
	semaines = Semaine.objects.filter(semainenote__classe=classe,semainenote__matiere=matiere,lundi__range=(semin.lundi,semax.lundi)).distinct().order_by('lundi')
	yield semaines
	listeEleves = list(Eleve.objects.filter(classe=classe).select_related('user'))
	elevesdict = {eleve.pk:[eleve.user.first_name.title(),eleve.user.last_name.upper(),"",""] for eleve in listeEleves}
	moyennes = list(Note.objects.exclude(note__gt=20).filter(matiere=matiere,classe=classe).filter(semaine__lundi__range=[semin.lundi,semax.lundi]).values('eleve__id','eleve__user__first_name','eleve__user__last_name').annotate(Avg('note')).order_by('eleve__user__last_name','eleve__user__first_name'))
	moyennes.sort(key=lambda x:x['note__avg'],reverse=True)
	for i,x in enumerate(moyennes):
		x['rang']=i+1
	for i in range(len(moyennes)-1):
		if moyennes[i]['note__avg']-moyennes[i+1]['note__avg']<1e-6:
			moyennes[i+1]['rang']=moyennes[i]['rang']
	for moyenne in moyennes:
		elevesdict[moyenne['eleve__id']][2:]=[moyenne['note__avg'],moyenne['rang']]
	eleves = list(elevesdict.values())
	eleves.sort(key=lambda x:(x[1],x[0]))
	for elevemoy,eleve in zip(eleves,listeEleves):
		note=dict()
		note['eleve']=eleve
		note['moyenne']=elevemoy[2]
		note['rang']=elevemoy[3]
		note['semaine']=list()
		for semaine in semaines:
			note['semaine'].append(Note.objects.filter(eleve=eleve,matiere=matiere,semaine=semaine).values('note','colleur__user__first_name','colleur__user__last_name','commentaire'))
		yield note

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
	groupes = Groupe.objects.filter(classe=classe).values('nom','pk').annotate(nb=Count('groupeeleve'))
	nom_groupes = []
	eleves_groupes = list(Eleve.objects.filter(classe=classe,groupe__isnull=False).values('pk','user__first_name','user__last_name').order_by('groupe__nom','user__last_name','user__first_name'))
	for value in groupes:
		nom_groupes.append((value['pk'],(value['nom'],"; ".join(["{} {}".format(x['user__first_name'].title(),x['user__last_name'].upper()) for x in eleves_groupes[:value['nb']]]))))
		del eleves_groupes[:value['nb']]
	listegroupes = dict(nom_groupes)
	jours,creneaux,colles,semaines=Colle.objects.classe2colloscope(classe,semin,semax)
	return render(request,'secretariat/colloscope.html',
	{'semin':semin,'semax':semax,'form':form,'classe':classe,'jours':jours,'listegroupes':listegroupes,'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'classes':Classe.objects.all(),'dictColleurs':classe.dictColleurs(semin,semax)})

@user_passes_test(is_secret, login_url='login_secret')
def colloscopePdf(request,id_classe,id_semin,id_semax):
	"""Renvoie le fichier PDF du colloscope de la classe dont l'id est id_classe, entre les semaines d'id id_semin et id_semax"""
	classe=get_object_or_404(Classe,pk=id_classe)
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	return Pdf(classe,semin,semax)

@user_passes_test(is_secret, login_url='login_secret')
def recapitulatif(request):
	"""Renvoie la vue de la page de récapitulatif des heures de colle"""
	moisMin,moisMax=mois()
	form = MoisForm(moisMin,moisMax,request.POST or None)
	if form.is_valid():
		moisMin=form.cleaned_data['moisMin']
		moisMax=form.cleaned_data['moisMax']
	listeDecompte,effectifs=Ramassage.objects.decompte(moisMin,moisMax)
	return render(request,"secretariat/recapitulatif.html",{'form':form,'decompte':listeDecompte,'classes':Classe.objects.all(),'effectifs':effectifs})

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

@user_passes_test(is_secret, login_url='login_secret')
def ectscredits(request,id_classe,form=None):
	classe =get_object_or_404(Classe,pk=id_classe)
	eleves = Eleve.objects.filter(classe=classe).order_by('user__last_name','user__first_name')
	if not form:
		form=ECTSForm(classe,request.POST or None)
	total = [0]*5
	credits = NoteECTS.objects.credits(classe)
	for credit in credits:
		attest = 1
		if credit['ddn']:
			total[0]+=1
		else:
			attest = 0
		if credit['ine']:
			total[1]+=1
		else:
			attest = 0
		if credit['sem1'] == 30:
			total[2]+=1
		else:
			attest = 0
		if credit['sem2'] == 30:
			total[3]+=1
		else:
			attest = 0
		total[4] += attest			
	return render(request,'secretariat/ectscredits.html',{'classe':classe,'credits':credits,'form':form,'total':total,"nbeleves":eleves.order_by().count()})

@user_passes_test(is_secret, login_url='login_secret')
def ficheectspdf(request,id_eleve):
	eleve = get_object_or_404(Eleve,pk=id_eleve)
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
	return creditsects(datedujour,filiere,signataire,etoile,domaine,branche,precision,eleve)

@user_passes_test(is_secret, login_url='login_secret')
def attestationectspdf(request,id_eleve):
	eleve = get_object_or_404(Eleve,pk=id_eleve)
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
	return attestationects(datedujour,filiere,signataire,etoile,annee,eleve)

@user_passes_test(is_secret, login_url='login_secret')
def ficheectsclassepdf(request,id_classe):
	classe = get_object_or_404(Classe,pk=id_classe)
	if request.method=="POST":
		form=ECTSForm(classe,request.POST)
		if form.is_valid():
			datedujour = form.cleaned_data['date'].strftime('%d/%m/%Y')
			filiere,annee = form.cleaned_data['classe'].split("_")
			signataire = form.cleaned_data['signature']
			etoile = form.cleaned_data['etoile']
			tree=etree.parse(RESOURCES_ROOT+'classes.xml')
			classexml=tree.xpath("/classes/classe[@nom='{}'][@annee='{}']".format(filiere,annee)).pop()
			domaine = classexml.get("domaine")
			branche = classexml.get("type").lower()
			precision = classexml.get("precision")
		else:
			return ectscredits(request,classe.pk,form)
	else:
		datedujour = date.today().strftime('%d/%m/%Y')
		filiere = classe.nom
		signataire = 'Proviseur'
		etoile = False
		domaine = branche = precision = ""
	return creditsects(datedujour,filiere,signataire,etoile,domaine,branche,precision,None,classe)

@user_passes_test(is_secret, login_url='login_secret')
def attestationectsclassepdf(request,id_classe):
	classe = get_object_or_404(Classe,pk=id_classe)
	if request.method=="POST":
		form=ECTSForm(classe,request.POST)
		if form.is_valid():
			datedujour = form.cleaned_data['date'].strftime('%d/%m/%Y')
			filiere = form.cleaned_data['classe'].split("_")[0]
			signataire = form.cleaned_data['signature']
			annee = form.cleaned_data['anneescolaire']
			etoile = form.cleaned_data['etoile']
		else:
			return ectscredits(request,classe.pk,form)
	else:
		datedujour = date.today().strftime('%d/%m/%Y')
		filiere = classe.nom
		signataire = 'Proviseur'
		annee = date.today().year
		etoile = False
	annee = "{}-{}".format(int(annee)-1,annee)
	return attestationects(datedujour,filiere,signataire,etoile,annee,None,classe)