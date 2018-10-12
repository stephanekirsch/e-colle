#-*- coding: utf-8 -*-
from accueil.models import Groupe, JourFerie, Colle, Semaine, Eleve, Colleur, Creneau, Classe
from datetime import timedelta
from django.db.models import Count, F
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from colleur.forms import SemaineForm, CreneauForm, ColleForm, GroupeForm
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
	matieres = list(classe.matieres.filter(colleur__classes=classe, colleur__user__is_active = True).values_list('pk','nom','couleur','temps').annotate(nb=Count("colleur")))
	colleurs = list(Colleur.objects.exclude(matieres = None).filter(classes=classe,user__is_active = True).values_list('pk','user__first_name','user__last_name').order_by("matieres__nom", "matieres__pk", "user__last_name", "user__first_name"))
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
	colleurs="\n".join(["le colleur {} {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['colleur__user__first_name'].title(),valeur['colleur__user__last_name'].upper(),valeur['nbcolles'],valeur['semaine__numero'],LISTE_JOURS[valeur['creneau__jour']],valeur['creneau__heure']//60,(valeur['creneau__heure']%60)) for valeur in colleurs])
	eleves = Colle.objects.filter(groupe__classe=classe).values('groupe__nom','semaine__numero','creneau__jour','creneau__heure').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','creneau__jour','creneau__heure','groupe__nom')
	eleves="\n".join(["le groupe {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['groupe__nom'].title(),valeur['nbcolles'],valeur['semaine__numero'],LISTE_JOURS[valeur['creneau__jour']],valeur['creneau__heure']//60,(valeur['creneau__heure']%60)) for valeur in eleves])
	elevesolo = Colle.objects.compatEleve(classe.pk)
	elevesolo = "\n".join(["l'élève {} {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['prenom'].title(),valeur['nom'].upper(),valeur['nbcolles'],valeur['numero'],LISTE_JOURS[valeur['jour']],valeur['heure']//60,(valeur['heure']%60)) for valeur in elevesolo])
	groupes=Colle.objects.filter(groupe__classe=classe).values('groupe__nom','matiere__nom','semaine__numero').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','matiere__nom','groupe__nom')
	groupes = "\n".join(["le groupe {} a {} colles de {} en semaine {}".format(valeur['groupe__nom'].title(),valeur['nbcolles'],valeur['matiere__nom'].title(),valeur['semaine__numero']) for valeur in groupes])
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
