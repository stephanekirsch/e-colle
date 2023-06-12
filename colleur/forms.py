#-*- coding: utf-8 -*-
from django import forms
from accueil.models import Colleur, Colle, Note, Semaine, Programme, Eleve, Creneau, Matiere, Groupe, MatiereECTS, NoteECTS, NoteGlobaleECTS, Devoir, DevoirCorrige, DevoirRendu, TD, Cours, Document, Config
from django.db.models import Q, Count, Value
from django.db.models.functions import Coalesce
from datetime import date, timedelta
from django.forms.widgets import SelectDateWidget
from django.core.exceptions import ValidationError
from xml.etree import ElementTree as etree
from ecolle.settings import RESOURCES_ROOT, MEDIA_ROOT, IMAGEMAGICK
from os.path import isfile,join
from os import remove
from copy import copy
from _io import TextIOWrapper
import csv
import re
from zipfile import ZipFile
from unidecode import unidecode
from django.core.files.base import ContentFile

class ColleurConnexionForm(forms.Form):
        username = forms.CharField(label="Identifiant")
        password = forms.CharField(label="Mot de passe",widget=forms.PasswordInput)
            
class ProgrammeForm(forms.ModelForm):
    class Meta:
        model = Programme
        fields=['semaine','titre','detail','fichier']
        widgets = {'semaine':forms.CheckboxSelectMultiple}


    def clean_semaine(self):# on vérifie que les semaines choisies ne chevauchent pas de semaines d'un programme existant.
        semaines = self.cleaned_data['semaine']
        query = Programme.objects.filter(semaine__in=semaines, classe=self.instance.classe,matiere=self.instance.matiere)
        if self.instance.pk: # si c'est une modification:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise ValidationError(
            "Il existe déjà un programme de colle sur une des semaines sélectionnées",
            code='uniqueness violation',
            params={'value': semaines},
            )
        return semaines


    def clean(self):
        super().clean()
        if self.cleaned_data['fichier'] is False: # si on coche la case effacer, on efface le fichier
            fichier=join(MEDIA_ROOT,self.instance.fichier.name)
            if isfile(fichier):
                remove(fichier)
            if IMAGEMAGICK:
                image = join(MEDIA_ROOT,"image"+self.instance.fichier.name[9:-3]+"jpg")
                if isfile(image):
                    remove(image)


class MatiereChoiceField(forms.ModelChoiceField):
    def label_from_instance(self,matiere):
        return matiere.nom.title()

class Groupe2Form(forms.Form):
    def __init__(self,classe,groupe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.groupe=groupe
        self.classe=classe
        if not groupe:
            query=Eleve.objects.filter(groupe__isnull=True,classe=classe).select_related('user')
            query2=Eleve.objects.filter(groupe2__isnull=True,classe=classe).select_related('user')
        else:
            query=Eleve.objects.filter(classe=classe).filter(Q(groupe__isnull=True)|Q(groupe=groupe)).select_related('user')
            query2=Eleve.objects.filter(classe=classe).filter(Q(groupe2__isnull=True)|Q(groupe2=groupe)).select_related('user')
        groupes_pris = set(Groupe.objects.filter(classe=classe).values_list('nom',flat = True))
        groupes = set(range(1,31)) - groupes_pris
        if groupe: # si c'est une modification
            groupes |= {groupe.nom}
        groupes = sorted(groupes)
        groupes = zip(groupes,groupes)
        self.fields['nom'] = forms.ChoiceField(label="nom",choices=groupes)
        self.fields['idem'] = forms.BooleanField(label="recopier les élèves au second semestre",required = False)
        self.fields['eleve0'] = forms.ModelChoiceField(label="Premier élève",queryset=query,empty_label="Élève fictif",required=False)
        self.fields['eleve1'] = forms.ModelChoiceField(label="Deuxième élève",queryset=query,empty_label="Élève fictif",required=False)
        self.fields['eleve2'] = forms.ModelChoiceField(label="Troisième élève",queryset=query,empty_label="Élève fictif",required=False)
        self.fields['eleve20'] = forms.ModelChoiceField(label="Premier élève",queryset=query2,empty_label="Élève fictif",required=False)
        self.fields['eleve21'] = forms.ModelChoiceField(label="Deuxième élève",queryset=query2,empty_label="Élève fictif",required=False)
        self.fields['eleve22'] = forms.ModelChoiceField(label="Troisième élève",queryset=query2,empty_label="Élève fictif",required=False)
        query = Matiere.objects.filter(matieresclasse=classe,lv=1).distinct()
        if query.exists():
            self.fields['lv11'] = MatiereChoiceField(label="LV1",queryset=query,empty_label="Tout",required=False)
            self.fields['lv12'] = MatiereChoiceField(label="LV1",queryset=query,empty_label="Tout",required=False)
        query = Matiere.objects.filter(matieresclasse=classe,lv=2).distinct()
        if query.exists():
            self.fields['lv21'] = MatiereChoiceField(label="LV2",queryset=query,empty_label="Tout",required=False)
            self.fields['lv22'] = MatiereChoiceField(label="LV2",queryset=query,empty_label="Tout",required=False)
        options = {classe.option1.pk if classe.option1 is not None else None, classe.option2.pk if classe.option2 is not None else None} - {None}
        query = Matiere.objects.filter(pk__in=options).distinct()
        if query.exists():
            self.fields['option'] = MatiereChoiceField(label="Option",queryset=query,empty_label="Tout",required=False)

    def clean_nom(self):
        """Validation du champ nom (unicité pour une classe donnée)"""
        data = self.cleaned_data['nom']
        query = Groupe.objects.filter(nom=data,classe=self.classe)
        if self.groupe: # si c'est une modification, on exclut de la requête le groupe en question
            query=query.exclude(pk=self.groupe.pk)
        if query.exists():
            raise ValidationError(
            "le nom %(value)s est déjà pris",
            code='uniqueness violation',
            params={'value': data},
            )
        return data

    def clean(self):
        """validation du formulaire. S'il y a deux fois le même élève (non fictif) on lève une ValidationError"""
        eleves = [self.cleaned_data['eleve{}'.format(i)] for i in range(3) if 'eleve{}'.format(i) in self.cleaned_data and self.cleaned_data['eleve{}'.format(i)]]
        eleves2 = [self.cleaned_data['eleve2{}'.format(i)] for i in range(3) if 'eleve2{}'.format(i) in self.cleaned_data and self.cleaned_data['eleve2{}'.format(i)]]
        if len(eleves) > len(set(eleves)) or len(eleves2) > len(set(eleves2)): # s'il y a doublon
            raise ValidationError("Un élève ne peut apparaître qu'une fois dans un groupe",code="uniqueness violation")

    def save(self):
        """sauvegarde en base de données les données du formulaire"""
        if self.groupe: # dans le cas d'une modification
            groupe=self.groupe
            Eleve.objects.filter(groupe=groupe).update(groupe=None) # on efface les groupes des -anciens- élèves du groupe
            Eleve.objects.filter(groupe2=groupe).update(groupe2=None)
            Groupe.objects.filter(pk=groupe.pk).update(nom=self.cleaned_data['nom']) # on met à jour le nom du groupe
        else: # sinon on crée un nouveau groupe
            groupe=Groupe(nom=self.cleaned_data['nom'],classe=self.classe)
            groupe.save()
        Eleve.objects.filter(pk__in=[self.cleaned_data['eleve{}'.format(i)].pk for i in range(3) if self.cleaned_data['eleve{}'.format(i)] is not None]).update(groupe=groupe) # maj des groupes
        Eleve.objects.filter(pk__in=[self.cleaned_data['eleve2{}'.format(i)].pk for i in range(3) if self.cleaned_data['eleve2{}'.format(i)] is not None]).update(groupe2=groupe) 


class GroupeForm(forms.Form):
    def __init__(self,classe,groupe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.groupe=groupe
        self.classe=classe
        if not groupe:
            query=Eleve.objects.filter(groupe__isnull=True,classe=classe).select_related('user')
        else:
            query=Eleve.objects.filter(classe=classe).filter(Q(groupe__isnull=True)|Q(groupe=groupe)).select_related('user')
        groupes_pris = set(Groupe.objects.filter(classe=classe).values_list('nom',flat = True))
        groupes = set(range(1,31)) - groupes_pris
        if groupe: # si c'est une modification
            groupes |= {groupe.nom}
        groupes = sorted(groupes)
        groupes = zip(groupes,groupes)
        self.fields['nom'] = forms.ChoiceField(label="nom",choices=groupes)
        self.fields['eleve0'] = forms.ModelChoiceField(label="Premier élève",queryset=query,empty_label="Élève fictif",required=False)
        self.fields['eleve1'] = forms.ModelChoiceField(label="Deuxième élève",queryset=query,empty_label="Élève fictif",required=False)
        self.fields['eleve2'] = forms.ModelChoiceField(label="Troisième élève",queryset=query,empty_label="Élève fictif",required=False)
        query = Matiere.objects.filter(matieresclasse=classe,lv=1).distinct()
        if query.exists():
            self.fields['lv1'] = MatiereChoiceField(label="LV1",queryset=query,empty_label="Tout",required=False)
        query = Matiere.objects.filter(matieresclasse=classe,lv=2).distinct()
        if query.exists():
            self.fields['lv2'] = MatiereChoiceField(label="LV2",queryset=query,empty_label="Tout",required=False)
        
    def clean_nom(self):
        """Validation du champ nom (unicité pour une classe donnée)"""
        data = self.cleaned_data['nom']
        query = Groupe.objects.filter(nom=data,classe=self.classe)
        if self.groupe: # si c'est une modification, on exclut de la requête le groupe en question
            query=query.exclude(pk=self.groupe.pk)
        if query.exists():
            raise ValidationError(
            "le nom %(value)s est déjà pris",
            code='uniqueness violation',
            params={'value': data},
            )
        return data

    def clean(self):
        """validation du formulaire. S'il y a deux fois le même élève (non fictif) on lève une ValidationError"""
        eleves = [self.cleaned_data['eleve{}'.format(i)] for i in range(3) if 'eleve{}'.format(i) in self.cleaned_data and self.cleaned_data['eleve{}'.format(i)]]
        if len(eleves) > len(set(eleves)): # s'il y a doublon
            raise ValidationError("Un élève ne peut apparaître qu'une fois dans un groupe",code="uniqueness violation")

    def save(self):
        """sauvegarde en base de données les données du formulaire"""
        if self.groupe: # dans le cas d'une modification
            groupe=self.groupe
            Eleve.objects.filter(groupe=groupe).update(groupe=None) # on efface les groupes des -anciens- élèves du groupe
            Groupe.objects.filter(pk=groupe.pk).update(nom=self.cleaned_data['nom']) # on met à jour le nom du groupe
        else: # sinon on crée un nouveau groupe
            groupe=Groupe(nom=self.cleaned_data['nom'],classe=self.classe)
            groupe.save()
        Eleve.objects.filter(pk__in=[self.cleaned_data['eleve{}'.format(i)].pk for i in range(3) if self.cleaned_data['eleve{}'.format(i)] is not None]).update(groupe=groupe) # maj des groupes

class CreneauForm(forms.ModelForm):
    class Meta:
        model = Creneau
        fields = ['jour','heure','salle']

class SemaineForm(forms.Form):
    try:
        query=Semaine.objects.order_by('lundi')
        semin=forms.ModelChoiceField(queryset=query, empty_label=None,initial=query[0])
        semax=forms.ModelChoiceField(queryset=query, empty_label=None,initial=query[query.count()-1])
    except Exception:
        semin=forms.ModelChoiceField(queryset=Semaine.objects.none(), empty_label=None)
        semax=forms.ModelChoiceField(queryset=Semaine.objects.none(), empty_label=None)

class ColleForm(forms.Form):
    def __init__(self,classe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        query1=classe.matieres.all()
        query2=Colleur.objects.none()
        query3=Groupe.objects.filter(classe=classe).order_by('nom')
        query4=Eleve.objects.filter(classe=classe).all()
        try:
            self.fields['matiere']=forms.ModelChoiceField(queryset=query1,empty_label=None,initial=query1[0])
        except Exception:
            self.fields['matiere']=forms.ModelChoiceField(queryset=query1,empty_label=None)
        self.fields['colleur']=forms.ModelChoiceField(queryset=query2,empty_label=None)
        self.fields['GSC']=forms.ChoiceField(label="Groupe/Solo/Classe",choices=[(0,'Groupe'),(1,'Solo'),(2,'Classe')], widget=forms.RadioSelect)
        try:
            self.fields['groupe']=forms.ModelChoiceField(queryset=query3,empty_label=None,initial=query3[0])
        except Exception:
            self.fields['groupe']=forms.ModelChoiceField(queryset=query3,empty_label=None)
        try:
            self.fields['eleve']=forms.ModelChoiceField(queryset=query4,empty_label=None,initial=query4[0])
        except Exception:
            self.fields['eleve']=forms.ModelChoiceField(queryset=query4,empty_label=None)
        DUREE=[(1,"1 semaine")]+list(zip(range(2,31),["{} semaines".format(i) for i in range (2,31)]))
        PERMUTATION=[(i,"de {} en {}".format(i,i)) for i in range(1,21)]
        FREQUENCE=[(i,"une semaine sur {}".format(i)) for i in (1,2,3,4,8)]
        self.fields['duree']=forms.ChoiceField(label="Durée",choices=DUREE)
        self.fields['frequence']=forms.ChoiceField(label="Fréquence",choices=FREQUENCE)
        self.fields['permutation']=forms.ChoiceField(label="Permutation des groupes",choices=PERMUTATION)

class EleveForm(forms.Form):
    def __init__(self,classe,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['eleve'] = forms.ModelChoiceField(label = "Élève",queryset=Eleve.objects.filter(classe=classe),empty_label=None)


class MatiereECTSForm(forms.ModelForm):
    class Meta:
        model = MatiereECTS
        fields = ['nom','precision','profs','semestre1','semestre2']

    def clean(self):
        """validation du formulaire. On vérifie qu'au moins un des champs semestre1 ou semetre2 est non nul et que le triplet
        classe/nom/precision, sans compter la casse, est unique"""
        if self.cleaned_data['semestre1'] is None and self.cleaned_data['semestre2'] is None:
            raise ValidationError("au moins un des champs de coefficient doit être précisé")
        query = MatiereECTS.objects.filter(classe=self.instance.classe,nom__iexact=self.cleaned_data['nom'],precision__iexact=self.cleaned_data['precision'])
        if self.instance.pk: # si le pk existe déjà et donc qu'on procède à une modification
            query=query.exclude(pk=self.instance.pk)
        if query.exists():
            raise ValidationError("le couple nom/précision est unique",code="uniqueness violation")

class SelectEleveForm(forms.Form):
    def __init__(self,classe,*args, **kwargs):
        super().__init__(*args, **kwargs)
        query = Eleve.objects.filter(classe=classe).select_related('user').order_by('user__last_name','user__first_name')
        self.fields['eleve'] = forms.ModelMultipleChoiceField(queryset=query,required=True,widget = forms.CheckboxSelectMultiple)
        self.fields['eleve'].empty_label=None

class NoteEleveForm(forms.Form):
        semestre1 = forms.ChoiceField(choices=[(None,'---')]+list(enumerate("ABCDEF")),required=False)
        semestre2 = forms.ChoiceField(choices=[(None,'---')]+list(enumerate("ABCDEF")),required=False)

class NoteEleveFormSet(forms.BaseFormSet):
    def __init__(self,chaine_eleves=[],matiere=None,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.chaine_eleves=chaine_eleves
        self.matiere=matiere
                
    def save(self):
        """Sauvegarde (mise à jour) en BDD les notes ECTS du formulaire"""
        for form,eleve in zip(self,self.chaine_eleves):
            if 'semestre1' in form.cleaned_data:
                if form.cleaned_data['semestre1'] == "":
                    NoteECTS.objects.filter(semestre=1,matiere=self.matiere,eleve=eleve).delete()
                elif form.cleaned_data['semestre1'] in "012345":
                    NoteECTS.objects.update_or_create(defaults={'eleve':eleve,'matiere':self.matiere,'semestre':1,'note':form.cleaned_data['semestre1']},semestre=1,matiere=self.matiere,eleve=eleve)
            if 'semestre2' in form.cleaned_data:
                if form.cleaned_data['semestre2'] == "":
                    NoteECTS.objects.filter(semestre=2,matiere=self.matiere,eleve=eleve).delete()
                elif form.cleaned_data['semestre2'] in "012345":
                    NoteECTS.objects.update_or_create(defaults={'eleve':eleve,'matiere':self.matiere,'semestre':2,'note':form.cleaned_data['semestre2']},semestre=2,matiere=self.matiere,eleve=eleve)

class NoteGlobaleEleveForm(forms.Form):
        note_globale = forms.ChoiceField(choices=[(None,'---')]+list(enumerate("ABCDEF")),required=False)

class NoteGlobaleEleveFormSet(forms.BaseFormSet):
    def __init__(self,annee,chaine_eleves=[],*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.chaine_eleves=chaine_eleves
        self.annee = annee
                
    def save(self):
        """Sauvegarde (mise à jour) en BDD les notes ECTS du formulaire"""
        for form,eleve in zip(self,self.chaine_eleves):
            if 'note_globale' in form.cleaned_data:
                if form.cleaned_data['note_globale'] == "":
                    NoteGlobaleECTS.objects.filter(annee=self.annee,eleve=eleve).delete()
                elif form.cleaned_data['note_globale'] in "012345":
                    NoteGlobaleECTS.objects.update_or_create(defaults={'eleve':eleve,'annee':self.annee,'note':form.cleaned_data['note_globale']},eleve=eleve,annee=self.annee)

class ECTSForm(forms.Form):
    def __init__(self,classe,*args,**kwargs):
        super().__init__(*args,**kwargs)
        tree=etree.parse(join(RESOURCES_ROOT,'classes.xml')).getroot()
        types={x.get("type")+'_'+x.get("annee") for x in tree.findall("classe")}
        types = list(types)
        types.sort()
        LISTE_CLASSES=[]
        default = None
        for typ in types:
            style,annee=typ.split("_")
            LISTE_CLASSES.append((style+" "+annee+"è"+("r" if annee=="1" else "m")+"e année",sorted((lambda y,z:[(x.get("nom")+"_"+x.get("annee"),x.get("nom")) for x in z.findall("classe") if [x.get("type"),x.get("annee")] == y.split("_")])(typ,tree))))
        for x in tree.findall("classe"):
            if classe.nom.lower()[:len(x.get("nom"))] == x.get("nom").lower() and classe.annee == int(x.get("annee")):
                default=x.get("nom")+"_"+x.get("annee")
        imagesProviseur=(join(RESOURCES_ROOT,'proviseur.png'),join(RESOURCES_ROOT,'proviseur.jpg'))
        imagesProviseurAdjoint=(join(RESOURCES_ROOT,'proviseuradjoint.png'),join(RESOURCES_ROOT,'proviseuradjoint.jpg'))
        self.fields['classe'] = forms.ChoiceField(label="filière",choices=LISTE_CLASSES,initial=default)
        self.fields['date'] = forms.DateField(label="Date d'édition",input_formats=['%d/%m/%Y','%j/%m/%Y','%d/%n/%Y','%j/%n/%Y'],widget=forms.TextInput(attrs={'placeholder': 'jj/mm/aaaa'}),initial=date.today().strftime('%d/%m/%Y'))
        self.fields['signature'] = forms.ChoiceField(label="signature/tampon par:",choices=(['Proviseur']*2,['Proviseur adjoint']*2))
        self.fields['anneescolaire'] = forms.ChoiceField(label="année scolaire",choices=[(x+1,"{}-{}".format(x,x+1)) for x in range(date.today().year-10,date.today().year+10)],initial=date.today().year)
        if classe.annee == 2 and "*" in classe.nom:
            self.fields['etoile'] = forms.BooleanField(label="classe étoile",required=False,initial=True)
        else:
            self.fields['etoile'] = forms.BooleanField(label="classe étoile",required=False)
        if any(isfile(x) for x in imagesProviseur+imagesProviseurAdjoint): # si au moins un des tampons est présent
            self.fields['tampon'] = forms.BooleanField(label='incruster le tampon/la signature',required=False)

class SelectEleveNoteForm(forms.Form):
    def __init__(self,classe,groupeeleve,*args,**kwargs):
        super().__init__(*args,**kwargs)     
        if groupeeleve == 1:
            query = iter(Eleve.objects.filter(classe=classe).annotate(groupe_nom=Coalesce('groupe__nom',Value(100))).select_related('user').order_by('groupe_nom','user__last_name','user__first_name'))
            listeGroupes = Groupe.objects.filter(classe=classe).annotate(nb=Count('groupeeleve')).order_by('nom')
        elif groupeeleve == 2:
            query = iter(Eleve.objects.filter(classe=classe).annotate(groupe_nom=Coalesce('groupe2__nom',Value(100))).select_related('user').order_by('groupe_nom','user__last_name','user__first_name'))
            listeGroupes = Groupe.objects.filter(classe=classe).annotate(nb=Count('groupe2eleve')).order_by('nom')
        else:
            query = iter(Eleve.objects.filter(classe=classe).select_related('user').order_by('user__last_name','user__first_name'))
            listeGroupes = []
        choices_groupe = [(groupe.pk, "Groupe {}".format(groupe.nom)) for groupe in listeGroupes]
        choices = [(0,"Élève fictif")]
        indexFictif = -1
        for x in listeGroupes:
            for i in range(x.nb):
                eleve = next(query)
                choices.append((eleve.pk,str(eleve)))
            for j in range(3-x.nb):
                choices.append((indexFictif,"Élève fictif"))
                indexFictif -= 1
        modulo = 0
        while True:
            try:
                eleve = next(query)
                choices.append((eleve.pk,str(eleve)))
                modulo += 1
            except Exception:
                break
        for j in range(3 - (modulo % 3)):
            choices.append((indexFictif,"Élève fictif"))
            indexFictif -= 1
        self.tailleGroupes = [x.nb for x in listeGroupes]
        self.fields['groupe'] = forms.MultipleChoiceField(choices=choices_groupe, widget = forms.CheckboxSelectMultiple, required = False)
        self.fields['eleve'] = forms.MultipleChoiceField(choices=choices, widget = forms.CheckboxSelectMultiple, required = True)

    def clean_eleve(self):
        data = self.cleaned_data['eleve']
        if len(data) > 3:
            raise ValidationError("Vous ne pouvez pas noter plus de 3 élèves sur un même créneau")
        return data

class NoteElevesHeadForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['semaine','jour','heure','rattrapee','date_colle']

    def __init__(self, matiere, colleur, classe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matiere = matiere
        self.colleur = colleur
        self.classe = classe
        self.fields['date_colle'].widget=SelectDateWidget(years=[date.today().year+i-1 for i in range(10)])
    
class NoteElevesTailForm(forms.Form):
    def __init__(self, eleve, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eleve = eleve
        LISTE_NOTE=[(21,"n.n"),(22,"Abs")]
        LISTE_NOTE.extend(zip(range(21),range(21)))
        self.fields['note'] = forms.ChoiceField(choices=LISTE_NOTE)
        self.fields['commentaire'] = forms.CharField(widget=forms.Textarea, required = False)

class NoteElevesFormset(forms.BaseFormSet):
    def __init__(self, headForm, eleves, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.headForm = headForm
        self.eleves = eleves

    def get_form_kwargs(self, index):
        """déterminer l'argument nommé 'eleve' à passer en paramètre du formulaire"""
        kwargs = super().get_form_kwargs(index)
        if self.eleves:
            kwargs['eleve'] = self.eleves[index]
        else:
            kwargs['eleve'] = None
        return kwargs

    def clean(self):
        """Vérifie que le colleur n'aura au final pas plus de 3 notes sur ce créneau et qu'il n'a pas déjà collé un des élève cette semaine dans cette matière"""
        if not self.headForm.is_valid(): # on valide le formulaire de tête
            raise ValidationError("erreur dans dans la semaine/date/jeure/jour")
        if not self.headForm.cleaned_data['rattrapee']:
            self.headForm.cleaned_data['date_colle']=self.headForm.cleaned_data['semaine'].lundi+timedelta(days=int(self.headForm.cleaned_data['jour']))
        nbNotesColleur=Note.objects.filter(date_colle=self.headForm.cleaned_data['date_colle'],colleur=self.headForm.colleur,heure=self.headForm.cleaned_data['heure'])
        if self.headForm.instance.pk: # si on modifie une note:
            nbNotesColleur = nbNotesColleur.exclude(pk = self.headForm.instance.pk)
        nbNotesColleur = nbNotesColleur.count()
        if nbNotesColleur + len(self.eleves) > 3:
            raise ValidationError("Vous avez trop de notes sur ce créneau horaire")
        if self.headForm.matiere.temps == 20:
            nbNotesEleve=Note.objects.filter(semaine=self.headForm.cleaned_data['semaine'],matiere=self.headForm.matiere,colleur=self.headForm.colleur,eleve__in=self.eleves)
            if self.headForm.instance.pk: # si on modifie une note:
                nbNotesEleve = nbNotesEleve.exclude(pk = self.headForm.instance.pk)
            nbNotesEleve = nbNotesEleve.exists()
            if nbNotesEleve:
                raise ValidationError("Vous avez déjà noté un des élèves cette semaine dans cette matière")

    def save(self):
        """sauvegarde en base de données les notes"""
        note = self.headForm.instance
        if note.pk: # si on modifie une note
            for form in self:
                note.note = form.cleaned_data['note']
                note.commentaire = form.cleaned_data['commentaire']
                note.eleve = form.eleve
                note.classe = self.headForm.classe
                note.matiere = self.headForm.matiere
                note.colleur = self.headForm.colleur
                note.update()
            note.save()
        else:
            notes = []
            for form in self:
                notebis = copy(note)
                notebis.note = form.cleaned_data['note']
                notebis.commentaire = form.cleaned_data['commentaire']
                notebis.eleve = form.eleve
                notebis.classe = self.headForm.classe
                notebis.matiere = self.headForm.matiere
                notebis.colleur = self.headForm.colleur
                notebis.update()
                notes.append(notebis)
            Note.objects.bulk_create(notes) # on sauvegarde toutes les notes en une seule requête

class DateInput(forms.DateInput):
    input_type = 'date'

class DevoirForm(forms.ModelForm):
    class Meta:
        model = Devoir
        fields=['numero','detail','a_rendre_jour','a_rendre_heure','fichier','corrige']
        widgets = {'a_rendre_jour': DateInput()}

    def __init__(self, matiere, classe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matiere = matiere
        self.classe = classe

    def clean(self):
        """Vérifie la condition d'unicité de numéro/classe/matière"""
        query = Devoir.objects.filter(numero = self.cleaned_data['numero'], matiere = self.matiere, classe = self.classe)
        if self.instance:
            query = query.exclude(pk = self.instance.pk)
        if query.exists():
            raise ValidationError("il existe déjà un devoir n°{} dans la classe {} en {}".format(self.cleaned_data['numero'], self.classe, self.matiere))

class CopieForm(forms.ModelForm):
    class Meta:
        model = DevoirCorrige
        fields = ['fichier', 'commentaire']

    def save(self, *args, **kwargs):
        if self.cleaned_data['fichier'] in (False, None): # si on efface la copie rendue, ou si on ne soumet aucun fichier
            if self.instance.id:
                self.instance.delete()
        else: # sinon on applique la sauvegarde classique
            super().save()

class CopiesForm(forms.Form):
    def __init__(self, devoir, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.devoir = devoir
        self.fields['fichier'] = forms.FileField(label="fichier zip", help_text="déposer un fichier zip avec les copies corrigées ayant le même nom que les copies ramassées.\
         Si vous déposez une copie corrigée pour un élève qui en a déjà une, elle écrasera la précédente. Si un nom de fichier ne correspond pas à un nom de copie ramassée, il sera ignoré.")

    def clean_fichier(self):
        fichier =  self.cleaned_data['fichier']
        if fichier.content_type != 'application/zip': # on vérifie qu'on a un fichier zip
            raise ValidationError("le fichier n'est pas un fichier zip valide")
        with ZipFile(fichier) as myzip:
            for info in myzip.infolist():
                if info.filename[-4:] != ".pdf":
                    raise ValidationError("le fichier n'est pas un fichier pdf")
                if info.file_size > DevoirCorrige.fichier.field.max_upload_size:
                    raise ValidationError("le fichier {} est trop volumineux".format(info.filename))
        return fichier

    def save(self):
        with ZipFile(self.cleaned_data['fichier']) as myzip:
            nomfichiers = myzip.namelist() # on récupère les noms des fichiers
            for nomfichier in nomfichiers: # pour chaque fichier, on cherche une correspondance, et si on trouve, on enregistre en écrasant
                copie = DevoirRendu.objects.filter(devoir=self.devoir, fichier = join("devoir", nomfichier)).first()
                if copie: # si le devoir a été rendu
                    copiecorrigee = DevoirCorrige.objects.filter(devoir = self.devoir, eleve = copie.eleve).first()
                    if copiecorrigee:
                        copiecorrigee.delete()
                    with myzip.open(nomfichier) as myfile:
                        copiecorrigee = DevoirCorrige(eleve = copie.eleve, devoir = self.devoir, commentaire = "")
                        copiecorrigee.fichier.save(copiecorrigee.update_name() , ContentFile(myfile.read()), save = False)
                        copiecorrigee.save()

class ColloscopeImportForm(forms.Form):
    def __init__(self, classe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classe = classe
        self.entete = []
        self.colles = []
        self.semaines = []
        self.fields['fichier'] = forms.FileField(label="Fichier csv",required=True)

    def clean(self):
        def indice(subs,i):
            if subs is None:
                return None
            if subs[0] != 'so':
                if i == 0:
                    return subs
                else:
                    return None
            if len(subs[1]) > i:
                return (subs[0],subs[1][i])
            return None 
        matieres = {unidecode(matiere.nom.lower()) + ("(lv{})".format(matiere.lv) if matiere.lv else ""): matiere for matiere in Matiere.objects.filter(matieresclasse=self.classe).distinct()}
        colleurs = {(unidecode(colleur.user.last_name.lower()), unidecode(colleur.user.first_name.lower())): (colleur, set(colleur.matieres.values_list("pk",flat = True))) for colleur in Colleur.objects.filter(classes=self.classe)}
        groupes = {groupe.nom: groupe for groupe in Groupe.objects.filter(classe = self.classe)}
        jours = {"lu":0, "ma":1, "me":2, "je":3, "ve":4, "sa":5, "di":6}
        p1 = re.compile('\\d+a?b?c?')
        p2 = re.compile('\\d+')
        p3 = re.compile('a?b?c?')
        dico = {'a':0,'b':1,'c':2}
        if self.classe.semestres:
            semestre2 = Config.objects.get_config().semestre2
        else:
            semestre2 = 100
        try:
            with TextIOWrapper(self.cleaned_data['fichier'].file,encoding = 'utf-8-sig',newline='') as csvfile:
                colloscopereader = csv.reader(csvfile, delimiter=',')
                self.entete = next(colloscopereader)
                try:
                    self.semaines = [Semaine.objects.get(numero = p2.search(x).group()) for x in self.entete[5:]]
                except Exception:
                    raise ValidationError("erreur dans les numéros de semaine (il faut uniquement des nombres précédés de la lettre 'S')")
                taille = len(self.entete)
                if taille <= 5:
                    raise ValidationError("première ligne du fichier trop courte!")
                self.colles = []
                for row in colloscopereader:
                    maxnum = 0
                    if len(row) != taille:
                        raise ValidationError("longueurs de lignes inconsistantes")
                    mat = unidecode(row[0].lower())
                    if mat in matieres:
                        colle = [matieres[mat]]
                    else:
                        raise ValidationError("{} n'est pas une matière de la classe de {}".format(mat,self.classe.nom))
                    colleur = (unidecode(row[1].lower()),unidecode(row[2].lower()))
                    if colleur in colleurs and colle[0].pk in colleurs[colleur][1]:
                        colle.append(colleurs[colleur][0])
                    else:
                        raise ValidationError("{} n'est pas colleur de {} dans la matière {}".format(" ".join(colleur), self.classe.nom, mat))
                    creneau = row[3].split(" ")
                    if creneau[0] not in jours:
                        raise ValidationError("{} ne correspond à aucun jour de la semaine".format(creneau[0]))
                    else:
                        colle.append(jours[creneau[0]])
                    heure = creneau[1].split("h")
                    try:
                        minutes = 60*int(heure[0]) + int(heure[1])
                    except Exception:
                        raise ValidationError("l'heure {} est mal formatée".format(creneau[1]))
                    else:
                        colle.append(minutes)
                    colle.append(row[4])
                    eleves = dict(reversed(x) for x in self.classe.loginsEleves())
                    for (col,semaine) in zip(row[5:],self.semaines):
                        if col == "": # colle vide
                            colle.append(None)
                        elif col.isdigit() or ";" in col: # colle groupe(s)
                            groups = []
                            for x in p2.findall(col):
                                if x.isdigit() and int(x) in groupes:
                                    groups.append(groupes[int(x)])
                                else:
                                    raise ValidationError("le groupe {} n'existe pas".format(col))
                            colle.append(('gr',groups))
                        elif col.lower() == self.classe.nom.lower(): # colle classe
                            colle.append(('cl',self.classe))
                        else: # colle élève 
                            if col in eleves:
                                colle.append(('so',eleves[col]))
                            elif col[0].isdigit():
                                sgroupes = p1.findall(col)
                                eleves_tot = []
                                for sgroupe in sgroupes:
                                    groupe_numero = int(p2.search(sgroupe).group())
                                    eleves_position = [x for x in p3.findall(sgroupe) if x != '']
                                    if eleves_position == []:
                                        eleves_position = "abc"
                                    else:
                                        eleves_position = eleves_position[0]
                                    groupe = Groupe.objects.filter(nom=groupe_numero,classe=self.classe)
                                    if groupe.exists():
                                        groupe = groupe.get()
                                        if semaine.numero < semestre2:
                                            eleves = list(groupe.groupeeleve.all())
                                        else:
                                            eleves = list(groupe.groupe2eleve.all())
                                        for p in eleves_position:
                                            pos = dico[p]
                                            if pos < len(eleves):
                                                eleves_tot.append(eleves[pos])
                                if len(eleves_tot) > maxnum:
                                    maxnum = len(eleves_tot)
                                colle.append(('so',eleves_tot))
                            else:
                                raise ValidationError("{} n'est le login d'aucun élève de {}".format(col,self.classe))
                    if maxnum:
                        for i in range(maxnum):
                            souscolle = colle[:5] + [indice(element,i) for element in colle[5:]]
                            self.colles.append(souscolle)
                    else:
                        self.colles.append(colle)
        except ValidationError as e:
            raise ValidationError(str(e))
        except Exception as e:
            raise ValidationError("Le fichier doit être un fichier CSV valide, encodé en UTF-8")

    def save(self):
        # on efface les colles des semaines présentes
        Colle.objects.filter(semaine__in = self.semaines,creneau__classe = self.classe).delete()
        for colles in self.colles:
            colles_a_sauver = []
            # on cherche un créneau où officie déjà le colleur, dans la même matière, dans la même salle, sinon on le crée
            creneau = Creneau.objects.filter(jour=colles[2],heure=colles[3],salle=colles[4],classe=self.classe,colle__matiere=colles[0],colle__colleur=colles[1])
            if creneau.exists() and not Colle.objects.filter(creneau = creneau[0],semaine__in =self.semaines).exists():
                creneau = creneau[:1][0]
            else:
                creneau = Creneau.objects.filter(jour=colles[2],heure=colles[3],salle=colles[4],classe=self.classe,colle__isnull=True)
                if creneau.exists():
                    creneau = creneau[:1][0]
                else:
                    creneau = Creneau(jour=colles[2],heure=colles[3],salle=colles[4],classe=self.classe)
                    creneau.save()
            for col, semaine in zip(colles[5:],self.semaines):
                if col is not None:
                    gsc, data = col
                    if gsc == "gr":
                        for groupe in data:
                            colles_a_sauver.append(Colle(creneau = creneau, colleur = colles[1],matiere = colles[0], groupe = groupe, eleve = None, classe = self.classe, semaine = semaine))
                    elif gsc == "so":
                        colles_a_sauver.append(Colle(creneau = creneau, colleur = colles[1],matiere = colles[0], groupe = None, eleve = data, classe = self.classe, semaine = semaine))
                    else:
                        colles_a_sauver.append(Colle(creneau = creneau, colleur = colles[1],matiere = colles[0], groupe = None, eleve = None, classe = self.classe, semaine = semaine))
            Colle.objects.bulk_create(colles_a_sauver)


class TDForm(forms.ModelForm):
    class Meta:
        model = TD
        fields=['numero','detail','fichier']

    def __init__(self, matiere, classe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matiere = matiere
        self.classe = classe

    def clean(self):
        """Vérifie la condition d'unicité de numéro/classe/matière"""
        query = TD.objects.filter(numero = self.cleaned_data['numero'], matiere = self.matiere, classe = self.classe)
        if self.instance:
            query = query.exclude(pk = self.instance.pk)
        if query.exists():
            raise ValidationError("il existe déjà un td n°{} dans la classe {} en {}".format(self.cleaned_data['numero'], self.classe, self.matiere))

class CoursForm(forms.ModelForm):
    class Meta:
        model = Cours
        fields=['numero','detail','fichier']

    def __init__(self, matiere, classe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matiere = matiere
        self.classe = classe

    def clean(self):
        """Vérifie la condition d'unicité de numéro/classe/matière"""
        query = Cours.objects.filter(numero = self.cleaned_data['numero'], matiere = self.matiere, classe = self.classe)
        if self.instance:
            query = query.exclude(pk = self.instance.pk)
        if query.exists():
            raise ValidationError("il existe déjà un cours n°{} dans la classe {} en {}".format(self.cleaned_data['numero'], self.classe, self.matiere))

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields=['titre','detail','fichier']

    def __init__(self, matiere, classe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matiere = matiere
        self.classe = classe

    def clean(self):
        """Vérifie la condition d'unicité de numéro/classe/matière"""
        query = Document.objects.filter(titre = self.cleaned_data['titre'], matiere = self.matiere, classe = self.classe)
        if self.instance:
            query = query.exclude(pk = self.instance.pk)
        if query.exists():
            raise ValidationError("il existe déjà un document nommé '{}' dans la classe {} en {}".format(self.cleaned_data['titre'], self.classe, self.matiere))

   
        
