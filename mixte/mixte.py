#-*- coding: utf-8 -*-
from accueil.models import Groupe, JourFerie, Colle, Semaine
from datetime import timedelta
from django.db.models import Count

def mixteajaxcompat(classe):
	LISTE_JOURS=['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
	colleurs = Colle.objects.filter(groupe__classe=classe).values('colleur__user__first_name','colleur__user__last_name','semaine__numero','creneau__jour','creneau__heure').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','creneau__jour','creneau__heure','colleur__user__last_name','colleur__user__first_name')
	colleurs="\n".join(["le colleur {} {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['colleur__user__first_name'].title(),valeur['colleur__user__last_name'].upper(),valeur['nbcolles'],valeur['semaine__numero'],LISTE_JOURS[valeur['creneau__jour']],valeur['creneau__heure']//4,15*(valeur['creneau__heure']%4)) for valeur in colleurs])
	eleves = Colle.objects.filter(groupe__classe=classe).values('groupe__nom','semaine__numero','creneau__jour','creneau__heure').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','creneau__jour','creneau__heure','groupe__nom')
	eleves="\n".join(["le groupe {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['groupe__nom'].title(),valeur['nbcolles'],valeur['semaine__numero'],LISTE_JOURS[valeur['creneau__jour']],valeur['creneau__heure']//4,15*(valeur['creneau__heure']%4)) for valeur in eleves])
	elevesolo = Colle.objects.compatEleve(classe.pk)
	elevesolo = "\n".join(["l'élève {} {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['prenom'].title(),valeur['nom'].upper(),valeur['nbcolles'],valeur['numero'],LISTE_JOURS[valeur['jour']],valeur['heure']//4,15*(valeur['heure']%4)) for valeur in elevesolo])
	groupes=Colle.objects.filter(groupe__classe=classe).values('groupe__nom','matiere__nom','semaine__numero').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','matiere__nom','groupe__nom')
	groupes = "\n".join(["le groupe {} a {} colles de {} en semaine {}".format(valeur['groupe__nom'].title(),valeur['nbcolles'],valeur['matiere__nom'].title(),valeur['semaine__numero']) for valeur in groupes])
	reponse=colleurs+"\n\n"*int(bool(colleurs))+eleves+"\n\n"*int(bool(eleves))+elevesolo+"\n\n"*int(bool(elevesolo))+groupes
	if not reponse:
		reponse="aucune incompatibilité dans le colloscope"
	return reponse


def mixteajaxcolloscopemulticonfirm(matiere,colleur,groupe,eleve,semaine,creneau,duree, frequence, permutation):
	numsemaine=semaine.numero
	if matiere.temps == 20:
		if matiere.lv == 0:
			groupeseleves=list(Groupe.objects.filter(classe=creneau.classe).order_by('nom'))
		elif matiere.lv == 1:
			groupeseleves=list(Groupe.objects.filter(classe=creneau.classe,groupeeleve__lv1=matiere).distinct().order_by('nom'))
		elif matiere.lv == 2:
			groupeseleves=list(Groupe.objects.filter(classe=creneau.classe,groupeeleve__lv2=matiere).distinct().order_by('nom'))
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
	return creneaux