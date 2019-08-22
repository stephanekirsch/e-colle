#-*- coding: utf-8 -*-
from django import forms
from accueil.models import Classe, Matiere, Etablissement, Semaine, Colleur, Eleve, JourFerie, User, Prof, Config,  Note,  Colle, RestrictedImageField
from django.forms.widgets import SelectDateWidget
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q
from ecolle.settings import RESOURCES_ROOT, MEDIA_ROOT
from xml.etree import ElementTree as etree
from random import choice
from os import path, remove
from datetime import date, timedelta


class ConfigForm(forms.ModelForm):
    class Meta:
        model = Config
        fields=['nom_etablissement','app_mobile','modif_secret_col','modif_secret_groupe','modif_prof_col','default_modif_col',\
        'modif_prof_groupe','default_modif_groupe','message_eleves','mathjax','ects','nom_adresse_etablissement','ville','academie']

    def save(self):
        Config.objects.all().delete()
        super().save()

class ColleurFormSetMdp(forms.BaseFormSet):
    def clean(self):
        """vérifie si on n'a pas deux identifiants identiques dans le groupe de formulaires"""
        if any(self.errors):
            return
        usernames = [form.cleaned_data['username'] for form in self.forms]
        if len(usernames) != len(set(usernames)):
            raise ValidationError("Deux identifiants identiques dans le formulaire")

    def save(self):
        """Sauvegarde en BDD les colleurs/users du formulaire"""
        # on ne peut pas utiliser bulk_create ici, puisqu'on a besoin des pk pour les relation un-un et many-many
        with transaction.atomic():
            for form in self.forms:
                colleur= Colleur(grade=form.cleaned_data['grade'],etablissement=form.cleaned_data['etablissement'])
                colleur.save() # on sauvegarde en BDD pour avoir un pk, indispensable pour les relations many-many
                # on ajoute les matières et les classes
                colleur.matieres.set(form.cleaned_data['matiere'])
                colleur.classes.set(form.cleaned_data['classe'])
                # on crée le user
                user = User(username=form.cleaned_data['username'],first_name=form.cleaned_data['first_name'].lower(),last_name=form.cleaned_data['last_name'].lower(),email=form.cleaned_data['email'],colleur=colleur)
                user.set_password(form.cleaned_data['password'])
                user.save()     

class ColleurFormSet(forms.BaseFormSet):
    def __init__(self,chaine_colleurs=[],*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.chaine_colleurs=chaine_colleurs

    def get_form_kwargs(self, index):
        """déterminer l'argument nommé 'pk' à passer en paramtre du formulaire"""
        kwargs = super().get_form_kwargs(index)
        if self.chaine_colleurs:
            kwargs['pk'] = self.chaine_colleurs[index].pk
        else:
            kwargs['pk'] = 0
        return kwargs

    def clean(self):
        """vérifie si on n'a pas deux identifiants identiques dans le groupe de formulaires"""
        if any(self.errors):
            return
        usernames = {form.cleaned_data['username'] for form in self.forms}
        if len(usernames) != len(self.chaine_colleurs):
            raise ValidationError("Deux identifiants identiques dans le formulaire")

    def save(self):
        """Sauvegarde (mise à jour) en BDD les colleurs/users du formulaire"""
        with transaction.atomic():
            for colleur,form in zip(self.chaine_colleurs,self.forms):
                colleur.grade=form.cleaned_data['grade']
                colleur.etablissement=form.cleaned_data['etablissement']
                colleur.classes.set(form.cleaned_data['classe'])
                colleur.matieres.set(form.cleaned_data['matiere'])
                colleur.save()
                user=colleur.user
                user.first_name=form.cleaned_data['first_name'].lower()
                user.last_name=form.cleaned_data['last_name'].lower()
                user.email=form.cleaned_data['email']
                user.username = form.cleaned_data['username']
                user.is_active=form.cleaned_data['is_active']
                if form.cleaned_data['password']:
                    user.set_password(form.cleaned_data['password'])
                user.save()

class EleveFormSet(forms.BaseFormSet):
    def __init__(self,chaine_eleves=[],*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.chaine_eleves = chaine_eleves

    def get_form_kwargs(self, index):
        """déterminer l'argument nommé 'pk' à passer en paramtre du formulaire"""
        kwargs = super().get_form_kwargs(index)
        if self.chaine_eleves:
            kwargs['pk'] = self.chaine_eleves[index].pk
        else:
            kwargs['pk'] = 0
        return kwargs

    def clean(self):
        """vérifie si on n'a pas deux identifiants identiques dans le groupe de formulaires"""
        if any(self.errors):
            return
        usernames = {form.cleaned_data['username'] for form in self.forms}
        if len(usernames) != len(self.chaine_eleves):
            raise ValidationError("Deux identifiants identiques dans le formulaire")
        # on efface les photos à effacer:
        super().clean()
        for eleve,form in zip(self.chaine_eleves,self.forms):
            if form.cleaned_data['photo'] is not None: # si on a coché effacer la photo ou si on change de photo
                fichier=path.join(MEDIA_ROOT,eleve.photo.name)
                if path.isfile(fichier):
                    remove(fichier)

    def save(self):
        """Sauvegarde (mise à jour) en BDD les eleves/users du formulaire"""
        with transaction.atomic():
            for eleve,form in zip(self.chaine_eleves,self.forms):
                user=eleve.user
                user.last_name=form.cleaned_data['last_name'].lower()
                user.first_name=form.cleaned_data['first_name'].lower()
                user.email=form.cleaned_data['email']
                user.username = form.cleaned_data['username']
                if form.cleaned_data['password']:
                    user.set_password(form.cleaned_data['password'])
                if eleve.classe != form.cleaned_data['classe']: # si l'élève change effectivement de classe, on le retire de son groupe
                    groupe = eleve.groupe
                    eleve.groupe = None
                    eleve.save()
                    if groupe is not None and not Eleve.objects.filter(groupe=groupe).exists(): # si l'ancien groupe de l'élève est vide, on essaie de l'effacer
                        try:
                            groupe.delete()
                        except Exception:
                            pass
                eleve.classe=form.cleaned_data['classe']
                if form.cleaned_data['photo']:
                    eleve.photo=form.cleaned_data['photo']
                elif form.cleaned_data['photo'] is False:
                    eleve.photo=None
                eleve.ddn=form.cleaned_data['ddn']
                eleve.ldn=form.cleaned_data['ldn']
                eleve.ine=form.cleaned_data['ine']
                eleve.lv1=form.cleaned_data['lv1']
                eleve.lv2=form.cleaned_data['lv2']
                user.save()
                eleve.save()

class EleveFormSetMdp(forms.BaseFormSet):
    def clean(self):
        """vérifie si on n'a pas deux identifiants identiques dans le groupe de formulaires"""
        if any(self.errors):
            return
        usernames = [form.cleaned_data['username'] for form in self.forms]
        if len(usernames) != len(set(usernames)):
            raise ValidationError("Deux identifiants identiques dans le formulaire")

    def save(self):
        with transaction.atomic():
            for form in self.forms:
                user = User(first_name=form.cleaned_data['first_name'].lower(),last_name=form.cleaned_data['last_name'].lower(),email=form.cleaned_data['email'], username = form.cleaned_data['username'])
                user.set_password(form.cleaned_data['password'])
                eleve = Eleve(classe=form.cleaned_data['classe'],photo=form.cleaned_data['photo'],ddn=form.cleaned_data['ddn'],ldn=form.cleaned_data['ldn'],ine=form.cleaned_data['ine'],lv1=form.cleaned_data['lv1'],lv2=form.cleaned_data['lv2'])
                eleve.save()
                user.eleve=eleve
                user.save()

class AdminConnexionForm(forms.Form):
    username = forms.CharField(label="identifiant")
    password = forms.CharField(label="Mot de passe",widget=forms.PasswordInput)


class ClasseForm(forms.ModelForm):
    class Meta:
        model = Classe
        fields=['nom','annee','matieres']
        widgets = {'matieres':forms.CheckboxSelectMultiple}

    def clean_matieres(self):
        # Si la classe existe déjà on vérifie qu'on n'enleve pas une matiere qui a des notes ou des colles dans celle classe.
        matieresPk = {x.pk for x in self.cleaned_data['matieres']}
        matieresNotes = Note.objects.filter(classe=self.instance).values_list('matiere__pk','matiere__nomcomplet').distinct()
        matieresNotesDict = dict(matieresNotes)
        matieresNotesSet = set(matieresNotesDict.keys())
        diff = matieresNotesSet - matieresPk
        if diff:
            raise ValidationError("Vous ne pouvez pas retirer la/les matière(s): {} elles contiennent des notes dans cette classe".format(", ".join(matieresNotesDict[x] for x in diff)))
        matieresColles = set(Colle.objects.filter(creneau__classe=self.instance).values_list('matiere__pk', 'matiere__nomcomplet').distinct())
        matieresCollesDict = dict(matieresColles)
        matieresCollesSet = set(matieresCollesDict.keys())
        diff = matieresCollesSet - matieresPk
        if diff:
            raise ValidationError("Vous ne pouvez pas retirer la/les matière(s): {} elles contiennent des colles dans cette classe".format(", ".join(matieresCollesDict[x] for x in diff)))
        return self.cleaned_data['matieres']

class ClasseGabaritForm(forms.ModelForm):
    gabarit=forms.BooleanField(label="gabarit",required=False)
    tree=etree.parse(path.join(RESOURCES_ROOT,'classes.xml')).getroot()
    types=sorted({x.get("type")+'_'+x.get("annee") for x in tree.findall("classe")})
    LISTE_CLASSES=[]
    for typ in types:
        style,annee=typ.split("_")
        LISTE_CLASSES.append((style+" "+annee+"è"+("r" if annee=="1" else "m")+"e année",sorted((lambda y,z:[(x.get("nom")+"_"+x.get("annee"),x.get("nom")) for x in z.findall("classe") if [x.get("type"),x.get("annee")] == y.split("_")])(typ,tree))))
    classe = forms.ChoiceField(label="classe",choices=LISTE_CLASSES)
    class Meta:
        model = Classe
        fields=['nom','annee','matieres']
        widgets = {'matieres':forms.CheckboxSelectMultiple}

    def save(self):
        if self.cleaned_data['gabarit']: # si on crée une classe via gabarit
            nom,annee=self.cleaned_data['classe'].split("_")
            annee=int(annee)
            # on passe en revue les matières, si elles existent, on les associe, sinon on les crée
            classe=self.tree.findall("classe[@nom='{}'][@annee='{}']".format(nom,annee)).pop()
            nouvelleClasse = Classe(nom=self.cleaned_data['nom'],annee=classe.get("annee")) #On crée la classe
            nouvelleClasse.save() # on la sauvegarde
            listeMatieres=[]
            for matiere in list(classe):# on parcourt les matières du gabarit de la classe
                query = Matiere.objects.filter(nom__iexact=matiere.get('nom'),temps=int(matiere.get("temps")),lv=int(matiere.get('lv') or 0))
                if query.exists():
                    matiere = query[0]
                else:
                    matiere = Matiere(nom=matiere.get("nom"),temps=int(matiere.get("temps")),lv=(matiere.get('lv') or 0),couleur=choice(list(zip(*Matiere.LISTE_COULEURS))[0]))
                    matiere.nomcomplet=str(matiere)
                    matiere.save()
                listeMatieres.append(matiere)
            nouvelleClasse.matieres.add(*listeMatieres)
        else:
            super().save()

class MatiereForm(forms.ModelForm):
    class Meta:
        model = Matiere
        fields=['nom','lv','couleur','temps']

    def save(self):
        classe = super().save(commit=False)
        classe.nomcomplet = str(classe)
        classe.save()

class EtabForm(forms.ModelForm):
    class Meta:
        model = Etablissement
        fields=['nom']

class SemaineForm(forms.ModelForm):
    LISTE_SEMAINES = [(i,i) for i in range(1,36)] 
    base = date.today()
    base = base-timedelta(days=base.weekday())
    # utilisation d'une fonction lambda car en python 3 les compréhensions on leur propre espace de nom, et les variables d'une classe englobante y sont invisibles
    liste1 = (lambda y:[y+timedelta(days=7*x) for x in range(-40,60)])(base)
    liste2 = [d.strftime('%d %B %Y') for d in liste1]
    LISTE_LUNDIS = zip(liste1,liste2)
    lundi = forms.ChoiceField(label="lundi", choices=LISTE_LUNDIS)

    class Meta:
        model = Semaine
        fields=['numero']

    def save(self):
        self.instance.lundi = self.cleaned_data['lundi']
        self.instance.numero = self.cleaned_data['numero']
        self.instance.save()
        

        
class JourFerieForm(forms.ModelForm):
    class Meta:
        model = JourFerie
        fields=['date','nom']
        widgets = {'date':SelectDateWidget()}

class ColleurForm(forms.Form):
    def __init__(self,*args,**kwargs):
        self.pk = kwargs.pop('pk')
        super().__init__(*args,**kwargs)
        LISTE_GRADE=((0,"autre"),(1,"certifié"),(2,"bi-admissible"),(3,"agrégé"),(4,"chaire supérieure"))
        self.fields['last_name'] = forms.CharField(label="Nom",max_length=30)
        self.fields['first_name'] = forms.CharField(label="Prénom",max_length=30)
        self.fields['password'] = forms.CharField(label="Mot de passe",max_length=30,required=False)
        self.fields['is_active'] = forms.BooleanField(label="actif",required=False)
        self.fields['email'] = forms.EmailField(label="email(facultatif)",max_length=50,required=False)
        self.fields['username'] = forms.CharField(label="Identifiant",max_length=150,required = True)
        self.fields['grade'] = forms.ChoiceField(choices=LISTE_GRADE)
        self.fields['etablissement'] = forms.ModelChoiceField(queryset=Etablissement.objects.order_by('nom'),empty_label="inconnu",required=False)
        self.fields['matiere'] = forms.ModelMultipleChoiceField(label="Matière(s)",queryset=Matiere.objects.order_by('nom'), required=False)
        self.fields['classe'] = forms.ModelMultipleChoiceField(label="Classe(s)",queryset=Classe.objects.order_by('annee','nom'),required=False)

    # validation du mot de passe
    def clean_motdepasse(self):
        user=User()
        if 'first_name' in self.cleaned_data:
            user.first_name=self.cleaned_data['first_name']
        if 'last_name' in self.cleaned_data:
            user.last_name=self.cleaned_data['last_name']
        data = self.cleaned_data['password']
        if data:
            validate_password(data,user)
        return data

class ColleurFormMdp(forms.ModelForm):
    LISTE_GRADE=enumerate(["autre","certifié","bi-admissible","agrégé","chaire supérieure"])
    grade = forms.ChoiceField(choices=LISTE_GRADE)
    etablissement = forms.ModelChoiceField(queryset=Etablissement.objects.order_by('nom'),empty_label="inconnu",required=False)
    matiere = forms.ModelMultipleChoiceField(label="Matière(s)",queryset=Matiere.objects.order_by('nom'))
    classe = forms.ModelMultipleChoiceField(label="Classe(s)",queryset=Classe.objects.order_by('annee','nom'),required=False)
    class Meta:
        model = User
        fields=['first_name','last_name','username','password','email','is_active']

    # validation du mot de passe
    def clean_password(self):
        user=User()
        if 'first_name' in self.cleaned_data:
            user.first_name=self.cleaned_data['first_name']
        if 'last_name' in self.cleaned_data:
            user.last_name=self.cleaned_data['last_name']
        data = self.cleaned_data['password']
        validate_password(data,user)
        return data

class EleveForm(forms.Form):
    def __init__(self,*args,**kwargs):
        self.pk = kwargs.pop('pk')
        super().__init__(*args,**kwargs)
        self.fields['last_name'] = forms.CharField(label="Nom",max_length=30, required = True)
        self.fields['first_name'] = forms.CharField(label="Prénom",max_length=30, required = True)
        self.fields['username'] = forms.CharField(label="Identifiant",max_length=150,required = True)
        self.fields['password'] = forms.CharField(label="Mot de passe",max_length=30,required=False)
        self.fields['email'] = forms.EmailField(label="Email(Facultatif)",max_length=50,required=False)
        self.fields['ddn'] = forms.DateField(label="Date de naissance (pour ECTS, facultatif)", required=False,input_formats=['%d/%m/%Y','%j/%m/%Y','%d/%n/%Y','%j/%n/%Y'],widget=forms.TextInput(attrs={'placeholder': 'jj/mm/aaaa'}))
        self.fields['ldn'] = forms.CharField(label="lieu de naissance (pour ECTS, facultatif)",required=False,max_length=50)
        self.fields['ine'] = forms.CharField(label="N° étudiant INE (pour ECTS, facultatif)",required=False,max_length=11)
        self.fields['photo'] = RestrictedImageField(label="photo(jpg/png, 300x400)",required=False,max_upload_size=5000000)
        self.fields['classe'] = forms.ModelChoiceField(queryset=Classe.objects.order_by('annee','nom'),empty_label=None)
        self.fields['lv1'] = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=1).order_by('nom'),empty_label='----',required=False)
        self.fields['lv2'] = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=2).order_by('nom'),empty_label='----',required=False)

    def clean_username(self):
        data = self.cleaned_data['username']
        if User.objects.filter(username = data).exclude(eleve__pk=self.pk).exists(): # si l'identifiant existe déjà
            raise ValidationError("identifiant déjà existant")
        return data

    def clean_motdepasse(self):
        user=User()
        if 'first_name' in self.cleaned_data:
            user.first_name=self.cleaned_data['first_name']
        if 'last_name' in self.cleaned_data:
            user.last_name=self.cleaned_data['last_name']
        data = self.cleaned_data['password']
        if data:
            validate_password(data,user)
        return data

    def clean_lv1(self):
        data = self.cleaned_data['lv1']
        if data is not None:
            if data not in self.cleaned_data['classe'].matieres.all():
                raise ValidationError("Cette langue ne fait pas partie des matières de cette classe")
        return data

    def clean_lv2(self):
        data = self.cleaned_data['lv2']
        if data is not None:
            if data not in self.cleaned_data['classe'].matieres.all():
                raise ValidationError("Cette langue ne fait pas partie des matières de cette classe")
        return data

    def clean_ine(self): # validation du numéro étudiant
        data = self.cleaned_data['ine']
        if data:
            if len(data) != 11:
                raise ValidationError("le numéro d'étudiant comporte 11 caractères")
            try:
                l=int(data[:-2])
                if l<=0 or not isinstance(l,int):
                    raise ValidationError("les 9 premiers caractères doivent être des chiffres")
            except Exception:
                raise ValidationError("les 9 premiers caractères doivent être des chiffres")
            if not (65 <= ord(data[-1]) <= 90):
                raise ValidationError("le dernier caractère est une lettre majuscule")
        return data


class EleveFormMdp(forms.ModelForm):
    ddn = forms.DateField(label="Date de naissance (pour ECTS, facultatif)", required=False,input_formats=['%d/%m/%Y','%j/%m/%Y','%d/%n/%Y','%j/%n/%Y'],widget=forms.TextInput(attrs={'placeholder': 'jj/mm/aaaa'}))
    ldn = forms.CharField(label="lieu de naissance (pour ECTS, facultatif)",required=False,max_length=50)
    ine = forms.CharField(label="N° étudiant INE (pour ECTS, facultatif)",required=False,max_length=11)
    photo = RestrictedImageField(label="photo(jpg/png, 300x400)",required=False,max_upload_size=5000000)
    classe = forms.ModelChoiceField(queryset=Classe.objects.order_by('annee','nom'),empty_label=None)
    lv1 = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=1).order_by('nom'),empty_label='----',required=False)
    lv2 = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=2).order_by('nom'),empty_label='----',required=False)
    class Meta:
        model = User
        fields=['first_name','last_name','username','password','email']

    def clean_lv1(self):
        data = self.cleaned_data['lv1']
        if data is not None:
            print(self.cleaned_data)
            if data not in self.cleaned_data['classe'].matieres.all():
                raise ValidationError("Cette langue ne fait pas partie des matières de cette classe")
        return data

    def clean_lv2(self):
        data = self.cleaned_data['lv2']
        if data is not None:
            if data not in self.cleaned_data['classe'].matieres.all():
                raise ValidationError("Cette langue ne fait pas partie des matières de cette classe")
        return data

    def clean_motdepasse(self):
        user=User()
        if 'prenom' in self.cleaned_data:
            user.first_name=self.cleaned_data['prenom']
        if 'nom' in self.cleaned_data:
            user.last_name=self.cleaned_data['nom']
        data = self.cleaned_data['motdepasse']
        validate_password(data,user)
        return data

    def clean_ine(self): # validation du numéro étudiant
        data = self.cleaned_data['ine']
        if data:
            if len(data) != 11:
                raise ValidationError("le numéro d'étudiant comporte 11 caractères")
            try:
                l=int(data[:-2])
                if l<=0 or not isinstance(l,int):
                    raise ValidationError("les 9 premiers caractères doivent être des chiffres")
            except Exception:
                raise ValidationError("les 9 premiers caractères doivent être des chiffres")
            if not (65 <= ord(data[-1]) <= 90):
                raise ValidationError("le dernier caractère est une lettre ASCII majuscule")
        return data

class ProfForm(forms.Form):
    def __init__(self,classe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classe=classe
        for matiere in classe.matieres.all():
            query=Colleur.objects.filter(matieres=matiere,classes=classe,user__is_active=True).order_by('user__last_name','user__last_name')
            self.fields[str(matiere.pk)] = forms.ModelChoiceField(label=matiere,queryset=query,required=False)
        query2 = Colleur.objects.filter(classes=classe,user__is_active=True)
        self.fields['profprincipal'] = forms.ModelChoiceField(label="prof principal",queryset=query2,required=False)

    def clean(self):
        """Vérifie que le prof principal est bien choisi parmi les profs de la classe"""
        if self.cleaned_data['profprincipal'] not in [self.cleaned_data[str(matiere.pk)] for matiere in self.classe.matieres.all()]:
            raise ValidationError("le professeur principal doit faire partie des professeurs de la classe")

    def save(self):
        """Sauvegarde en base de données les données du formulaire"""
        matieres_avec_prof=[matiere for matiere in self.classe.matieres.all() if self.cleaned_data[str(matiere.pk)]] # liste des matieres
        colleurs_avec_prof=[self.cleaned_data[str(matiere.pk)] for matiere in self.classe.matieres.all() if self.cleaned_data[str(matiere.pk)]] # liste des colleurs
        # on efface les profs correspondants à la classe courante
        Prof.objects.filter(classe=self.classe).delete()
        # on crée les nouvelles entités profs
        config=Config.objects.get_config()
        Prof.objects.bulk_create([Prof(classe=self.classe,matiere=matiere,modifgroupe=config.default_modif_groupe,modifcolloscope=config.default_modif_col,colleur=colleur) for matiere,colleur in zip(matieres_avec_prof,colleurs_avec_prof)])
        # mise à jour du prof principal
        if self.cleaned_data['profprincipal']:
            self.classe.profprincipal=self.cleaned_data['profprincipal']
        else:
            self.classe.profprincipal = None
        self.classe.save()

class CustomMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(*args,**kwargs):
        return ""

class SelectColleurForm(forms.Form):
    def __init__(self,matiere=None,classe=None, pattern = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        query = Colleur.objects
        if matiere:
            query = query.filter(matieres=matiere)
        if classe:
            query = query.filter(classes=classe)
        if pattern:
            query = query.filter(Q(user__first_name__icontains=pattern) | Q(user__last_name__icontains=pattern))
        query=query.order_by('user__last_name','user__first_name','user__pk')
        self.fields['colleur'] = CustomMultipleChoiceField(queryset=query, required=True,widget = forms.CheckboxSelectMultiple)
        self.fields['colleur'].empty_label=None

class ChercheUserForm(forms.Form):
    nom = forms.CharField(label = "Nom", required = False, max_length = 40)

    def clean_nom(self):
        return self.cleaned_data['nom'].lower() # on passe tout en minuscule
        

class SelectEleveForm(forms.Form):
    def __init__(self, klasse=None, tri = True, pattern = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        if klasse:
            query = Eleve.objects.filter(classe=klasse).select_related('user','classe','lv1','lv2')
        else:
            query = Eleve.objects.select_related('user','classe','lv1','lv2')
        if pattern:
            query = query.filter(Q(user__first_name__icontains=pattern) | Q(user__last_name__icontains=pattern))
        if tri:
            query = query.order_by('classe__nom','user__last_name','user__first_name')
        else:
            query = query.order_by('user__last_name','user__first_name','classe__nom')
        self.fields['eleve'] = CustomMultipleChoiceField(queryset=query, required=True,widget = forms.CheckboxSelectMultiple)
        self.fields['eleve'].empty_label=None
        self.fields['klasse'] = forms.ModelChoiceField(queryset=Classe.objects.order_by('annee','nom'),required=False)
        self.fields['klasse'].empty_label=None
        self.fields['lv1'] = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=1).order_by('nom'),required=False)
        self.fields['lv2'] = forms.ModelChoiceField(queryset=Matiere.objects.filter(lv=2).order_by('nom'),required=False)

class ClasseSelectForm(forms.Form):
    query=Classe.objects.order_by('nom')
    classe=forms.ModelChoiceField(label="Classe",queryset=query, empty_label="Toutes",required=False)

class MatiereClasseSelectForm(forms.Form):
    matiere=forms.ModelChoiceField(label="Matière",queryset=Matiere.objects.order_by('nom'), empty_label="Toutes",required=False)
    classe=forms.ModelChoiceField(label="Classe",queryset=Classe.objects.order_by('nom'), empty_label="Toutes",required=False)

    def clean(self):
        if self.cleaned_data['classe'] is not None and self.cleaned_data['matiere'] is not None and self.cleaned_data['matiere'] not in self.cleaned_data['classe'].matieres.all():
            raise ValidationError("la classe %(classe)s n'a pas pour matière %(matiere)s",params={'classe':self.cleaned_data['classe'],'matiere':self.cleaned_data['matiere']})

class CsvForm(forms.Form):
    nom = forms.CharField(label="intitulé du champ nom",required=True,max_length=30)
    prenom = forms.CharField(label="intitulé du champ prénom",required=True,max_length=30)
    ddn = forms.CharField(label="intitulé du champ date de naissance (pour ECTS, facultatif)",required=False,max_length=30)
    ldn = forms.CharField(label="intitulé du champ lieu de naissance (pour ECTS, facultatif)",required=False,max_length=50)
    ine = forms.CharField(label="intitulé du champ numéro INE (pour ETCS, facultatif)",required=False,max_length=30)
    email = forms.CharField(label="intitulé du champ email(facultatif)",required=False,max_length=30)
    fichier = forms.FileField(label="Fichier csv",required=True)
    classe=forms.ModelChoiceField(label="Classe",queryset=Classe.objects.order_by('nom'), empty_label="Non définie",required=False) 




