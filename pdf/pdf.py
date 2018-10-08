#-*- coding: utf-8 -*-
from io import BytesIO
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Table, TableStyle, Image, Frame, Paragraph
from reportlab.lib.styles import ParagraphStyle
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from ecolle.settings import RESOURCES_ROOT
from accueil.models import Groupe, Colle, Matiere, Colleur, NoteECTS, Eleve, Config
from reportlab.lib.units import cm
from unidecode import unidecode
from os.path import join
from xml.etree import ElementTree as etree

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
		self.drawCentredString(self.x,self.y,Config.objects.get_config().nom_etablissement)
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
	nomfichier="Colloscope_{}_semaine_{}_{}.pdf".format(unidecode(classe.nom),semin.numero,semax.numero)
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
				data[1][cren+1] = "{}h{:02d}".format(heure//60,(heure%60))
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
		data=[[matiere.nom.title() + ("" if not matiere.lv else "(LV{})".format(matiere.lv))]]
		colleurs=Colle.objects.filter(creneau__classe=classe,matiere=matiere,semaine__lundi__range=(semin.lundi,semax.lundi)).values('colleur').distinct().order_by('colleur__user__last_name','colleur__user__first_name')
		for colleur_id in colleurs:
			colleur=get_object_or_404(Colleur,pk=colleur_id['colleur'])
			data+=[["{}. {} ({})".format("" if not colleur.user.first_name else colleur.user.first_name[0].title(),colleur.user.last_name.upper(),classe.dictColleurs(semin,semax)[colleur.pk])]]
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

def attestationects(form,elev,classe):
	"""renvoie l'attestation ects pdf de l'élève elev, ou si elev vaut None renvoie les attestations ects pdf de toute la classe classe en un seul fichier"""
	datedujour = form.cleaned_data['date'].strftime('%d/%m/%Y')
	filiere = form.cleaned_data['classe'].split("_")[0]
	signataire = form.cleaned_data['signature']
	annee = form.cleaned_data['anneescolaire']
	etoile = form.cleaned_data['etoile']
	signature = False
	if 'tampon' in form.cleaned_data:
		signature = form.cleaned_data['tampon']
	config=Config.objects.get_config()
	annee = "{}-{}".format(int(annee)-1,annee)
	response = HttpResponse(content_type='application/pdf')
	if elev is None:
		eleves = Eleve.objects.filter(classe=classe).order_by('user__last_name','user__first_name').select_related('user')
		nomfichier="ATTESTATIONS_{}.pdf".format(unidecode(classe.nom)).replace(" ","-")
		credits = NoteECTS.objects.credits(classe)[0]
	else:
		eleves=[elev]
		credits=[False]
		nomfichier=unidecode("ATTESTATION_{}_{}_{}.pdf".format(elev.classe.nom.upper(),elev.user.first_name,elev.user.last_name.upper())).replace(" ","-")
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	pdf = easyPdf()
	pdf.marge_x = cm # 1cm de marge gauche/droite
	pdf.marge_y = 1.5*cm # 1,5cm de marge haut/bas
	I = Image(join(RESOURCES_ROOT,'marianne.jpg'))
	I.drawHeight = 1.8*cm
	I.drawWidth = 3*cm
	if signature and signataire == 'Proviseur':
		try:
			I2 = Image(join(RESOURCES_ROOT,'proviseur.png'))
		except Exception:
			try:
				I2 = Image(join(RESOURCES_ROOT,'proviseur.png'))
			except Exception:
				I2 = False
	elif signature and signataire == 'Proviseur adjoint':
		try:
			I2 = Image(join(RESOURCES_ROOT,'proviseuradjoint.png'))
		except Exception:
			try:
				I2 = Image(join(RESOURCES_ROOT,'proviseuradjoint.png'))
			except Exception:
				I2 = False
	else:
		I2 = False
	if I2:
		I2.drawHeight = 3*cm
		I2.drawWidth = 3*cm
	newpage = False
	for eleve,credit in zip(eleves,credits):
		if elev or credit and credit['ddn'] and credit['ine'] and credit['sem1']==30 and credit['sem2']==30: # si l'élève a bien toutes les infos/crédits
			if newpage:# si ce n'est pas la première page, on change de page
				pdf.showPage()
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
			pdf.drawCentredString(pdf.format[0]/2,pdf.y, "Le recteur de l'académie de {}, Chancelier des universités,".format(config.academie))
			pdf.y -= 15
			pdf.drawCentredString(pdf.format[0]/2,pdf.y, "atteste que")
			pdf.y -= 40
			pdf.setFont("Helvetica",12)
			pdf.drawCentredString(pdf.format[0]/2,pdf.y, "{}".format(eleve))
			pdf.y -= 50
			pdf.setFont("Helvetica",11)
			pdf.drawString(2*cm,pdf.y, "né(e) le {} à {}".format(eleve.ddn.strftime('%d/%m/%Y'),eleve.ldn.title()))
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
			pdf.drawString(2*cm,pdf.y,config.nom_etablissement)
			pdf.y -= 30
			pdf.drawCentredString(pdf.format[0]/2,pdf.y,"Fait à {},".format(config.ville))
			pdf.y -= 15
			pdf.drawString(15*cm,pdf.y,"le {}".format(datedujour))
			pdf.y -= 15
			pdf.drawString(15*cm,pdf.y,"Pour le recteur,")
			pdf.y -= 15
			pdf.drawString(15*cm,pdf.y,"Le {}".format(signataire.lower()))
			pdf.y -= 3*cm
			pdf.x = pdf.format[0]-5*cm-2*pdf.marge_x
			if I2:
				I2.drawOn(pdf,pdf.x,pdf.y)
			pdf.setFont("Helvetica-Oblique",9)
			pdf.y=3*cm
			pdf.drawCentredString(pdf.format[0]/2,pdf.y,"Attestation délivrée en application des dispositions de l’article 8 du décret n° 94-1015")
			pdf.y-=12
			pdf.drawCentredString(pdf.format[0]/2,pdf.y,"du 23 novembre 1994 modifié par le décret n° 2007-692 du 3 mai 2007")
			pdf.y-=12
			pdf.drawCentredString(pdf.format[0]/2,pdf.y,"Le descriptif de la formation figure dans l’annexe jointe.")
			newpage = True
	pdf.save()
	fichier = pdf.buffer.getvalue()
	pdf.buffer.close()
	response.write(fichier)
	return response

def creditsects(form,elev,classe):
	"""renvoie les crédits ects pdf de l'élève elev, ou si elev vaut None renvoie les crédits ects pdf de toute la classe en un seul fichier"""
	datedujour = form.cleaned_data['date'].strftime('%d/%m/%Y')
	filiere,annee = form.cleaned_data['classe'].split("_")
	signataire = form.cleaned_data['signature']
	etoile = form.cleaned_data['etoile']
	tree=etree.parse(join(RESOURCES_ROOT,'classes.xml')).getroot()
	classexml=tree.findall("classe[@nom='{}'][@annee='{}']".format(filiere,annee)).pop()
	domaine = classexml.get("domaine")
	branche = classexml.get("type").lower()
	precision = classexml.get("precision")
	signature = False
	if 'tampon' in form.cleaned_data:
		signature = form.cleaned_data['tampon']
	LIST_NOTES="ABCDEF"
	response = HttpResponse(content_type='application/pdf')
	if elev is None:
		eleves = Eleve.objects.filter(classe=classe).order_by('user__last_name','user__first_name').select_related('user')
		nomfichier="ECTS_{}.pdf".format(unidecode(classe.nom)).replace(" ","-").replace('*','etoile')
		credits = NoteECTS.objects.credits(classe)[0]
	else:
		eleves=[elev]
		credits=[False]
		nomfichier=unidecode("ECTS_{}_{}_{}.pdf".format(classe.nom.upper(),elev.user.first_name,elev.user.last_name.upper())).replace(" ","-")
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	pdf = easyPdf()
	cm = pdf.format[0]/21
	pdf.marge_x = cm # 1cm de marge gauche/droite
	pdf.marge_y = 1.5*cm # 1,5cm de marge haut/bas
	I = Image(join(RESOURCES_ROOT,'marianne.jpg'))
	I.drawHeight = 1.8*cm
	I.drawWidth = 3*cm
	if signature and signataire == 'Proviseur':
		try:
			I2 = Image(join(RESOURCES_ROOT,'proviseur.png'))
		except Exception:
			try:
				I2 = Image(join(RESOURCES_ROOT,'proviseur.png'))
			except Exception:
				I2 = False
	elif signature and signataire == 'Proviseur adjoint':
		try:
			I2 = Image(join(RESOURCES_ROOT,'proviseuradjoint.png'))
		except Exception:
			try:
				I2 = Image(join(RESOURCES_ROOT,'proviseuradjoint.png'))
			except Exception:
				I2 = False
	else:
		I2 = False
	if I2:
		I2.drawHeight = 3*cm
		I2.drawWidth = 3*cm
	newpage = False
	style=ParagraphStyle(name='normal',fontSize=9,leading=11,spaceAfter=5)
	styleResume=ParagraphStyle(name='resume',fontSize=9,leading=11,spaceAfter=0)
	styleTitre=ParagraphStyle(name='titre',fontSize=12,leading=13,fontName="Helvetica-Bold",borderColor='black',borderPadding=(0,0,2,0),borderWidth=1,backColor='#DDDDDD',spaceAfter=2)
	data1 = [["A","Très Bien","C","Assez Bien","E","Passable"],["B","Bien","D","Convenable","F","Insuffisant"]]
	LIST_STYLE1 = TableStyle([('GRID',(0,0),(-1,-1),.2,(0,0,0))
								,('VALIGN',(0,0),(-1,-1),'MIDDLE')
								,('ALIGN',(0,0),(-1,-1),'CENTRE')
								,('FACE',(0,0),(-1,-1),'Helvetica')
								,('SIZE',(0,0),(-1,-1),8)
								,('BACKGROUND',(0,0),(-1,-1),(.9,.9,.9))])
	t1=Table(data1,colWidths=[.8*cm,2*cm,.8*cm,2*cm,.8*cm,2*cm],rowHeights=[12]*2)
	t1.setStyle(LIST_STYLE1)
	data2 = [["8","D","","Université","",""],["7","D","","Université","",""],["6","D","","Université","",""],\
			["5","M","","Université ou grande école","",""],["4","M","","Université ou grande école","",""],["3","L","ATS","Université ou grande école","",""],\
			["2","L","STS-IUT","","Université","CPGE"],["1","L","STS-IUT","","Université","CPGE"],["0","Bac","Enseignement secondaire","","",""]]
	LIST_STYLE2 = TableStyle([('GRID',(0,0),(1,4),.8,(0,0,0))
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
	t2=Table(data2,colWidths=[.84*cm,.91*cm,.75*cm,1.4*cm,2.5*cm,2.5*cm],rowHeights=[.8*cm]*9)
	t2.setStyle(LIST_STYLE2)
	texte="1. Information sur l'étudiant"
	p1=Paragraph(texte,styleTitre)
	texte="2. Information sur la formation"
	p3=Paragraph(texte,styleTitre)
	texte="3. Information sur le niveau de la formation"
	p5=Paragraph(texte,styleTitre)
	texte="""<b><i>3.1. Niveau de la formation:</i></b><br/>
	Située au sein des études menant au grade de licence.<br/>
	Niveau bac + 2 / 120 crédits ECTS<br/>
	<b><i>3.2. Durée officielle du programme de formation:</i></b><br/>
	La durée du programme est de 2 ans.<br/>
	<b><i>3.3. Conditions d’accès:</i></b><br/>
	Entrée sélective après le baccalauréat s’effectuant dans le cadre d’une procédure nationale d’admission.<br/>
	Cf: <a href="http://www.parcoursup.fr" color="blue">http://www.parcoursup.fr</a>"""
	p6=Paragraph(texte,style)
	texte="""4. Information sur les contenus et les résultats obtenus"""
	p7=Paragraph(texte,styleTitre)
	texte="""<b><i>4.1. Organisation des études:</i></b><br/>
	Plein temps, contrôle continu écrit et oral<br/>
	<b><i>4.2. Exigences du programme:</i></b><br/>
	La formation dispensée a pour objet de donner aux étudiants une compréhension approfondie des disciplines enseignées et une appréhension de leurs caractéristiques générales. Elle prend en compte leurs évolutions, leurs applications et la préparation à des démarches de recherche.
	Elle est définie par des programmes nationaux.<br/>
	<b><i>4.3. Précisions sur le programme:</i></b><br/>
	Voir relevé au verso et catalogue de cours<br/>
	<b><i>4.4. Échelle d’évaluation:</i></b><br/>
	L’évaluation prend en compte l’ensemble des travaux des étudiants. La qualité du travail, des résultats obtenus et des compétences acquises est exprimée par une mention conformément au tableau ci-dessous."""
	p8=Paragraph(texte,styleResume)
	texte="""<b><i>4.5. Classification de la formation:</i></b><br/>
	Une mention globale, portant sur l’ensemble du parcours et s’exprimant dans la même échelle qu’en 4.4 figure à la fin du relevé."""
	p9=Paragraph(texte,style)
	texte="5. Information sur la fonction de la qualification"
	p10=Paragraph(texte,styleTitre)
	texte="""<b><i>5.1. Accès à un niveau d’études supérieur:</i></b><br/>
	Accès par concours aux grandes écoles.<br/>
	Accès, par validation de parcours, à tout type d’établissement d’enseignement supérieur.<br/>
	<b><i>5.2. Statut  professionnel (si applicable):</i></b><br/>
	Sans objet"""
	p11=Paragraph(texte,style)
	texte="6. Informations complémentaires"
	p12=Paragraph(texte,styleTitre)
	texte="""<b><i>6.1. Informations complémentaires:</i></b><br/>
	Catalogue des cours et arrêtés ministériels définissant les programmes consultables sur :<br/>
	<a href="http://www.enseignementsup-recherche.gouv.fr/" color="blue">http://www.enseignementsup-recherche.gouv.fr/</a><br/>
	<b><i>6.2. Autres sources d’information:</i></b><br/>
	Pour toute information sur le dispositif CPGE consulter :<br/>
	<a href="http://www.enseignementsup-recherche.gouv.fr/" color="blue">http://www.enseignementsup-recherche.gouv.fr/</a>"""
	p13=Paragraph(texte,style)
	texte="7. Certification de l’attestation"
	p14=Paragraph(texte,styleTitre)
	texte="8. Informations sur le système national d’enseignement supérieur"
	p16=Paragraph(texte,styleTitre)
	p17=Paragraph("<br/> <br/>",style)
	for eleve,credit in zip(eleves,credits):
		if elev or credit and credit['ddn'] and credit['ine'] and credit['sem1']==30 and credit['sem2']==30: # si l'élève a bien toutes les infos/crédits
			if newpage:# si ce n'est pas la première page, on change de page
				pdf.showPage()
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
			story=[p1]
			texte="<b><i>1.1. Nom:</i></b> {}<br/><b><i>1.2. Prénom:</i></b> {}<br/><b><i>1.3. Date de Naissance:</i></b> {}<br/><b><i>1.4. Lieu de Naissance:</i></b> {}<br/><b><i>1.5. N° INE:</i></b> {}".format(eleve.user.last_name.upper(),eleve.user.first_name.title(),"" if not eleve.ddn else eleve.ddn.strftime('%d/%m/%Y'),"" if not eleve.ldn else eleve.ldn.title(),eleve.ine)
			p2=Paragraph(texte,style)
			story.extend([p2,p3])
			texte="""<b><i>2.1. Nom de la formation:</i></b><br/>
			Classe préparatoire {} {} {}<br/>
			<b><i>2.2. Principaux domaines d’étude:</i></b><br/>
			{}<br/>
			<b><i>2.3. Nom et statut de l’institution gérant la formation:</i></b><br/>
			Ministère de l’enseignement supérieur et de la recherche
			Classes préparatoires aux grandes écoles<br/>
			<b><i>2.4. Nom et statut de l’établissement dispensant la formation:</i></b><br/>
			{}<br/>
			<b><i>2.5. Langue de formation:</i></b> français""".format(branche,filiere,"("+precision+")" if precision else "",domaine,Config.objects.get_config().nom_adresse_etablissement.replace("\n","<br/>").replace("\r","<br/>").replace("<br/><br/>","<br/>"))
			p4=Paragraph(texte,style)
			story.extend([p4,p5,p6,p7,p8,t1,p9])
			fl = Frame(cm, 1.5*cm, 9*cm, 23*cm , showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
			fl.addFromList(story,pdf)
			story=[p10,p11,p12,p13,p14]
			texte="""<b><i>7.1. Date:</i></b> {}<br/>
			<b><i>7.2. Signature:</i></b><br/><br/><br/><br/>
			<b><i>7.3. Fonction:</i></b> {}<br/>
			<b><i>7.4. Tampon ou cachet officiel:</i></b><br/><br/><br/><br/><br/><br/>""".format(datedujour,signataire)
			p15=Paragraph(texte,style)
			story.extend([p15,p16,p17,t2])
			fr = Frame(11*cm, 1.5*cm, 9*cm, 23*cm , showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
			fr.addFromList(story,pdf)
			if I2:
				I2.drawOn(pdf,16.2*cm,13.2*cm)
			pdf.showPage()
			pdf.y = pdf.format[1]-pdf.marge_y-12
			pdf.setFont('Helvetica-Bold',12)
			pdf.drawCentredString(10.5*cm,pdf.y,"RELEVÉ DE RÉSULTATS (classe {})".format(filiere + ('*' if etoile and classe.annee == 2 else '')))
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
				if note[4] !=5:
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
			pdf.y-= 3.2*cm
			if I2:
				I2.drawOn(pdf,pdf.format[0]-2*pdf.marge_x-3*cm,pdf.y)
			newpage=True
	pdf.save()
	fichier = pdf.buffer.getvalue()
	pdf.buffer.close()
	response.write(fichier)
	return response
