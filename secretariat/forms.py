#-*- coding: utf-8 -*-
from django import forms
from django.db.models import Max, Min
from accueil.models import Matiere, Classe, Semaine, Ramassage
from datetime import date, timedelta
from django.core.exceptions import ValidationError

def mois():
    """Renvoie les mois min et max (+1 mois) des semaines de colle. Renvoie le mois courant en double si aucune semaine n'est définie"""
    try:
        moisMin=Semaine.objects.aggregate(Min('lundi'))
        moisMax=Semaine.objects.aggregate(Max('lundi'))
        moisMin=date(moisMin['lundi__min'].year+moisMin['lundi__min'].month//12,moisMin['lundi__min'].month%12+1,1)-timedelta(days=1) # dernier jour du mois
        moisMax=moisMax['lundi__max']+timedelta(days=35)
        moisMax=date(moisMax.year+moisMax.month//12,moisMax.month%12+1,1)-timedelta(days=1) # dernier jour du mois
    except Exception:
        hui=date.today()
        moisMin=moisMax=date(hui.year+hui.month//12,hui.month%12+1,1)-timedelta(days=1)
    return moisMin,moisMax

def incremente_mois(moment):
        """ajoute un mois à moment"""
        moment += timedelta(days=1)
        return date(moment.year+moment.month//12,moment.month%12+1,1) - timedelta(days=1)

class RamassageForm(forms.Form):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        print("init")
        moisMin,moisMax=mois()
        moiscourant=moisMin
        LISTE_MOIS =[moiscourant]
        moiscourant=incremente_mois(moiscourant)
        while moiscourant<=moisMax:
            LISTE_MOIS.append(moiscourant)
            moiscourant=incremente_mois(moiscourant)
        LISTE_MOIS=[(x,x.strftime('%B %Y')) for x in LISTE_MOIS]
        if Ramassage.objects.exists(): # s'il existe déjà des ramassages
            maxmois = Ramassage.objects.aggregate(Max('moisFin'))['moisFin__max']
            self.fields['moisFin'] = forms.ChoiceField(label="jusqu'à (inclus)",choices = (lambda t,z:[(x,y) for x,y in z if x > t])(maxmois,LISTE_MOIS))
        else:
            self.fields['moisFin'] = forms.ChoiceField(label="jusqu'à (inclus)",choices = LISTE_MOIS)

    def clean(self):
        """Vérifie qu'il n'existe pas de ramassage d'un mois identique ou postérieur"""
        if self.cleaned_data:
            if Ramassage.objects.filter(moisFin=self.cleaned_data['moisFin']).exists():
                raise ValidationError('Il existe déjà un ramassage pour ce mois.')
            if Ramassage.objects.filter(moisFin__gt=self.cleaned_data['moisFin']).exists():
                raise ValidationError('Il existe déjà un ramassage postérieur à ce mois')

    def save(self):
        """Sauvegarde du ramassage (avec création du décompte associé)"""
        Ramassage.objects.createOrUpdate(self.cleaned_data['moisFin'])

class MoisForm(forms.Form):
    def __init__(self, moisMin, moisMax, *args, **kwargs):
        super().__init__(*args, **kwargs)
        LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
        nbMois=12*(moisMax.year-moisMin.year)+moisMax.month-moisMin.month+1
        ListeMoisMin=[False]*nbMois
        ListeMoisMax=[False]*nbMois
        for i in range(nbMois):
            moisDebut=date(moisMin.year+(moisMin.month+i-1)//12,(moisMin.month+i-1)%12+1,1)
            moisFin=date(moisMin.year+(moisMin.month+i)//12,(moisMin.month+i)%12+1,1) - timedelta(days=1)
            ListeMoisMin[i]=(moisDebut,"{} {}".format(LISTE_MOIS[moisDebut.month],moisDebut.year))
            ListeMoisMax[i]=(moisFin,"{} {}".format(LISTE_MOIS[moisFin.month],moisFin.year))
        self.fields['moisMin']=forms.ChoiceField(choices=ListeMoisMin,initial=ListeMoisMin[0][0])
        self.fields['moisMax']=forms.ChoiceField(choices=ListeMoisMax,initial=ListeMoisMax[0][0])

class MatiereClasseSelectForm(forms.Form):
    matiere=forms.ModelChoiceField(label="Matière",queryset=Matiere.objects.order_by('nom'),required=True,empty_label=None)
    classe=forms.ModelChoiceField(label="Classe",queryset=Classe.objects.order_by('nom'),required=True,empty_label=None)

class MatiereClasseSemaineSelectForm(forms.Form):
    matiere=forms.ModelChoiceField(label="Matière",queryset=Matiere.objects.order_by('nom'),required=True,empty_label=None)
    classe=forms.ModelChoiceField(label="Classe",queryset=Classe.objects.order_by('nom'),required=True,empty_label=None)
    try:
        query=Semaine.objects.order_by('lundi')
        semin=forms.ModelChoiceField(queryset=query, empty_label=None,initial=query[0],required=True)
        semax=forms.ModelChoiceField(queryset=query, empty_label=None,initial=query[query.count()-1],required=True)
    except Exception:
        semin=forms.ModelChoiceField(queryset=Semaine.objects.none(), empty_label=None,required=True)
        semax=forms.ModelChoiceField(queryset=Semaine.objects.none(), empty_label=None,required=True)

    def clean(self):
        if self.cleaned_data['matiere'] not in self.cleaned_data['classe'].matieres.all():
            raise ValidationError("la classe %(classe)s n'a pas pour matière %(matiere)s",params={'classe':self.cleaned_data['classe'],'matiere':self.cleaned_data['matiere']})

class SelectClasseSemaineForm(forms.Form):
    classes = forms.ModelMultipleChoiceField(queryset=Classe.objects.all(),label="classes",widget=forms.CheckboxSelectMultiple,required=True)
    query=Semaine.objects.all()
    try:
        semin = forms.ModelChoiceField(queryset=query,label="semaine de départ",initial=query[0])
        semax = forms.ModelChoiceField(queryset=query,label="semaine de fin",initial=query[len(query)-1])
    except Exception:
        semin = forms.ModelChoiceField(queryset=query,label="semaine de départ")
        semax = forms.ModelChoiceField(queryset=query,label="semaine de fin")
