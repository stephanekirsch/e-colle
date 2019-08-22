#-*- coding: utf-8 -*-
from django import forms
from accueil.models import Colleur, Groupe, Matiere, Destinataire, Message, Classe, Eleve, User, Prof
from administrateur.forms import CustomMultipleChoiceField
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q

class ConnexionForm(forms.Form):
    username = forms.CharField(label="identifiant")
    password = forms.CharField(label="Mot de passe",
                               widget=forms.PasswordInput)

class GroupeMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self,groupe,*args,**kwargs):
        return "{}: ".format(groupe.nom)+"/".join([str(eleve.user.last_name.upper()) for eleve in groupe.groupeeleve.all()])

class ColleurForm(forms.Form):
    def __init__(self,*args,**kwargs):
        self.pk = kwargs.pop('pk')
        super().__init__(*args,**kwargs)
        self.fields['last_name'] = forms.CharField(label="Nom",max_length=30)
        self.fields['first_name'] = forms.CharField(label="Prénom",max_length=30)
        self.fields['password'] = forms.CharField(label="Mot de passe",max_length=30,required=False)
        self.fields['is_active'] = forms.BooleanField(label="actif",required=False)
        self.fields['email'] = forms.EmailField(label="email(facultatif)",max_length=50,required=False)
    

class UserForm(forms.ModelForm):
    motdepasse = forms.CharField(label="Mot de passe",max_length=30,required=False)
    class Meta:
        model = User
        fields=['email','css']

    def clean_motdepasse(self):
        data = self.cleaned_data['motdepasse']
        if data:
            validate_password(data)
        return data

    def save(self):
        user = self.instance
        if self.cleaned_data['motdepasse']:
            user.set_password(self.cleaned_data['motdepasse'])
        user.save()


class ColleurMultipleChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self,classe,matiere=False,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.classe=classe
        self.matiere=matiere

    def label_from_instance(self,colleur,*args,**kwargs):
        chaine = str(colleur)
        if not self.matiere:
            chaine += " ("+ " et ".join([str(mat).title() for mat in Matiere.objects.filter(matiereprof__colleur=colleur,matiereprof__classe=self.classe)]) +")"
        return chaine

class UserProfprincipalForm(forms.ModelForm):
    class Meta:
        model = User
        fields=['email','css']

    def __init__(self,colleur,classes,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.classes = classes
        self.fields['motdepasse']=forms.CharField(label="Mot de passe",widget=forms.PasswordInput,required=False)
        for classe in classes:
            self.fields["{}_groupe".format(classe.pk)] = ColleurMultipleChoiceField(classe,label="Droits de modifier les groupes de {}".format(classe.nom.upper()),queryset=Colleur.objects.filter(colleurprof__classe=classe,user__is_active=True).select_related('user').exclude(pk=colleur.pk),widget=forms.CheckboxSelectMultiple,required=False)
            self.fields["{}_colloscope".format(classe.pk)] = ColleurMultipleChoiceField(classe,label="Droits de modifier le colloscope de {}".format(classe.nom.upper()),queryset=Colleur.objects.filter(colleurprof__classe=classe,user__is_active=True).select_related('user').exclude(pk=colleur.pk),widget=forms.CheckboxSelectMultiple,required=False)

    def clean_motdepasse(self):
        data = self.cleaned_data['motdepasse']
        if data:
            validate_password(data)
        return data

    def save(self):
        user = self.instance
        if self.cleaned_data['motdepasse']:
            user.set_password(self.cleaned_data['motdepasse'])
        user.save()
        for classe in self.classes:
            for matiere in classe.matieres.all():
                prof = Prof.objects.filter(classe=classe,matiere=matiere)
                if prof and prof[0].colleur in self.cleaned_data["{}_groupe".format(classe.pk)]:
                    prof.update(modifgroupe=True)
                else:
                    prof.update(modifgroupe=False)
                if prof and prof[0].colleur in self.cleaned_data["{}_colloscope".format(classe.pk)]:
                    prof.update(modifcolloscope=True)
                else:
                    prof.update(modifcolloscope=False)
        
class SelectMessageForm(forms.Form):
    def __init__(self,user,*args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        query=Message.objects.filter(Q(auteur=user,hasAuteur=True)|Q(messagerecu__user=user)).distinct().order_by('-date')
        self.fields['message'] = CustomMultipleChoiceField(queryset=query, required=True,widget = forms.CheckboxSelectMultiple)
        self.fields['message'].empty_label=None

    def save(self,*args,**kwargs):
        """si le formulaire est valide on efface les message/destinataires nécessaires"""
        for message in self.cleaned_data['message']:
            if message.auteur == self.user: # si c'est un message envoyé:
                if not message.messagerecu.all(): # s'il n'y a plus de destinataires, on efface
                    message.delete()
                else: # sinon on passe hasauteur à False:
                    message.hasAuteur = False
                    message.save()
            else: # si c'est un message reçu, on efface son destinataire:
                Destinataire.objects.filter(message = message, user = self.user).delete()
                if not Destinataire.objects.filter(message = message).exists and not message.hasAuteur: # s"il n'y a plus ni auteur ni destinataire, on efface
                    message.delete()

class ReponseForm(forms.Form):
    def format_reponse(self,message):
        return (">"+message.strip().replace("\n","\n>")+"\n")

    def __init__(self,message,*args, **kwargs):
        super().__init__(*args,**kwargs)
        self.fields['destinataire'] = forms.CharField(label="Destinataire",required=False)
        self.fields['destinataire'].widget.attrs={'disabled':True}
        self.fields['titre'] = forms.CharField(label="titre",max_length=100,required=True,initial="Re: "+message.titre)
        self.fields['titre'].widget.attrs={'size':50}
        self.fields['corps'] = forms.CharField(label="corps du message",widget=forms.Textarea,required=True,max_length=2000,
            initial = self.format_reponse(message.corps))
        self.fields['corps'].widget.attrs={'cols':60,'rows':15}

class EcrireForm(forms.Form):
    def __init__(self,user,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.champs = []
        if user.colleur and user.is_active:
            classes = user.colleur.classes.all()
            classesprof = user.colleur.colleurprof.all()
            matieres = user.colleur.matieres.all()
            for classe in classes:
                listematieres=[]
                listecolleurs=[]
                listeprofs=False
                matieresprof = classesprof.filter(classe=classe).exists()
                prof=False
                if matieresprof:
                    query = Colleur.objects.filter(colleurprof__classe=classe).exclude(pk=user.colleur.pk).distinct().order_by('user__last_name')
                else:
                    query = Colleur.objects.filter(colleurprof__classe=classe,colleurprof__matiere__in=matieres).distinct().order_by('user__last_name')
                self.fields['classeprof_{}'.format(classe.pk)] = ColleurMultipleChoiceField(classe,False,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
                listeprofs = self['classeprof_{}'.format(classe.pk)]
                self.fields['matiereprof_{}'.format(classe.pk)]=forms.BooleanField(label="Profs",required=False)
                prof=self['matiereprof_{}'.format(classe.pk)]
                self.fields['colleurs_{}'.format(classe.pk)]=forms.BooleanField(label="Colleurs",required=False)
                colleur = self['colleurs_{}'.format(classe.pk)]
                for matiere in Matiere.objects.filter(matiereprof__colleur=user.colleur,matiereprof__classe=classe):
                    self.fields['matiere_{}_{}'.format(classe.pk,matiere.pk)]=forms.BooleanField(label=str(matiere),required=False)
                    listecolleurs.append(self['matiere_{}_{}'.format(classe.pk,matiere.pk)])
                    query = Colleur.objects.filter(classes=classe,matieres=matiere,user__is_active=True).exclude(pk=user.colleur.pk).select_related('user').order_by('user__last_name')
                    self.fields['classematiere_{}_{}'.format(classe.pk,matiere.pk)] = ColleurMultipleChoiceField(classe,True,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
                    listematieres.append(self['classematiere_{}_{}'.format(classe.pk,matiere.pk)])
                self.fields['matieregroupe_{}'.format(classe.pk)]=forms.BooleanField(label="Élèves(groupe)",required=False)
                query2 = Groupe.objects.filter(groupeeleve__classe=classe).prefetch_related('groupeeleve__user').distinct()
                self.fields['classegroupe_{}'.format(classe.pk)] = GroupeMultipleChoiceField(queryset=query2,widget=forms.CheckboxSelectMultiple,required=False)
                self.fields['matiereeleve_{}'.format(classe.pk)]=forms.BooleanField(label="Élèves(solo)",required=False)
                query3 = Eleve.objects.filter(classe=classe).select_related('user')
                self.fields['classeeleve_{}'.format(classe.pk)] = forms.ModelMultipleChoiceField(queryset=query3,widget=forms.CheckboxSelectMultiple,required=False)
                colleurs = zip(listecolleurs,listematieres) if listecolleurs else False
                self.champs.append((classe,prof,listeprofs,colleur,colleurs,self['matieregroupe_{}'.format(classe.pk)],self['classegroupe_{}'.format(classe.pk)],self['matiereeleve_{}'.format(classe.pk)],self['classeeleve_{}'.format(classe.pk)]))
        elif user.eleve and user.eleve.classe:
            classe = user.eleve.classe
            matieres = classe.matieres.all()
            listematieres=[]
            listecolleurs=[]
            listeprofs=False
            prof=False
            query = Colleur.objects.filter(colleurprof__classe=classe,colleurprof__matiere__in=matieres).distinct().order_by('user__last_name')
            self.fields['classeprof_{}'.format(classe.pk)] = ColleurMultipleChoiceField(classe,False,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
            self.fields['classeprof_{}'.format(classe.pk)] = ColleurMultipleChoiceField(classe,False,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
            listeprofs = self['classeprof_{}'.format(classe.pk)]
            self.fields['matiereprof_{}'.format(classe.pk)]=forms.BooleanField(label="Profs",required=False)
            prof=self['matiereprof_{}'.format(classe.pk)]
            self.fields['colleurs_{}'.format(classe.pk)]=forms.BooleanField(label="Colleurs",required=False)
            colleur = self['colleurs_{}'.format(classe.pk)]
            for matiere in matieres:
                self.fields['matiere_{}_{}'.format(classe.pk,matiere.pk)]=forms.BooleanField(label=str(matiere),required=False)
                listecolleurs.append(self['matiere_{}_{}'.format(classe.pk,matiere.pk)])
                query = Colleur.objects.filter(classes=classe,matieres=matiere,user__is_active=True).select_related('user').order_by('user__last_name')
                self.fields['classematiere_{}_{}'.format(classe.pk,matiere.pk)] = ColleurMultipleChoiceField(classe,True,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
                listematieres.append(self['classematiere_{}_{}'.format(classe.pk,matiere.pk)])
            self.fields['matieregroupe_{}'.format(classe.pk)]=forms.BooleanField(label="Élèves(groupe)",required=False)
            query2 = Groupe.objects.filter(groupeeleve__classe=classe).prefetch_related('groupeeleve__user').distinct()
            self.fields['classegroupe_{}'.format(classe.pk)] = GroupeMultipleChoiceField(queryset=query2,widget=forms.CheckboxSelectMultiple,required=False)
            self.fields['matiereeleve_{}'.format(classe.pk)]=forms.BooleanField(label="Élèves(solo)",required=False)
            query3 = Eleve.objects.filter(classe=classe).select_related('user')
            self.fields['classeeleve_{}'.format(classe.pk)] = forms.ModelMultipleChoiceField(queryset=query3,widget=forms.CheckboxSelectMultiple,required=False)
            colleurs = zip(listecolleurs,listematieres) if listecolleurs else False
            self.champs.append((classe,prof,listeprofs,colleur,colleurs,self['matieregroupe_{}'.format(classe.pk)],self['classegroupe_{}'.format(classe.pk)],self['matiereeleve_{}'.format(classe.pk)],self['classeeleve_{}'.format(classe.pk)]))
        elif user.username=="Secrétariat" or user.username=="admin":
            classes = Classe.objects.all()
            for classe in classes:
                listematieres=[]
                listecolleurs=[]
                listeprofs=False
                prof=False
                query = Colleur.objects.filter(colleurprof__classe=classe).distinct().order_by('user__last_name')
                self.fields['classeprof_{}'.format(classe.pk)] = ColleurMultipleChoiceField(classe,False,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
                listeprofs = self['classeprof_{}'.format(classe.pk)]
                self.fields['matiereprof_{}'.format(classe.pk)]=forms.BooleanField(label="Profs",required=False)
                prof=self['matiereprof_{}'.format(classe.pk)]
                self.fields['colleurs_{}'.format(classe.pk)]=forms.BooleanField(label="Colleurs",required=False)
                colleur = self['colleurs_{}'.format(classe.pk)]
                for matiere in classe.matieres.all():
                    self.fields['matiere_{}_{}'.format(classe.pk,matiere.pk)]=forms.BooleanField(label=matiere.nom.title(),required=False)
                    listecolleurs.append(self['matiere_{}_{}'.format(classe.pk,matiere.pk)])
                    query = Colleur.objects.filter(classes=classe,matieres=matiere,user__is_active=True).select_related('user').order_by('user__last_name')
                    self.fields['classematiere_{}_{}'.format(classe.pk,matiere.pk)] = ColleurMultipleChoiceField(classe,True,queryset=query,widget=forms.CheckboxSelectMultiple,required=False)
                    listematieres.append(self['classematiere_{}_{}'.format(classe.pk,matiere.pk)])
                self.fields['matieregroupe_{}'.format(classe.pk)]=forms.BooleanField(label="Élèves(groupe)",required=False)
                query2 = Groupe.objects.filter(groupeeleve__classe=classe).prefetch_related('groupeeleve__user').distinct()
                self.fields['classegroupe_{}'.format(classe.pk)] = GroupeMultipleChoiceField(queryset=query2,widget=forms.CheckboxSelectMultiple,required=False)
                self.fields['matiereeleve_{}'.format(classe.pk)]=forms.BooleanField(label="Élèves(solo)",required=False)
                query3 = Eleve.objects.filter(classe=classe).select_related('user')
                self.fields['classeeleve_{}'.format(classe.pk)] = forms.ModelMultipleChoiceField(queryset=query3,widget=forms.CheckboxSelectMultiple,required=False)
                colleurs = zip(listecolleurs,listematieres) if listecolleurs else False
                self.champs.append((classe,prof,listeprofs,colleur,colleurs,self['matieregroupe_{}'.format(classe.pk)],self['classegroupe_{}'.format(classe.pk)],self['matiereeleve_{}'.format(classe.pk)],self['classeeleve_{}'.format(classe.pk)]))
        self.colspan = len(self.champs)
        self.colspansubmit = self.colspan+1
        if user.eleve:
            nb = 1
        else:
            nb = classes.count()
        self.rowspan,self.reste = (nb+1)>>1 ,nb&1
        self.fields['titre'] = forms.CharField(label="titre",max_length=100,required=True)
        self.fields['titre'].widget.attrs={'size':50}
        self.fields['corps'] = forms.CharField(label="corps du message",widget=forms.Textarea,required=True,max_length=2000)
        self.fields['corps'].widget.attrs={'cols':60,'rows':15}
