#-*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import user_passes_test
from administrateur.forms import AdminConnexionForm
from colleur.forms import ECTSForm
from secretariat.forms import MoisForm, RamassageForm, MatiereClasseSemaineSelectForm
from accueil.models import Config, Note, Semaine, Matiere, Colleur, Ramassage, Classe, Eleve, Groupe, Creneau, mois, NoteECTS
from mixte.mixte import mixtegroupe, mixtegroupesuppr, mixtegroupemodif, mixtecolloscope,mixtecolloscopemodif, mixtecreneaudupli, mixtecreneausuppr, mixteajaxcompat, mixteajaxcolloscope, mixteajaxcolloscopeeleve, mixteajaxmajcolleur, mixteajaxcolloscopeeffacer, mixteajaxcolloscopemulti, mixteajaxcolloscopemulticonfirm
from django.http import Http404, HttpResponse,  HttpResponseForbidden
from pdf.pdf import Pdf, easyPdf, creditsects, attestationects
from reportlab.platypus import Table, TableStyle
from datetime import timedelta
import csv

def is_secret(user):
	"""Renvoie True si l'utilisateur est le secrétariat, False sinon"""
	return user.is_authenticated and user.username=="Secrétariat"

def is_secret_ects(user):
	"""Renvoie True si l'utilisateur est le secrétariat et ECTS activé, False sinon"""
	return is_secret(user) and Config.objects.get_config().ects

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
	semaines=list(Semaine.objects.all())
	try:
		semin,semax=semaines[0],semaines[-1]
	except Exception:
		raise Http404
	return colloscope2(request,id_classe,semin.pk,semax.pk)

@user_passes_test(is_secret, login_url='login_secret')
def colloscope2(request,id_classe,id_semin,id_semax):
	"""Renvoie la vue de la page du colloscope de la classe dont l'id est id_classe entre les semaines dont l'id est id_semin et id_semax"""
	classe=get_object_or_404(Classe,pk=id_classe)
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	isprof = Config.objects.get_config().modif_secret_col
	return mixtecolloscope(request,classe,semin,semax,isprof)

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
	if not Config.objects.get_config().modif_secret_col:
		return HttpResponseForbidden("Accès non autorisé")
	classe=get_object_or_404(Classe,pk=id_classe)
	semin=get_object_or_404(Semaine,pk=id_semin)
	semax=get_object_or_404(Semaine,pk=id_semax)
	return mixtecolloscopemodif(request,classe,semin,semax,creneaumodif)
	
@user_passes_test(is_secret, login_url='accueil')
def creneauSuppr(request,id_creneau,id_semin,id_semax):
	"""Essaie de supprimer le créneau dont l'id est id_creneau puis redirige vers la page de modification du colloscope
	dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
	if not Config.objects.get_config().modif_secret_col:
		return HttpResponseForbidden("Accès non autorisé")
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	return mixtecreneausuppr(request,creneau,id_semin,id_semax)

@user_passes_test(is_secret, login_url='accueil')
def creneauModif(request,id_creneau,id_semin,id_semax):
	"""Renvoie la vue de la page de modification du creneau dont l'id est id_creneau"""
	if not Config.objects.get_config().modif_secret_col:
		return HttpResponseForbidden("Accès non autorisé")
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	return colloscopeModif(request,creneau.classe.pk,id_semin,id_semax,creneaumodif=creneau)

@user_passes_test(is_secret, login_url='accueil')
def creneauDupli(request,id_creneau,id_semin,id_semax):
	"""Renvoie la vue de la page de duplication du creneau dont l'id est id_creneau"""
	if not Config.objects.get_config().modif_secret_col:
		return HttpResponseForbidden("Accès non autorisé")
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	return mixtecreneaudupli(request.user,creneau,id_semin,id_semax)

@user_passes_test(is_secret, login_url='accueil')
def ajaxcompat(request,id_classe):
	"""Renvoie une chaîne de caractères récapitulant les incompatibilités du colloscope de la classe dont l'id est id_classe"""
	if not Config.objects.get_config().modif_secret_col:
		return HttpResponseForbidden("Accès non autorisé")
	classe=get_object_or_404(Classe,pk=id_classe)
	return mixteajaxcompat(classe)

@user_passes_test(is_secret, login_url='accueil')
def ajaxmajcolleur(request, id_matiere, id_classe):
	"""Renvoie la liste des colleurs de la classe dont l'id est id_classe et de la matière dont l'id est id_matiere, au format json"""
	if not Config.objects.get_config().modif_secret_col:
		return HttpResponseForbidden("Accès non autorisé")
	classe=get_object_or_404(Classe,pk=id_classe)
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	return mixteajaxmajcolleur(matiere,classe)
	

@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscope(request, id_matiere, id_colleur, id_groupe, id_semaine, id_creneau):
	"""Ajoute la colle propre au quintuplet (matière,colleur,groupe,semaine,créneau) et renvoie le username du colleur
	en effaçant au préalable toute colle déjà existante sur ce couple créneau/semaine"""
	if not Config.objects.get_config().modif_secret_col:
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
	if not Config.objects.get_config().modif_secret_col:
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
	if not Config.objects.get_config().modif_secret_col:
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
	if not Config.objects.get_config().modif_secret_col:
		return HttpResponseForbidden("Accès non autorisé")
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	colleur=get_object_or_404(Colleur,pk=id_colleur)
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	return mixteajaxcolloscopemulti(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation)
	
@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscopemulticonfirm(request, id_matiere, id_colleur, id_groupe, id_eleve, id_semaine, id_creneau, duree, frequence, permutation):
	"""ajoute les colles sur les couples créneau/semaine sur le créneau dont l'id est id_creneau
	et les semaines dont le numéro est compris entre celui de la semaine d'id id_semaine et ce dernier + duree
	et dont le numéro est congru à celui de la semaine d'id id_semaine modulo frequence, avec le colleur dont l'id est id_colleur
	le groupe démarre au groupe dont l'id est id_groupe puis va de permutation en permutation, et la matière dont l'id est id_matière"""
	if not Config.objects.get_config().modif_secret_col:
		return HttpResponseForbidden("Accès non autorisé")
	matiere=get_object_or_404(Matiere,pk=id_matiere)
	colleur=get_object_or_404(Colleur,pk=id_colleur)
	semaine=get_object_or_404(Semaine,pk=id_semaine)
	creneau=get_object_or_404(Creneau,pk=id_creneau)
	return mixteajaxcolloscopemulticonfirm(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation)

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
def ramassageCSV(request,id_ramassage):
	"""Renvoie le fichier CSV du ramassage par année/effectif correspondant au ramassage dont l'id est id_ramassage"""
	ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
	LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
	response = HttpResponse(content_type='text/csv')
	debut=ramassage.moisDebut
	fin=Ramassage.incremente_mois(ramassage.moisFin)-timedelta(days=1)
	listeDecompte,effectifs=Ramassage.objects.decompte(debut,fin)
	nomfichier="ramassage{}_{}-{}_{}.csv".format(debut.month,debut.year,fin.month,fin.year)
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	writer = csv.writer(response)
	writer.writerow(["Matière","Établissement","Grade","Colleur"]+["{}è. ann.  {}".format(annee,effectif) for annee,effectif in effectifs])
	for matiere, listeEtabs, nbEtabs in listeDecompte:
		for etablissement, listeGrades, nbGrades in listeEtabs:
			for grade, listeColleurs, nbColleurs in listeGrades:
				for colleur, decomptes in listeColleurs:
					writer.writerow([matiere.title(),'Inconnu' if not etablissement else etablissement.title(),
						grade, colleur] + ["{},{:02d}".format(decomptes[i]//60,(1+decomptes[i]%60*5)//3) for i in range(len(effectifs))])
	return response

@user_passes_test(is_secret, login_url='login_secret')
def ramassagePdf(request,id_ramassage):
	"""Renvoie le fichier PDF du ramassage par année/effectif correspondant au ramassage dont l'id est id_ramassage"""
	ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
	LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
	response = HttpResponse(content_type='application/pdf')
	debut=ramassage.moisDebut
	fin=Ramassage.incremente_mois(ramassage.moisFin)-timedelta(days=1)
	listeDecompte,effectifs=Ramassage.objects.decompte(debut,fin)
	nomfichier="ramassage{}_{}-{}_{}.pdf".format(debut.month,debut.year,fin.month,fin.year)
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	pdf = easyPdf(titre="Ramassage des colles de {} {} à {} {}".format(LISTE_MOIS[debut.month],debut.year,LISTE_MOIS[fin.month],fin.year),marge_x=30,marge_y=30)
	largeurcel=(pdf.format[0]-2*pdf.marge_x)/(9+len(effectifs))
	hauteurcel=30
	nbKolleurs=sum([z for x,y,z in listeDecompte])
	pdf.debutDePage()
	LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
										,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
										,('VALIGN',(0,0),(-1,-1),'MIDDLE')
										,('ALIGN',(0,0),(-1,-1),'CENTRE')
										,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
										,('SIZE',(0,0),(-1,-1),8)])
	data = [["Matière","Établissement","Grade","Colleur"]+["{}è. ann.\n{}".format(annee,effectif) for annee,effectif in effectifs]]+[[""]*(4+len(effectifs)) for i in range(min(23,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
	ligneMat=ligneEtab=ligneGrade=ligneColleur=1
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
						data[ligneColleur][i+4]="{},{:02d}h".format(decomptes[i]//60,(1+decomptes[i]%60*5)//3)
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
							if ligneEtab>1:
								data[1][1]='Inconnu' if not etablissement else etablissement.title()
								if ligneEtab>2:
									LIST_STYLE.add('SPAN',(1,1),(1,min(ligneEtab,23)))
								if ligneGrade>1:
									data[1][2]=grade
									if ligneGrade>2:
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
def ramassageCSVParClasse(request, id_ramassage, total):
	"""Renvoie le fichier CSV du ramassage par classe correspondant au ramassage dont l'id est id_ramassage
	si total vaut 1, les totaux par classe et matière sont calculés"""
	ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
	LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
	response = HttpResponse(content_type='text/csv')
	debut=ramassage.moisDebut
	fin=Ramassage.incremente_mois(ramassage.moisFin)-timedelta(days=1)
	listeClasses, classes = Ramassage.objects.decompteParClasse(debut,fin)
	nomfichier="ramassageCSVParclasse{}_{}-{}_{}.csv".format(debut.month,debut.year,fin.month,fin.year)
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	writer = csv.writer(response)
	writer.writerow(["Classe","Matière","Établissement","Grade","Colleur","heures"])
	total = int(total)
	for classe, listeClasse in zip(classes,listeClasses):
		totalclasse = 0
		for matiere, listeEtabs, nbEtabs in listeClasse:
			totalmatiere = 0
			for etablissement, listeGrades, nbGrades in listeEtabs:
				for grade, listeColleurs, nbColleurs in listeGrades:
					for colleur, decomptes in listeColleurs:
						writer.writerow([classe.nom, matiere.title(),'Inconnu' if not etablissement else etablissement.title(),
						grade, colleur,"{},{:02d}".format(decomptes//60,(1+decomptes%60*5)//3)])
						totalmatiere += decomptes
			totalclasse += totalmatiere
			if total:
				print(total)
				writer.writerow([""]*6)
				writer.writerow([classe.nom, "total {}".format(matiere.title()), "", "", "", "{},{:02d}".format(totalmatiere//60,(1+totalmatiere%60*5)//3)])
				writer.writerow([""]*6)
		if total:
			writer.writerow(["total {}".format(classe.nom), "", "", "", "", "{},{:02d}".format(totalclasse//60,(1+totalclasse%60*5)//3)])
			writer.writerow([""]*6)
			writer.writerow([""]*6)
	return response


@user_passes_test(is_secret, login_url='login_secret')
def ramassagePdfParClasse(request,id_ramassage,total):
	"""Renvoie le fichier PDF du ramassage par classe correspondant au ramassage dont l'id est id_ramassage
	si total vaut 1, les totaux par classe et matière sont calculés"""
	ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
	LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
	response = HttpResponse(content_type='application/pdf')
	debut=ramassage.moisDebut
	fin=Ramassage.incremente_mois(ramassage.moisFin)-timedelta(days=1)
	listeClasses, classes = Ramassage.objects.decompteParClasse(debut,fin)
	nomfichier="ramassagePdfParclasse{}_{}-{}_{}.pdf".format(debut.month,debut.year,fin.month,fin.year)
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	pdf = easyPdf(titre="Ramassage des colles de {} {} à {} {}".format(LISTE_MOIS[debut.month],debut.year,LISTE_MOIS[fin.month],fin.year),marge_x=30,marge_y=30)
	largeurcel=(pdf.format[0]-2*pdf.marge_x)/10
	hauteurcel=30
	total=int(total)
	for classe, listeClasse in zip(classes,listeClasses):
		totalclasse = 0
		pdf.debutDePage(soustitre = classe.nom)
		nbKolleurs=sum([z for x,y,z in listeClasse])
		if total:
			nbKolleurs += 1 + len([x for x,y,z in listeClasse]) # on rajoute le nombre de matières et 1 pour la classe
		LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
											,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
											,('VALIGN',(0,0),(-1,-1),'MIDDLE')
											,('ALIGN',(0,0),(-1,-1),'CENTRE')
											,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
											,('SIZE',(0,0),(-1,-1),8)])
		data = [["Matière","Établissement","Grade","Colleur", "heures"]]+[[""]*5 for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
		ligneMat=ligneEtab=ligneGrade=ligneColleur=1
		for matiere, listeEtabs, nbEtabs in listeClasse:
			totalmatiere = 0
			data[ligneMat][0]=matiere.title()
			if nbEtabs>1:
				LIST_STYLE.add('SPAN',(0,ligneMat),(0,min(ligneMat+nbEtabs-1,22)))
			ligneMat+=nbEtabs
			for etablissement, listeGrades, nbGrades in listeEtabs:
				data[ligneEtab][1]='Inconnu' if not etablissement else etablissement.title()
				if nbGrades>1:
					LIST_STYLE.add('SPAN',(1,ligneEtab),(1,min(ligneEtab+nbGrades-1,22)))
				ligneEtab+=nbGrades
				for grade, listeColleurs, nbColleurs in listeGrades:
					data[ligneGrade][2]=grade
					if nbColleurs>1:
						LIST_STYLE.add('SPAN',(2,ligneGrade),(2,min(ligneGrade+nbColleurs-1,22)))
					ligneGrade+=nbColleurs
					for colleur, decomptes in listeColleurs:
						print(ligneColleur)
						totalmatiere += decomptes
						data[ligneColleur][3]=colleur
						data[ligneColleur][4]="{},{:02d}h".format(decomptes//60,(1+decomptes%60*5)//3)
						ligneColleur+=1
						if ligneColleur==23 and nbKolleurs>22: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
							t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel, largeurcel],rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
							t.setStyle(LIST_STYLE)
							w,h=t.wrapOn(pdf,0,0)
							t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
							pdf.finDePage()
							# on redémarre sur une nouvelle page
							pdf.debutDePage(soustitre = classe.nom)
							LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
											,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
											,('VALIGN',(0,0),(-1,-1),'MIDDLE')
											,('ALIGN',(0,0),(-1,-1),'CENTRE')
											,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
											,('SIZE',(0,0),(-1,-1),8)])
							nbKolleurs-=22
							data = [["Matière","Établissement","Grade","Colleur", "heures"]]+[[""]*5 for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
							ligneEtab-=22
							ligneGrade-=22
							ligneMat-=22
							ligneColleur=1
							if ligneMat>1:
								data[1][0]=matiere.title()
								if ligneMat>2:
									LIST_STYLE.add('SPAN',(0,1),(0,min(ligneMat-1,22)))
								if ligneEtab>1:
									data[1][1]='Inconnu' if not etablissement else etablissement.title()
									if ligneEtab>2:
										LIST_STYLE.add('SPAN',(1,1),(1,min(ligneEtab,22)))
									if ligneGrade>1:
										data[1][2]=grade
										if ligneGrade>2:
											LIST_STYLE.add('SPAN',(2,1),(2,min(ligneGrade,22)))
			# fin matière
			totalclasse += totalmatiere
			if total:
				LIST_STYLE.add('SPAN',(0,ligneColleur),(3,ligneColleur))
				LIST_STYLE.add('BACKGROUND',(0,ligneColleur),(-1,ligneColleur),(.8,.8,.8))
				data[ligneColleur] = ["total {}".format(matiere.title()),"","","","{},{:02d}h".format(totalmatiere//60,(1+totalmatiere%60*5)//3)]
				ligneEtab+=1
				ligneGrade+=1
				ligneMat+=1
				ligneColleur+=1
				if ligneColleur==23 and nbKolleurs>22: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
					t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel, largeurcel],rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
					t.setStyle(LIST_STYLE)
					w,h=t.wrapOn(pdf,0,0)
					t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
					pdf.finDePage()
					# on redémarre sur une nouvelle page
					pdf.debutDePage(soustitre = classe.nom)
					LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
									,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
									,('VALIGN',(0,0),(-1,-1),'MIDDLE')
									,('ALIGN',(0,0),(-1,-1),'CENTRE')
									,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
									,('SIZE',(0,0),(-1,-1),8)])
					nbKolleurs-=22
					data = [["Matière","Établissement","Grade","Colleur", "heures"]]+[[""]*5 for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
					ligneEtab-=22
					ligneGrade-=22
					ligneMat-=22
					ligneColleur=1
		# fin classe
		if total:
			LIST_STYLE.add('SPAN',(0,ligneColleur),(3,ligneColleur))
			LIST_STYLE.add('BACKGROUND',(0,ligneColleur),(-1,ligneColleur),(.7,.7,.7))
			data[ligneColleur] = ["total {}".format(classe.nom),"","","","{},{:02d}h".format(totalclasse//60,(1+totalclasse%60*5)//3)]
			ligneEtab+=1
			ligneGrade+=1
			ligneMat+=1
			ligneColleur+=1
		t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel,largeurcel],rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
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
	if not Config.objects.get_config().modif_secret_groupe:
		return HttpResponseForbidden("Accès non autorisé")
	classe=get_object_or_404(Classe,pk=id_classe)
	groupes = Groupe.objects.filter(classe=classe).prefetch_related('groupeeleve__user')
	return mixtegroupe(request,classe,groupes)

@user_passes_test(is_secret, login_url='accueil')
def groupeSuppr(request,id_groupe):
	"""Essaie de supprimer la groupe dont l'id est id_groupe, puis redirige vers la page de gestion des groupes"""
	if not Config.objects.get_config().modif_secret_groupe:
		return HttpResponseForbidden("Accès non autorisé")
	groupe=get_object_or_404(Groupe,pk=id_groupe)
	return mixtegroupesuppr(request.user,groupe)

@user_passes_test(is_secret, login_url='accueil')
def groupeModif(request,id_groupe):
	"""Renvoie la vue de la page de modification du groupe dont l'id est id_groupe"""
	if not Config.objects.get_config().modif_secret_groupe:
		return HttpResponseForbidden("Accès non autorisé")
	groupe=get_object_or_404(Groupe,pk=id_groupe)
	return mixtegroupemodif(request,groupe)

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
	form = ECTSForm(eleve.classe, request.POST)
	if request.method=="POST":
		if form.is_valid():
			return creditsects(form,eleve,eleve.classe)
		else:
			return ectscredits(request,eleve.classe.pk,form)
	else:
		raise Http404

@user_passes_test(is_secret_ects, login_url='login_secret')
def attestationectspdf(request,id_eleve):
	eleve = get_object_or_404(Eleve,pk=id_eleve)
	form = ECTSForm(eleve.classe, request.POST)
	if request.method=="POST":
		if form.is_valid():
			return attestationects(form,eleve,eleve.classe)
		else:
			return ectscredits(request,eleve.classe.pk,form)
	else:
		raise Http404

@user_passes_test(is_secret_ects, login_url='login_secret')
def ficheectsclassepdf(request,id_classe):
	classe = get_object_or_404(Classe,pk=id_classe)
	form = ECTSForm(classe, request.POST)
	if request.method=="POST":
		if form.is_valid():
			return creditsects(form,None,classe)
		else:
			return ectscredits(request,classe.pk,form)
	else:
		raise Http404

@user_passes_test(is_secret_ects, login_url='login_secret')
def attestationectsclassepdf(request,id_classe):
	classe = get_object_or_404(Classe,pk=id_classe)
	form = ECTSForm(classe, request.POST)
	if request.method=="POST":
		if form.is_valid():
			return attestationects(form,None,classe)
		else:
			return ectscredits(request,classe.pk,form)
	else:
		raise Http404
