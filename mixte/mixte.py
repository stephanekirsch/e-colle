#-*- coding: utf-8 -*-
from accueil.models import Groupe, JourFerie, Colle, Semaine, Eleve, Colleur, Creneau, Ramassage
from datetime import timedelta
from django.db.models import Count, F, Min, Max
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from colleur.forms import SemaineForm, CreneauForm, ColleForm, GroupeForm
from pdf.pdf import easyPdf
from reportlab.platypus import Table, TableStyle
import json

def mixtegroupe(request,classe,groupes):
	form = GroupeForm(classe,None,request.POST or None)
	if form.is_valid():
		form.save()
		return redirect('groupe_colleur' if request.user.colleur else 'groupe_secret', classe.pk)
	return render(request,"mixte/groupe.html",{'classe':classe,'groupes':groupes,'form':form,'hide':json.dumps([(eleve.id,"" if not eleve.lv1 else eleve.lv1.pk,"" if not eleve.lv2 else eleve.lv2.pk) for eleve in form.fields['eleve0'].queryset])})

def mixtegroupesuppr(request,groupe):
	try:
		groupe.delete()
	except Exception:
		messages.error(request,"Impossible de supprimer le groupe car il est présent dans le colloscope")
	return redirect('groupe_colleur' if request.user.colleur else 'groupe_secret',groupe.classe.pk)

def mixtegroupemodif(request,groupe):
	initial = {"eleve{}".format(i):eleve for i,eleve in enumerate(groupe.groupeeleve.all())}
	initial['nom']=groupe.nom
	form = GroupeForm(groupe.classe,groupe,request.POST or None, initial=initial)
	if form.is_valid():
		form.save()
		return redirect('groupe_colleur' if request.user.colleur else 'groupe_secret', groupe.classe.pk)
	return render(request,'mixte/groupeModif.html',{'form':form,'groupe':groupe,'hide':json.dumps([(eleve.id,"" if not eleve.lv1 else eleve.lv1.pk,"" if not eleve.lv2 else eleve.lv2.pk) for eleve in form.fields['eleve0'].queryset])})

def mixtecolloscope(request,classe,semin,semax,isprof):
	form=SemaineForm(request.POST or None,initial={'semin':semin,'semax':semax})
	if form.is_valid():
		return redirect('colloscope2_colleur' if request.user.colleur else 'colloscope2_secret',classe.pk,form.cleaned_data['semin'].pk,form.cleaned_data['semax'].pk)
	jours,creneaux,colles,semaines=Colle.objects.classe2colloscope(classe,semin,semax)
	return render(request,'mixte/colloscope.html',
	{'semin':semin,'semax':semax,'form':form,'isprof':isprof,'classe':classe,'jours':jours,'dictgroupes':classe.dictGroupes(),'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'dictColleurs':classe.dictColleurs(semin,semax)})

def mixtecolloscopemodif(request,classe,semin,semax,creneaumodif):
	form1=SemaineForm(request.POST or None,initial={'semin':semin,'semax':semax})
	if form1.is_valid():
		return redirect('colloscopemodif_colleur' if request.user.colleur else 'colloscopemodif_secret',classe.pk,form1.cleaned_data['semin'].pk,form1.cleaned_data['semax'].pk)
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
		return redirect('colloscopemodif_colleur' if request.user.colleur else 'colloscopemodif_secret',classe.pk,semin.pk,semax.pk)
	matieres = list(classe.matieres.filter(colleur__classes=classe, colleur__user__is_active = True).order_by('nom','lv','temps').values_list('pk','nom','couleur','temps').annotate(nb=Count("colleur")))
	colleurs = list(Colleur.objects.exclude(matieres = None).filter(classes=classe, matieres__in = classe.matieres.all(), user__is_active = True).values_list('pk','user__first_name','user__last_name').order_by("matieres__nom", "matieres__lv", "matieres__temps", "user__last_name", "user__first_name"))
	groupes = Groupe.objects.filter(classe=classe)
	matieresgroupes = [[groupe for groupe in groupes if groupe.haslangue(matiere)] for matiere in classe.matieres.filter(colleur__classes=classe).order_by("nom", "lv", "temps")]
	listeColleurs = []
	for x in matieres:
		listeColleurs.append(colleurs[:x[4]])
		del colleurs[:x[4]]
	largeur=str(650+42*creneaux.count())+'px'
	hauteur=str(27*(len(matieres)+classe.classeeleve.count()+Colleur.objects.filter(classes=classe).count()))+'px'
	return render(request,'mixte/colloscopeModif.html',
	{'semin':semin,'semax':semax,'form1':form1,'form':form,'form2':form2,'largeur':largeur,'hauteur':hauteur,'groupes':groupes,'matieres':zip(matieres,listeColleurs,matieresgroupes),'creneau':creneaumodif\
	,'classe':classe,'jours':jours,'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'dictColleurs':classe.dictColleurs(semin,semax),'dictGroupes':json.dumps(classe.dictGroupes(False)),'dictEleves':json.dumps(classe.dictElevespk())})

def mixtecreneausuppr(request,creneau,id_semin,id_semax):
	try:
		creneau.delete()
	except Exception:
		messages.error(request,"Vous ne pouvez pas effacer un créneau qui contient des colles")
	return redirect('colloscopemodif_colleur' if request.user.colleur else 'colloscopemodif_secret',creneau.classe.pk,id_semin,id_semax)

def mixtecreneaudupli(user,creneau,id_semin,id_semax):
	creneau.pk=None
	creneau.salle=None
	creneau.save()
	return redirect('colloscopemodif_colleur' if user.colleur else 'colloscopemodif_secret',creneau.classe.pk,id_semin,id_semax)

def mixteajaxcompat(classe):
	LISTE_JOURS=['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
	colleurs = Colle.objects.filter(groupe__classe=classe).values('colleur__user__first_name','colleur__user__last_name','semaine__numero','creneau__jour','creneau__heure').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','creneau__jour','creneau__heure','colleur__user__last_name','colleur__user__first_name')
	colleurs="\n".join(["le colleur {} {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['colleur__user__first_name'].title(),valeur['colleur__user__last_name'].upper(),valeur['nbcolles'],valeur['semaine__numero'],LISTE_JOURS[valeur['creneau__jour']],valeur['creneau__heure']//60,valeur['creneau__heure']%60) for valeur in colleurs])
	eleves = Colle.objects.filter(groupe__classe=classe).values('groupe__nom','semaine__numero','creneau__jour','creneau__heure').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','creneau__jour','creneau__heure','groupe__nom')
	eleves="\n".join(["le groupe {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['groupe__nom'],valeur['nbcolles'],valeur['semaine__numero'],LISTE_JOURS[valeur['creneau__jour']],valeur['creneau__heure']//60,valeur['creneau__heure']%60) for valeur in eleves])
	elevesolo = Colle.objects.compatEleve(classe.pk)
	elevesolo = "\n".join(["l'élève {} {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['prenom'].title(),valeur['nom'].upper(),valeur['nbcolles'],valeur['numero'],LISTE_JOURS[valeur['jour']],valeur['heure']//60,valeur['heure']%60) for valeur in elevesolo])
	groupes=Colle.objects.filter(groupe__classe=classe).values('groupe__nom','matiere__nom','semaine__numero').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','matiere__nom','groupe__nom')
	groupes = "\n".join(["le groupe {} a {} colles de {} en semaine {}".format(valeur['groupe__nom'],valeur['nbcolles'],valeur['matiere__nom'].title(),valeur['semaine__numero']) for valeur in groupes])
	reponse=colleurs+"\n\n"*int(bool(colleurs))+eleves+"\n\n"*int(bool(eleves))+elevesolo+"\n\n"*int(bool(elevesolo))+groupes
	if not reponse:
		reponse="aucune incompatibilité dans le colloscope"
	return HttpResponse(reponse)

def mixteajaxcolloscope(matiere,colleur,groupe,semaine,creneau):
	Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
	feries = [dic['date'] for dic in JourFerie.objects.all().values('date')]
	if semaine.lundi+timedelta(days=creneau.jour) in feries:
		return HttpResponse("jour férié")
	Colle(semaine=semaine,creneau=creneau,groupe=groupe,colleur=colleur,matiere=matiere).save()
	return HttpResponse("{}:{}".format(creneau.classe.dictColleurs()[colleur.pk],groupe.nom))

def mixteajaxcolloscopeeleve(matiere,colleur, id_eleve,semaine,creneau,login):
	try:
		eleve = Eleve.objects.get(pk=id_eleve)
	except Exception:
		if matiere.temps == 60:
			eleve = None
		else:
			raise Http404
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

def mixteajaxcolloscopeeffacer(semaine,creneau):
	Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
	return HttpResponse("efface")

def mixteajaxmajcolleur(matiere,classe):
	colleurs=Colleur.objects.filter(user__is_active=True,matieres=matiere,classes=classe).values('id','user__first_name','user__last_name','user__username').order_by('user__first_name','user__last_name')
	colleurs=[{'nom': value['user__first_name'].title()+" "+value['user__last_name'].upper()+' ('+classe.dictColleurs()[value['id']]+')','id':value['id']} for value in colleurs]
	return HttpResponse(json.dumps([matiere.temps]+colleurs))

def mixteajaxcolloscopemulti(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation):
	frequence = int(frequence)
	modulo = int(semaine.numero)%frequence
	ecrase = Colle.objects.filter(creneau = creneau,semaine__numero__range=(semaine.numero,semaine.numero+int(duree)-1)).annotate(semaine_mod = F('semaine__numero') % frequence).filter(semaine_mod=modulo).count()
	nbferies = JourFerie.objects.recupFerie(creneau.jour,semaine,duree,frequence,modulo)
	if not(ecrase and nbferies[0]):
		return HttpResponse("{}_{}".format(ecrase,nbferies[0]))
	else:
		return mixteajaxcolloscopemulticonfirm(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation)

def mixteajaxcolloscopemulticonfirm(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation):
	groupe=None if matiere.temps!=20 else get_object_or_404(Groupe,pk=id_groupe)
	eleve=None if matiere.temps!=30 else get_object_or_404(Eleve,pk=id_eleve)
	numsemaine=semaine.numero
	if matiere.temps == 20:
		if matiere.lv == 0:
			groupeseleves=list(Groupe.objects.filter(classe=creneau.classe).order_by('nom'))
		elif matiere.lv == 1:
			groupeseleves=list(Groupe.objects.filter(classe=creneau.classe,groupeeleve__lv1=matiere).distinct().order_by('nom'))
		elif matiere.lv == 2:
			groupeseleves=list(Groupe.objects.filter(classe=creneau.classe,groupeeleve__lv2=matiere).distinct().order_by('nom'))
		groupeseleves.sort(key = lambda x:int(x.nom))
		rang=groupeseleves.index(groupe)
	elif matiere.temps == 30:
		if matiere.lv == 0:
			groupeseleves=list(Eleve.objects.filter(classe=creneau.classe))
		elif matiere.lv == 1:
			groupeseleves=list(Eleve.objects.filter(classe=creneau.classe,lv1=matiere))
		elif matiere.lv == 2:
			groupeseleves=list(Eleve.objects.filter(classe=creneau.classe,lv2=matiere))
		rang=groupeseleves.index(eleve)
	i=0
	creneaux={'creneau':creneau.pk,'couleur':matiere.couleur,'colleur':creneau.classe.dictColleurs()[colleur.pk]}
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
	elif matiere.temps == 60:
		for numero in range(numsemaine,numsemaine+int(duree),int(frequence)):
			try:
				semainecolle=Semaine.objects.get(numero=numero)
				if semainecolle.lundi + timedelta(days = creneau.jour) not in feries:
					Colle.objects.filter(creneau=creneau,semaine=semainecolle).delete()
					Colle(creneau=creneau,colleur=colleur,matiere=matiere,eleve=None,semaine=semainecolle,classe = creneau.classe).save()
					creneaux['semgroupe'].append({'semaine':semainecolle.pk,'groupe':""})
			except Exception:
				pass
	return HttpResponse(json.dumps(creneaux))

def mixteRamassagePdfParClasse(ramassage,total,parmois,full,colleur=False):
    """Renvoie le fichier PDF du ramassage par classe correspondant au ramassage dont l'id est id_ramassage
    si total vaut 1, les totaux par classe et matière sont calculés"""
    LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
    response = HttpResponse(content_type='application/pdf')
    if Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).exists() and not full:# s'il existe un ramassage antérieur
        debut = Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).aggregate(Max('moisFin'))['moisFin__max'] + timedelta(days=1)
    else:
        debut = Semaine.objects.aggregate(Min('lundi'))['lundi__min']
    fin = ramassage.moisFin
    moisdebut = 12*debut.year+debut.month-1
    decomptes = Ramassage.objects.decompteRamassage(ramassage, csv = False, parClasse = True, parMois=bool(parmois), full = full, colleur = colleur)
    nomfichier="ramassagePdfParclasse{}_{}-{}_{}.pdf".format(debut.month,debut.year,fin.month,fin.year)
    response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
    pdf = easyPdf(titre="Ramassage des colles de {} {} à {} {}".format(LISTE_MOIS[debut.month],debut.year,LISTE_MOIS[fin.month],fin.year),marge_x=30,marge_y=30)
    largeurcel=(pdf.format[0]-2*pdf.marge_x)/(10+parmois)
    hauteurcel=30
    total=int(total)
    for classe, listeClasse, nbMatieres in decomptes:
        totalclasse = 0
        pdf.debutDePage(soustitre = classe)
        nbKolleurs = nbMatieres
        if total:
            nbKolleurs += 1 + len([x for x,y,z in listeClasse]) # on rajoute le nombre de matières et 1 pour la classe
        LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
                                            ,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
                                            ,('VALIGN',(0,0),(-1,-1),'MIDDLE')
                                            ,('ALIGN',(0,0),(-1,-1),'CENTRE')
                                            ,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
                                            ,('SIZE',(0,0),(-1,-1),8)])
        data = [["Matière","Établissement","Grade","Colleur"] + (["mois"] if parmois else []) + ["heures"]]+[[""]*(5+parmois) for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
        ligneMat=ligneEtab=ligneGrade=ligneColleur=ligneMois=1
        for matiere, listeEtabs, nbEtabs in listeClasse:
            totalmatiere = 0
            data[ligneMat][0]=matiere
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
                    if parmois:# si on ramassage pour chaque mois
                        for colleur, listeMois, nbMois in listeColleurs:
                            data[ligneColleur][3]=colleur
                            if nbMois>1:
                                LIST_STYLE.add('SPAN',(3,ligneColleur),(3,min(ligneColleur+nbMois-1,22)))
                            ligneColleur+=nbMois
                            for moi,  heures in listeMois:
                                totalmatiere += heures
                                if moi<moisdebut:
                                    LIST_STYLE.add('TEXTCOLOR',(4,ligneMois),(5,ligneMois),(1,0,0))
                                data[ligneMois][4]=LISTE_MOIS[moi%12+1]
                                data[ligneMois][5]="{:.02f}h".format(heures/60).replace('.',',')
                                ligneMois+=1
                                if ligneMois==23 and nbKolleurs>22: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
                                    t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel, largeurcel, largeurcel],rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
                                    t.setStyle(LIST_STYLE)
                                    w,h=t.wrapOn(pdf,0,0)
                                    t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
                                    pdf.finDePage()
                                    # on redémarre sur une nouvelle page
                                    pdf.debutDePage(soustitre = classe)
                                    LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
                                                    ,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
                                                    ,('VALIGN',(0,0),(-1,-1),'MIDDLE')
                                                    ,('ALIGN',(0,0),(-1,-1),'CENTRE')
                                                    ,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
                                                    ,('SIZE',(0,0),(-1,-1),8)])
                                    nbKolleurs-=22
                                    data = [["Matière","Établissement","Grade","Colleur","mois","heures"]]+[[""]*6 for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
                                    ligneEtab-=22
                                    ligneGrade-=22
                                    ligneMat-=22
                                    ligneColleur-=22
                                    ligneMois = 1
                                    if ligneMat>1:
                                        data[1][0]=matiere
                                        if ligneMat>2:
                                            LIST_STYLE.add('SPAN',(0,1),(0,min(ligneMat-1,22)))
                                        if ligneEtab>1:
                                            data[1][1]='Inconnu' if not etablissement else etablissement.title()
                                            if ligneEtab>2:
                                                LIST_STYLE.add('SPAN',(1,1),(1,min(ligneEtab-1,22)))
                                            if ligneGrade>1:
                                                data[1][2]=grade
                                                if ligneGrade>2:
                                                    LIST_STYLE.add('SPAN',(2,1),(2,min(ligneGrade-1,22)))
                                                if ligneColleur>1:
                                                    data[1][3]=colleur
                                                    if ligneColleur>2:
                                                        LIST_STYLE.add('SPAN',(3,1),(3,min(ligneColleur-1,22)))
            # fin matière
                    else:# si on ne ramasse pas pour chaque mois mais globalement sur la période de ramassage
                        for colleur, heures in listeColleurs:
                            totalmatiere += heures
                            data[ligneColleur][3]=colleur
                            data[ligneColleur][4]="{:.02f}h".format(heures/60).replace('.',',')
                            ligneColleur+=1
                            if ligneColleur==23 and nbKolleurs>22: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
                                t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel, largeurcel],rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
                                t.setStyle(LIST_STYLE)
                                w,h=t.wrapOn(pdf,0,0)
                                t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
                                pdf.finDePage()
                                # on redémarre sur une nouvelle page
                                pdf.debutDePage(soustitre = classe)
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
                                            LIST_STYLE.add('SPAN',(1,1),(1,min(ligneEtab-1,22)))
                                        if ligneGrade>1:
                                            data[1][2]=grade
                                            if ligneGrade>2:
                                                LIST_STYLE.add('SPAN',(2,1),(2,min(ligneGrade-1,22)))
            # fin matière
            totalclasse += totalmatiere
            if total:
                LIST_STYLE.add('SPAN',(0,ligneColleur),(3+parmois,ligneColleur))
                LIST_STYLE.add('BACKGROUND',(0,ligneColleur),(-1,ligneColleur),(.8,.8,.8))
                data[ligneColleur] = ["total {}".format(matiere.title())]+[""]*(3+parmois)+["{:.02f}h".format(totalmatiere/60).replace('.',',')]
                ligneEtab+=1
                ligneGrade+=1
                ligneMat+=1
                ligneColleur+=1
                ligneMois+=1
                if ligneColleur==23 and nbKolleurs>22: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
                    t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel, largeurcel],rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
                    t.setStyle(LIST_STYLE)
                    w,h=t.wrapOn(pdf,0,0)
                    t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
                    pdf.finDePage()
                    # on redémarre sur une nouvelle page
                    pdf.debutDePage(soustitre = classe)
                    LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
                                    ,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
                                    ,('VALIGN',(0,0),(-1,-1),'MIDDLE')
                                    ,('ALIGN',(0,0),(-1,-1),'CENTRE')
                                    ,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
                                    ,('SIZE',(0,0),(-1,-1),8)])
                    nbKolleurs-=22
                    data = [["Matière","Établissement","Grade","Colleur"] + (["mois"] if parmois else []) + ["heures"]]+[[""]*(5+parmois) for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
                    ligneEtab-=22
                    ligneGrade-=22
                    ligneMat-=22
                    if parmois:
                        ligneColleur-=22
                        ligneMois=1
                    else:
                        ligneColleur=1
        # fin classe
        if total:
            LIST_STYLE.add('SPAN',(0,ligneColleur),(3+parmois,ligneColleur))
            LIST_STYLE.add('BACKGROUND',(0,ligneColleur),(-1,ligneColleur),(.7,.7,.7))
            data[ligneColleur] = ["total {}".format(classe)]+[""]*(3+parmois)+["{:.02f}h".format(totalclasse/60).replace('.',',')]
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
