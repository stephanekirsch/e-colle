#-*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from administrateur.forms import AdminConnexionForm
from colleur.forms import SemaineForm
from secretariat.forms import MoisForm, RamassageForm, MatiereClasseSelectForm, MatiereClasseSemaineSelectForm
from accueil.models import Note, Semaine, Matiere, Etablissement, Colleur, Ramassage, Classe, Eleve, Groupe, Creneau, Colle, mois
from django.db.models import Count
from datetime import date, timedelta
from django.http import Http404, HttpResponse
from django.db.models import Avg
from pdf.pdf import easyPdf, Pdf
from reportlab.platypus import Table, TableStyle
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
	listeDecompte,effectifs=ramassage2decompte(moisMin,moisMax)
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
	listeDecompte,effectifs=ramassage2decompte(debut,fin)
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
		data[ligneMat][0]=matiere.nom.title()
		if nbEtabs>1:
			LIST_STYLE.add('SPAN',(0,ligneMat),(0,min(ligneMat+nbEtabs-1,23)))
		ligneMat+=nbEtabs
		for etablissement, listeGrades, nbGrades in listeEtabs:
			data[ligneEtab][1]=etablissement.nom.title()
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
						data[ligneColleur][i+4]="{}h{}0".format(decomptes[i]*matiere.temps//60,(decomptes[i]*matiere.temps%60)//10)
					ligneColleur+=1
					if ligneColleur==24: # si le tableau prend toute une page, on termine la page et on recommence un autre tableau
						t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel]+[largeurcel]*len(effectifs),rowHeights=min((1+nbKolleurs),24)*[hauteurcel])
						t.setStyle(LIST_STYLE)
						w,h=t.wrapOn(pdf,0,0)
						t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
						pdf.finDePage()
						# on redémarre sur une nouvelle page
						pdf.debutDePage()
						nbKolleurs-=23
						data = [["Matière","Établissement","Grade","Colleur"]+["{}è. ann.\n{}".format(annee,effectif) for annee,effectif in effectifs]]+[[""]*(4+len(effectifs)) for i in range(min(23,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
						ligneEtab-=23
						ligneGrade-=23
						ligneMat-=23
						ligneColleur=1
						if ligneMat>1:
							data[1][0]=matiere.nom.title()
							if ligneMat>2:
								LIST_STYLE.add('SPAN',(0,1),(0,min(ligneMat-1,23)))
							if ligneEtab>1:
								data[1][1]=etablissement.nom.title()
								if ligneEtab>2:
									LIST_STYLE.add('SPAN',(1,1),(1,min(ligneEtab-1,23)))
								if ligneGrade>1:
									data[1][2]=grade
									if ligneGrade>2:
										LIST_STYLE.add('SPAN',(2,1),(2,min(ligneGrade-1,23)))
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

def ramassage2decompte(moisMin,moisMax):
	"""Renvoie la liste des colleurs avec leur nombre d'heures de colle entre les mois moisMin et moisMax, trié par année/effectif de classe"""
	LISTE_GRADES=["inconnu","certifié","bi-admissible","agrégé","chaire sup"]
	matieres=Matiere.objects.filter(note__date_colle__range=(moisMin,moisMax)).distinct()
	listeDecompte=list()
	effectif_classe = [False]*6
	plage = [(0,19),(20,35),(36,100)]
	classes = Classe.objects.annotate(eleve_compte=Count('classeeleve'))
	for classe in classes:
		effectif_classe[int(20<=classe.eleve_compte<=35)+2*int(35<classe.eleve_compte)+3*classe.annee-3]=True
	nb_decompte = sum([int(value) for value in effectif_classe])
	for matiere in matieres:
		etablissements=Etablissement.objects.filter(colleur__matieres=matiere,colleur__note__date_colle__range=(moisMin,moisMax)).distinct().annotate(Count('colleur__id'))
		listeEtablissements=list()
		nbEtabs=0
		for etablissement in etablissements:
			grades=Etablissement.objects.filter(colleur__matieres=matiere,colleur__note__date_colle__range=(moisMin,moisMax),colleur__etablissement=etablissement).values('colleur__grade').distinct()
			listeGrades=list()
			nbGrades=0
			for grade in grades:
				colleurs=Colleur.objects.filter(matieres=matiere,note__date_colle__range=(moisMin,moisMax),grade=grade['colleur__grade'],etablissement=etablissement).distinct()
				listeColleurs=list()
				nbColleurs=0
				for colleur in colleurs:
					indice=0
					decompte=[0]*nb_decompte
					for i,boolean in enumerate(effectif_classe):
						if boolean:
							decompte[indice]=Note.objects.filter(classe__annee=1+i//3,colleur=colleur,matiere=matiere,date_colle__range=(moisMin,moisMax)).annotate(eleve_compte=Count('classe__classeeleve')).filter(eleve_compte__range=plage[i%3]).count()
							indice+=1
					if sum(decompte)>0:
						nbColleurs+=1
						listeColleurs.append((colleur,decompte))
				nbGrades+=nbColleurs
				if nbColleurs>0:
					listeGrades.append((LISTE_GRADES[grade['colleur__grade']],listeColleurs,nbColleurs))
			nbEtabs+=nbGrades
			if nbGrades>0:
				listeEtablissements.append((etablissement,listeGrades,nbGrades))
		if nbEtabs>0:
			listeDecompte.append((matiere,listeEtablissements,nbEtabs))
	effectifs= list(zip([1]*3+[2]*3,["eff<20","20≤eff≤35","eff>35"]*2))
	effectifs = [x for x,boolean in zip(effectifs,effectif_classe) if boolean]
	return listeDecompte,effectifs

