#-*- coding: utf-8 -*-
from io import BytesIO
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, legal, landscape
from reportlab.platypus import Table, TableStyle
from reportlab.platypus.flowables import Flowable
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from ecolle.settings import NOM_ETABLISSEMENT
from accueil.models import Groupe, Colle, Matiere, Colleur
from reportlab.lib.units import cm

class FlowTextRectangle(Flowable):
	"""un rectangle avec du texte, flowable, donc qu'on peut insérer facilement dans une Frame"""
	def __init__(self,texte="",marge=False):
		self.texte=texte
		self.fillcolor=(.9,.9,.9)
		self.size=9*cm
		self.marge=marge

	def wrap(self, *args):
		if self.marge:
			return (0,20)
		return (0,16)

	def draw(self):
		canvas = self.canv
		canvas.setLineWidth(1)
		canvas.setFillColor(self.fillcolor)
		canvas.setStrokeColor((0,0,0))
		canvas.rect(0,0,self.size,16,1,1)
		canvas.setFont("Helvetica-Bold",12)
		canvas.setFillColorRGB(0,0,0)
		canvas.drawString(1,3,self.texte)

class easyPdf(Canvas):
	"""classe fille de canvas avec des méthodes supplémentaires pour créer le titre et la fin de page"""
	def __init__(self,size=A4,orientation='portrait',marge_x=0,marge_y=0,titre="",*args,**kwargs):
		"""initialise la page en définissant le format et les marges"""
		self.titre=titre
		self.format=size
		self.marge_x=marge_x
		self.marge_y=marge_y
		self.x=self.y=0
		if orientation=='landscape':
			self.format=landscape(self.format)
		self.buffer=BytesIO()
		Canvas.__init__(self,self.buffer,pagesize=self.format)

	def texteRectangle(self,texte,largeur,hauteur,fontsize,couleur=(1,1,1),droite=True):
		"""dessine un rectangle de largeur largeur et de hauteur hauteur contenant le texte texte centré,\
		 avec comme couleur de fond couleur, taille de caractère fontsize et modifie les coordonnées x et y du curseur"""
		if fontsize:
			self.setFont("Helvetica-Bold",fontsize)
		self.setFillColorRGB(couleur[0],couleur[1],couleur[2])
		self.rect(self.x,self.y,largeur,hauteur,1,1)
		self.setFillColorRGB(0,0,0)
		self.x+=largeur/2
		self.y+=hauteur/2-fontsize/3
		self.drawCentredString(self.x,self.y,texte)
		self.x+=largeur/2
		self.y-=hauteur/2-fontsize/3
		if not droite:
			self.x-=largeur
			self.y-=hauteur

	def debutDePage(self,hauteurcel=20,soustitre=False):
		"""débute la page en inscrivant le titre et le sous-titre"""
		self.x=self.format[0]/2
		self.y=self.format[1]-self.marge_y
		self.setFont("Helvetica-Bold",12)
		self.drawCentredString(self.x,self.y,self.titre)
		self.y-=20
		self.drawCentredString(self.x,self.y,NOM_ETABLISSEMENT)
		if soustitre:
			self.y-=26
			self.setFillColorRGB(.5,.5,.5)
			self.rect(self.marge_x,self.y,self.format[0]-2*self.marge_x,20,0,1)
			self.setFillColorRGB(0,0,0)
			self.y+=6
			self.drawCentredString(self.x,self.y,soustitre)
			self.y-=6

	def finDePage(self):
		"""termine la page en inscrivant le numéro de page en bas """
		self.x=self.format[0]/2
		self.y=self.marge_y
		self.setFont("Helvetica-Oblique",8)
		self.drawCentredString(self.x,self.y,"page n°{}".format(self.getPageNumber()))
		self.showPage()

def Pdf(classe,semin,semax):
	"""Renvoie le fichier PDF du colloscope de la classe classe, entre les semaines semin et semax"""
	groupes=Groupe.objects.filter(groupeeleve__classe=classe).distinct()
	jours,creneaux,colles,semaines=Colle.objects.classe2colloscope(classe,semin,semax)
	jours=list(jours)
	matieres=Matiere.objects.filter(colle__creneau__classe=classe,colle__semaine__lundi__range=(semin.lundi,semax.lundi)).distinct()
	couleurs=dict()
	for matiere in matieres:
		rouge=int(matiere.couleur[1:3],16)/255
		vert=int(matiere.couleur[3:5],16)/255
		bleu=int(matiere.couleur[5:7],16)/255
		couleurs[matiere.pk]=(rouge,vert,bleu)
	LISTE_JOURS=["lundi","mardi","mercredi","jeudi","vendredi","samedi"]
	response = HttpResponse(content_type='application/pdf')
	nomfichier="Colloscope_{}_semaine_{}_{}.pdf".format(classe.nom,semin.numero,semax.numero)
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	pdf = easyPdf(orientation='landscape',titre="Colloscope {} semaines n°{} à {}".format(classe.nom,semin.numero,semax.numero),marge_x=30,marge_y=30)
	nbCreneaux=creneaux.count()
	nbPages=max((nbCreneaux-1)//20+1,1)
	creneauxParPage=max(1,-((-nbCreneaux)//nbPages))
	largeurcel=min((pdf.format[0]-2*pdf.marge_x-70)/max(creneauxParPage,1),60)
	hauteurcel=(pdf.format[1]-70-2*pdf.marge_y)/18
	nbSemaines=len(colles)
	semaines=list(semaines)
	for indsemaine in range(0,nbSemaines,15): # on place au maximum 15 semaines par pages
		indjour=0
		reste=0
		dernierJour=0
		for indcreneau in range(0,nbCreneaux,creneauxParPage): # on place au maximum creneauxParPage créneaux par page
			nbjours=0
			nbCreneauxLoc=min(creneauxParPage,nbCreneaux-indcreneau)
			nbSemainesLoc=min(15,nbSemaines-indsemaine)
			pdf.debutDePage(soustitre="Calendrier des colles")
			LIST_STYLE = TableStyle([('GRID',(1,0),(-1,-1),1,(0,0,0))
										,('GRID',(0,1),(0,-1),1,(0,0,0))
										,('VALIGN',(0,0),(-1,-1),'MIDDLE')
										,('ALIGN',(0,0),(-1,-1),'CENTRE')
										,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
										,('SIZE',(0,0),(-1,-1),9)])
			data = [[""]*(1+nbCreneauxLoc) for i in range(3+nbSemainesLoc)] # on créé un tableau de la bonne taille, rempli de chaînes vides
			# on remplit les jours.
			if reste!=0:# S'il reste des créneaux d'un jour de la page précédente
				data[0][1]=LISTE_JOURS[dernierJour] # on réécrit le nom du jour
				LIST_STYLE.add('SPAN',(1,0),(reste,0)) # on fusionne les bonnes cases
				nbjours=reste # on met à jour le nombre de créneaux déjà pris en compte
				reste=0 # on remet le reste à 0
			while nbjours<nbCreneauxLoc:
				dernierJour=jours[indjour]['jour']
				data[0][nbjours+1]=LISTE_JOURS[dernierJour]
				LIST_STYLE.add('SPAN',(nbjours+1,0),(min(nbjours+jours[indjour]['nb'],nbCreneauxLoc),0))
				nbjours+=jours[indjour]['nb']
				indjour+=1
			reste=nbjours-nbCreneauxLoc
			# on remplit les heures, ainsi que les salles
			data[1][0]="Heure"
			data[2][0]="Salle"
			for cren in range(nbCreneauxLoc):
				heure = creneaux[indcreneau+cren].heure
				data[1][cren+1] = "{}h{:02d}".format(heure//4,15*(heure%4))
				data[2][cren+1] = creneaux[indcreneau+cren].salle
			#on places les colles dans le tableau, ainsi que les bonnes couleurs
			for icren in range(indcreneau,indcreneau+nbCreneauxLoc):
				for isem in range(indsemaine,indsemaine+nbSemainesLoc):
					# On place les semaines dans la première colonne
					data[3+isem-indsemaine][0]="S"+str(semaines[isem])
					colle=colles[isem][icren]
					if colle['id_col']:
						if colle['temps']==20:
							data[3+isem-indsemaine][1+icren-indcreneau]="{}:{}".format(classe.dictColleurs(semin,semax)[colle['id_colleur']],colle['nomgroupe'])
						elif colle['temps']==30:
							data[3+isem-indsemaine][1+icren-indcreneau]="{}:{}".format(classe.dictColleurs(semin,semax)[colle['id_colleur']],classe.dictEleves()[colle['id_eleve']])
						elif colle['temps']==60:
							data[3+isem-indsemaine][1+icren-indcreneau]="{}".format(classe.dictColleurs(semin,semax)[colle['id_colleur']])
						LIST_STYLE.add('BACKGROUND',(1+icren-indcreneau,3+isem-indsemaine),(1+icren-indcreneau,3+isem-indsemaine),couleurs[colle['id_matiere']])
			t=Table(data,colWidths=[70]+nbCreneauxLoc*[largeurcel],rowHeights=(3+nbSemainesLoc)*[hauteurcel])
			t.setStyle(LIST_STYLE)
			w,h=t.wrapOn(pdf,0,0)
			t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-((pdf.y-pdf.marge_y)-h)/2)
			pdf.finDePage()
	fontsize=10
	pdf.setFont("Helvetica-Bold",fontsize)
	largeurcel=(pdf.format[0]-2*pdf.marge_x)/6
	hauteurcel=(pdf.format[1]-2*pdf.marge_y-70)/12
	pdf.debutDePage(soustitre="Groupes de colle")
	groupes = list(groupes)
	nbGroupes = len(groupes)
	for indGroupe in range(0,nbGroupes,6):
		nbGroupesLoc=min(6,nbGroupes-indGroupe)
		data=[["Groupe {}".format(groupes[indGroupe+i]) for i in range(nbGroupesLoc)]]
		data += [[""]*nbGroupesLoc for i in range(3)]
		for iGroupe in range(indGroupe,indGroupe+nbGroupesLoc):
			ieleve=0
			for eleve in groupes[iGroupe].groupeeleve.all():
				ieleve+=1
				data[ieleve][iGroupe-indGroupe]="{} {} ({})".format(eleve.user.first_name.title(),eleve.user.last_name.upper(),classe.dictEleves()[eleve.id])
		LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
										,('VALIGN',(0,0),(-1,-1),'MIDDLE')
										,('ALIGN',(0,0),(-1,-1),'CENTRE')
										,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
										,('SIZE',(0,0),(-1,-1),8)
										,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))])
		t=Table(data,colWidths=[largeurcel]*nbGroupesLoc,rowHeights=[hauteurcel]*4)
		t.setStyle(LIST_STYLE)
		w,h=t.wrapOn(pdf,0,0)
		t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-10)
		pdf.y-=h+10
	pdf.finDePage()
	matieres=Matiere.objects.filter(matieresclasse=classe,colle__creneau__classe=classe,colle__semaine__lundi__range=(semin.lundi,semax.lundi)).distinct()
	largeurcel=min(150,(pdf.format[0]-2*pdf.marge_x)/max(matieres.count(),1))
	hauteurcel=40
	for matiere in matieres:
		nbcolleurs=Colle.objects.filter(creneau__classe=classe,matiere=matiere,semaine__lundi__range=(semin.lundi,semax.lundi)).values('colleur').distinct().count()
		hauteurcel=min(hauteurcel,(pdf.format[1]-2*pdf.marge_y-70)/nbcolleurs)
	pdf.debutDePage(soustitre="Liste des colleurs")
	pdf.x=(pdf.format[0]-matieres.count()*largeurcel)/2
	pdf.y-=10
	fontsize=9
	pdf.setFont("Helvetica-Bold",fontsize)
	for matiere in matieres:
		data=[[matiere]]
		colleurs=Colle.objects.filter(creneau__classe=classe,matiere=matiere,semaine__lundi__range=(semin.lundi,semax.lundi)).values('colleur').distinct()
		for colleur_id in colleurs:
			colleur=get_object_or_404(Colleur,pk=colleur_id['colleur'])
			data+=[["{}. {} ({})".format(colleur.user.first_name[0].title(),colleur.user.last_name.upper(),classe.dictColleurs(semin,semax)[colleur.pk])]]
		LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
										,('VALIGN',(0,0),(-1,-1),'MIDDLE')
										,('ALIGN',(0,0),(-1,-1),'CENTRE')
										,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
										,('SIZE',(0,0),(-1,-1),8)
										,('BACKGROUND',(0,0),(0,-1),couleurs[matiere.pk])])
		t=Table(data,rowHeights=hauteurcel,colWidths=largeurcel)
		t.setStyle(LIST_STYLE)
		w,h=t.wrapOn(pdf,0,0)
		t.drawOn(pdf,pdf.x,pdf.y-h)
		pdf.x+=w
	pdf.finDePage()
	pdf.save()
	fichier = pdf.buffer.getvalue()
	pdf.buffer.close()
	response.write(fichier)
	return response


