#-*- coding: utf-8 -*-
from accueil.models import Colleurgroupe, Dispo, Frequence, Groupe, Colleur
from Numberjack import Variable, Model, Gcc, AllDiff
from math import gcd


def planif(semin,semax,classes):
	"""recherche à planifier les colles sur les classes classes entre les semaines semin et semax
	en se basant sur les données de disponibilités des colleurs, de fréquences des colles par classe/matière
	de nombre max de colles par créneau, et les applique au colloscope si une solution est trouvée,
	en écrasant les éventuelles colles préexistantes"""
	# on commence par calculer le nombre minimal de semaines sur lequel on doit planifier (on étendra aux autres semaines en faisant tourner les groupes)
	# temp = 24
	# for frequence in Frequence.objects.filter(classe__in=classes):
	# 	temp=gcd(temp,frequence.frequence)
	# nbsemaines=24//temp
	# contraintes = [[[]]*nbsemaines]*classes.count() # liste qui va contenir les horaires des différentes colles
	# colleurs = [{} for i in range(nbsemaines)] # liste des colleurs avec leur colles par semaine
	# # on calcule le nombres de colles par classe/matieres/semaine
	# model=Model() # on initialise le modèle
	# for i,classe in enumerate(classes):
	# 	for matiere in classe.matieres.filter(temps=20):
	# 		frequence = Frequence.objects.filter(classe=classe,matiere=matiere).first()
	# 		if frequence is not None and frequence.repartition and frequence.frequence not in [18,16]:
	# 			indice = 0 
	# 			pas=24//frequence.frequence
	# 			semaine=frequence.premiere-1
	# 			for colleur in Colleur.objects.filter(classes=classe,matieres=matiere):
	# 				nbgroupes = Colleurgroupe.objects.filter(classe=classe,matiere=matiere,colleur=colleur,nbgroupes__gt=0)
	# 				if nbgroupes.exists():
	# 					nbgroupes=nbgroupes[0].nbgroupes
	# 					if colleur.dispos.all():
	# 						variables = [Variable([96*dispo.jour+dispo.heure for dispo in colleur.dispos.all()],"x_{}_{}_{}_{}_{}".format(classe.pk,semaine,matiere.pk,colleur.pk,j)) for j in range(nbgroupes)]
	# 						contraintes[i][semaine].extend(variables)
	# 						if colleur.pk in colleurs[semaine]:
	# 							colleurs[semaine][colleur.pk].extend(variables)
	# 						else:
	# 							colleurs[semaine][colleur.pk]=variables
	# for variables in colleurs:
	# 	for liste in variables.values():
	# 		if len(liste)>1:
	# 			model.add(AllDiff(liste))

	# print(model)
						

