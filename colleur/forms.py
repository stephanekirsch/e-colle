#-*- coding: utf-8 -*-
from django import forms
from accueil.models import Colleur, Note, Semaine, Programme, Eleve, Creneau, Matiere, Groupe, MatiereECTS, NoteECTS
from django.db.models import Q, Count
from datetime import date, timedelta
from django.forms.widgets import SelectDateWidget
from django.core.exceptions import ValidationError
from xml.etree import ElementTree as etree
from ecolle.settings import RESOURCES_ROOT, MEDIA_ROOT, IMAGEMAGICK
from os.path import isfile,join
from os import remove
from copy import copy

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
        query = Programme.objects.filter(semaine__in=semaines)
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

class GroupeForm(forms.Form):
    def __init__(self,classe,groupe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.groupe=groupe
        self.classe=classe
        if not groupe:
            query=Eleve.objects.filter(groupe__isnull=True,classe=classe).select_related('user')
        else:
            query=Eleve.objects.filter(classe=classe).filter(Q(groupe__isnull=True)|Q(groupe=groupe)).select_related('user')
        self.fields['nom'] = forms.ChoiceField(label="nom",choices=zip(range(1,21),range(1,21)))
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
        self.fields['etoile'] = forms.BooleanField(label="classe étoile",required=False)
        if any(isfile(x) for x in imagesProviseur+imagesProviseurAdjoint): # si au moins un des tampons est présent
            self.fields['tampon'] = forms.BooleanField(label='incruster le tampon/la signature',required=False)

class SelectEleveNoteForm(forms.Form):
    def __init__(self,classe,*args,**kwargs):
        super().__init__(*args,**kwargs)
        query = iter(Eleve.objects.filter(classe=classe).select_related('user').order_by('groupe__nom','user__last_name','user__first_name'))
        listeGroupes = Groupe.objects.filter(classe=classe).annotate(nb=Count('groupeeleve')).order_by('nom')
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
        
