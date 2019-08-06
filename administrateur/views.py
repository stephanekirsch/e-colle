#-*- coding: utf-8 -*-
from django.http import HttpResponseForbidden, Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from administrateur.forms import ChercheUserForm, ConfigForm, EleveFormSet, EleveFormSetMdp, ColleurFormSet, ColleurFormSetMdp, MatiereClasseSelectForm, AdminConnexionForm, ClasseForm, ClasseGabaritForm, ClasseSelectForm, MatiereForm, EtabForm, SemaineForm, ColleurForm, ColleurFormMdp, SelectColleurForm, EleveForm, EleveFormMdp, SelectEleveForm, ProfForm, JourFerieForm, CsvForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from accueil.models import *
from django.forms.formsets import formset_factory
from django.db import transaction
from django.db.models import Max
from datetime import timedelta
from random import choice
from reportlab.platypus import Table, TableStyle, Image, SimpleDocTemplate, PageBreak, Paragraph
from reportlab.lib.styles import ParagraphStyle, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
import csv
from os.path import join
from _io import TextIOWrapper
from ecolle.settings import IP_FILTRE_ADMIN, IP_FILTRE_ADRESSES, MEDIA_ROOT
import re 
from io import BytesIO

def random_string():
    """renvoie une chaine de caractères aléatoires contenant des lettres ou des chiffres ou un des symboles _+-.@"""
    return "".join([choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_+-.@0123456789") for i in range (30)])

def is_admin(user):
    """Renvoie True si l'utilisateur courant est l'administateur, False sinon"""
    return user.is_authenticated and user.username=="admin"

def ip_filter(func):
    """Décorateur qui combine deux vérifications: l'utilisateur courant est l'administrateur
     et l'IP de l'utilisateur est parmi les IP autorisées si le filtrage IP est actif"""
    def wrapped_view(request,*args,**kwargs):
        if IP_FILTRE_ADMIN:
            user_ip = request.META['REMOTE_ADDR']
            for ip in IP_FILTRE_ADRESSES:
                authenticated_by_ip = re.compile(ip).match(user_ip)
                if authenticated_by_ip:
                    return func(request, *args, **kwargs)
            return HttpResponseForbidden("Vous n'avez pas les droits suffisants pour accéder à cette page")
        return func(request, *args, **kwargs)
    return user_passes_test(is_admin, login_url="login_admin")(wrapped_view)

def ip_filter_connec(func):
    """Décorateur qui vérifie si l'IP de l'utilisateur est parmi les IP autorisées si le filtrage IP est actif"""
    def wrapped_view(request,*args,**kwargs):
        if IP_FILTRE_ADMIN:
            user_ip = request.META['REMOTE_ADDR']
            for ip in IP_FILTRE_ADRESSES:
                authenticated_by_ip = re.compile(ip).match(user_ip)
                if authenticated_by_ip:
                    return func(request, *args, **kwargs)
            return HttpResponseForbidden("Vous n'avez pas les droits suffisants pour accéder à cette page")
        return func(request, *args, **kwargs)
    return wrapped_view

@ip_filter_connec
def connec(request):
    """Renvoie la vue de la page de connexion de l'admin. Si l'administrateur est déjà connecté, redirige vers la page d'accueil de l'administrateur"""
    if is_admin(request.user):
        return redirect('action_admin')
    error = False
    form = AdminConnexionForm(request.POST or None, initial={'username':'admin'})
    if form.is_valid():
        username = 'admin'
        password = form.cleaned_data['password']
        user = authenticate(username=username,password=password)
        if user:
            login(request,user)
            return redirect('action_admin')
        else:
            error = True
    form.fields['username'].widget.attrs['readonly'] = True
    return render(request,'administrateur/home.html',{'form':form,'error':error})

@ip_filter
def action(request):
    """Renvoie la vue la page d'accueil de l'administrateur"""
    return render(request,'administrateur/action.html')

@ip_filter
def config(request):
    """Renvoie la vue de la page de configuration de l'administrateur"""
    form = ConfigForm(request.POST or None,instance=Config.objects.get_config())
    if form.is_valid():
        form.save()
        return redirect('configconfirm')
    return render(request,'administrateur/config.html',{'form':form})

@ip_filter
def configconfirm(request):
    """Renvoie la vue de la page de confirmation de modification de la configuration"""
    return render(request,'administrateur/configconfirm.html')

@ip_filter
def classe(request):
    """Renvoie la vue de la page de gestion des classes"""
    form = ClasseGabaritForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('gestion_classe')
    classes = Classe.objects.order_by('annee','nom')
    return render(request,'administrateur/classe.html',{'classes':classes,'form':form})

@ip_filter
def classemodif(request, id_classe):
    """Renvoie la vue de la page de modification de la classe dont l'id est id_classe"""
    classe = get_object_or_404(Classe, pk=id_classe)
    form=ClasseForm(request.POST or None, instance=classe)
    if form.is_valid():
        form.save()
        return redirect('gestion_classe')
    return render (request,'administrateur/classemodif.html',{'form':form,'classe':classe,'idclasse':id_classe})

@ip_filter
def classesuppr(request, id_classe):
    """essaie de supprimer la classe dont l'id est id_classe, puis redirige vers la page de gestion des classes"""
    try:
        get_object_or_404(Classe,pk=id_classe).delete()
    except Exception:
        messages.error(request,"Impossible d'effacer la classe car elle est présente chez certains élèves")
    return redirect('gestion_classe')

@ip_filter
def ferie(request):
    """Renvoie la vue de la page de gestion des jours fériés"""
    form = JourFerieForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('gestion_ferie')
    feries = JourFerie.objects.order_by('date','nom')
    return render(request,'administrateur/ferie.html',{'feries':feries,'form':form})

@ip_filter
def feriemodif(request, id_ferie):
    """Renvoie la vue de la page de modification du jour férié dont l'id est id_ferie"""
    ferie = get_object_or_404(JourFerie, pk=id_ferie)
    form=JourFerieForm(request.POST or None, instance=ferie)
    if form.is_valid():
        form.save()
        return redirect('gestion_ferie')
    return render (request,'administrateur/feriemodif.html',{'form':form,'ferie':ferie,'id_ferie':id_ferie})

@ip_filter
def feriesuppr(request, id_ferie):
    """essaie de supprimer le jour férié dont l'id est id_ferie, puis redirige vers la page de gestion des jours fériés"""
    try:
        get_object_or_404(JourFerie,pk=id_ferie).delete()
    except Exception:
        messages.error(request,"Impossible d'effacer le jour férié car il n'existe pas")
    return redirect('gestion_ferie')

@ip_filter
def matiere(request):
    """Renvoie la vue de la page de gestion des matieres"""
    form = MatiereForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('gestion_matiere')
    matieres = Matiere.objects.order_by('nom')
    return render(request,'administrateur/matiere.html',{'matieres':matieres,'form':form})

@ip_filter
def matieremodif(request, id_matiere):
    """Renvoie la vue de la page de modification de la matière dont l'id est id_matiere"""
    matiere = get_object_or_404(Matiere,pk=id_matiere)
    form=MatiereForm(request.POST or None, instance=matiere)
    if form.is_valid():
        form.save()
        return redirect('gestion_matiere')
    return render (request,'administrateur/matieremodif.html',{'form':form,'matiere':matiere})

@ip_filter
def matieresuppr(request, id_matiere):
    """essaie de supprimer la matière dont l'id est id_matiere, puis redirige vers la page de gestion des matières"""
    try:
        get_object_or_404(Matiere,pk=id_matiere).delete()
    except Exception:
        messages.error(request,"Impossible d'effacer la matière car elle est présente chez certains colleurs")
    return redirect('gestion_matiere')

@ip_filter
def etab(request):
    """Renvoie la vue de la page de gestion des établissements"""
    form = EtabForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('gestion_etab')
    etabs= Etablissement.objects.order_by('nom')
    return render (request,'administrateur/etab.html',{'etabs':etabs,'form':form})

@ip_filter
def etabmodif(request, id_etab):
    """Renvoie la vue de la page de modification de l'établissement dont l'id est id_etab"""
    etab = get_object_or_404(Etablissement,pk=id_etab)
    form=EtabForm(request.POST or None, instance=etab)
    if form.is_valid():
        form.save()
        return redirect('gestion_etab')
    return render (request,'administrateur/etabmodif.html',{'form':form,'etab':etab})

@ip_filter
def etabsuppr(request, id_etab):
    """essaie de supprimer l'établissement dont l'id est id_etab, puis redirige vers la page de gestion des établissements"""
    try:
        get_object_or_404(Etablissement,pk=id_etab).delete()
    except Exception:
        messages.error(request,"Impossible d'effacer l'établissement car il est présent chez certains colleurs")
    return redirect('gestion_etab')

@ip_filter
def semaine(request):
    """Renvoie la vue de la page de gestion des semaines"""
    lundimax=Semaine.objects.aggregate(Max('lundi'))
    numeromax=Semaine.objects.aggregate(Max('numero'))
    semaine=Semaine()
    if lundimax['lundi__max'] is not None and numeromax['numero__max'] is not None:
        semaine.lundi=lundimax['lundi__max']+timedelta(days=7)
        semaine.numero=numeromax['numero__max']+1
    print(semaine)
    form = SemaineForm(request.POST or None, initial={'lundi':semaine.lundi,'numero':semaine.numero})
    if form.is_valid():
        form.save()
        return redirect('gestion_semaine')
    semaines = Semaine.objects.order_by('lundi')
    return render(request,'administrateur/semaine.html',{'semaines':semaines,'form':form })

@ip_filter
def semainemodif(request, id_semaine):
    """Renvoie la vue de la page de modification de la semaine dont l'id est id_semaine"""
    semaine = get_object_or_404(Semaine,pk=id_semaine)
    form=SemaineForm(request.POST or None, instance=semaine, initial = {"numero":semaine.numero,"lundi":semaine.lundi})
    if form.is_valid():
        form.save()
        return redirect('gestion_semaine')
    return render (request,'administrateur/semainemodif.html',{'form':form,'semaine':semaine})

@ip_filter
def semainesuppr(request, id_semaine):
    """essaie de supprimer la semaine dont l'id est id_semaine, puis redirige vers la page de gestion des établissements"""
    try:
        get_object_or_404(Semaine,pk=id_semaine).delete()
    except Exception:
        messages.error(request,"Impossible d'effacer la semaine car elle est présente dans certain(e)s colles/programmes")
    return redirect('gestion_semaine')

@ip_filter
def colleur(request):
    """Renvoie la vue de la page de gestion des colleurs"""
    if "selectmatiere" in request.POST:
        form = MatiereClasseSelectForm(request.POST)
    else:
        try:
            matiere = Matiere.objects.get(pk=request.session['matiere'])
        except Exception:
            matiere = None
        try:
            classe = Classe.objects.get(pk=request.session['classe'])
        except Exception:
            classe = None
        form = MatiereClasseSelectForm(initial = {'matiere':matiere,'classe':classe})
    if form.is_valid():
        matiere = form.cleaned_data['matiere']
        request.session['matiere'] = None if not matiere else matiere.pk
        classe = form.cleaned_data['classe']
        request.session['classe'] = None if not classe else classe.pk
    else:
        try:
            matiere = Matiere.objects.get(pk=request.session['matiere'])
        except Exception:
            matiere = None
        try:
            classe = Classe.objects.get(pk=request.session['classe'])
        except Exception:
            classe = None
    terme_recherche = ""
    if "chercheuser" in request.POST:
        form3 = ChercheUserForm(request.POST)
        if form3.is_valid():
            terme_recherche = form3.cleaned_data['nom']
    else:
        form3 = ChercheUserForm(None)
    form2 = SelectColleurForm(matiere,classe, terme_recherche, request.POST if ("supprimer" in request.POST or "modifier" in request.POST) else None)
    if form2.is_valid():
        if "supprimer" in request.POST:
            colleursPasSuppr = []
            for colleur in form2.cleaned_data['colleur']:
                try:
                    colleur.delete()
                except Exception:
                    colleursPasSuppr.append(str(colleur))
            if colleursPasSuppr:
                messages.error(request,"les colleurs suivants n'ont pas pu être supprimés:\n{}\n car ils sont reliés à des notes de colle ou à des colles".format("\n".join(colleursPasSuppr)))
            return redirect('gestion_colleur')
        elif "modifier" in request.POST:
            return redirect('modif_colleur', "-".join([str(colleur.pk) for colleur in form2.cleaned_data['colleur']]))
    colleurs = Colleur.objects.listeColleurs(matiere,classe,terme_recherche)
    return render (request,'administrateur/colleur.html',{'form':form,'form2':form2, 'form3': form3, 'colleurs':colleurs, 'listegrades':["inconnu","certifié","bi-admissible","agrégé","chaire supérieure"]})

@ip_filter
def colleurmodif(request, chaine_colleurs):
    """Renvoie la vue de la page de modification des colleurs dont l'id fait partie de chaine_colleurs"""
    listeColleurs = Colleur.objects.filter(pk__in=[int(i) for i in chaine_colleurs.split("-")]).order_by('user__last_name','user__first_name').select_related('user')
    Colleurformset = formset_factory(ColleurForm,extra=0,max_num=listeColleurs.count(),formset=ColleurFormSet)
    if request.method == 'POST':
        formset = Colleurformset(listeColleurs,request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('gestion_colleur')
    else:
        formset = Colleurformset(listeColleurs,initial=[{'last_name':colleur.user.last_name,'first_name':colleur.user.first_name,'username':colleur.user.username,'email':colleur.user.email,'is_active':colleur.user.is_active,'grade':colleur.grade,'etablissement':colleur.etablissement,'matiere':colleur.matieres.all(),'classe':colleur.classes.all()} for colleur in listeColleurs]) 
    return render(request,'administrateur/colleurmodif.html',{'formset':formset})

@ip_filter
def colleurajout(request):
    """Renvoie la vue de la page d'ajout de colleurs"""
    Colleurformset = formset_factory(ColleurFormMdp,formset=ColleurFormSetMdp)
    formset = Colleurformset(request.POST or None)
    if formset.is_valid():
        formset.save()
        return redirect('gestion_colleur')
    return render(request,'administrateur/colleurajout.html',{'formset':formset})

@ip_filter
def colleursuppr(request, id_colleur):
    """essaie de supprimer le colleur dont l'id est id_colleur, puis redirige vers la page de gestion des colleurs"""
    colleur=get_object_or_404(Colleur,pk=id_colleur)
    try:
        colleur.delete()
    except Exception:
        messages.error(request,"Impossible d'effacer le colleur car il possède des notes/colles")
    return redirect('gestion_colleur')

@ip_filter
def eleveTri(request, tri):
    """change la façon de trier les élèves puis redirige vers la page de gestion des élèves"""
    request.session['tri'] = "c" if tri == "1" else "e"
    return redirect('gestion_eleve')

@ip_filter
def eleve(request):
    """Renvoie la vue de la page de gestion des élèves"""
    if "selectclasse" in request.POST:
        form = ClasseSelectForm(request.POST)
    else:
        try:
            classe = Classe.objects.get(pk=request.session['classe'])
        except Exception:
            classe = None
        form = ClasseSelectForm(initial = {'classe':classe})
    if form.is_valid():
        classe = form.cleaned_data['classe']
        request.session['classe'] = None if not classe else classe.pk
    else:
        try:
            classe = Classe.objects.get(pk=request.session['classe'])
        except Exception:
            classe = None
    terme_recherche = ""
    if "chercheuser" in request.POST:
        form3 = ChercheUserForm(request.POST)
        if form3.is_valid():
            terme_recherche = form3.cleaned_data['nom']
    else:
        form3 = ChercheUserForm(None)
    # variable de session pour garder en mémoire selon quel critère on trie en premier (nom ou classe)
    # 'c' = classe en premier et nom en 2nd, 'e' = nom en premier, classe en second.
    tri = False
    if 'tri' in request.session:
        tri = request.session['tri'] == 'c'
    # si une classeest sélectionnée, par besoin de tri
    if classe is not None:
        tri = None
    form2 = SelectEleveForm(classe, tri, terme_recherche, request.POST if ("supprimer" in request.POST or "modifier" in request.POST or "transferer" in request.POST or "lv1" in request.POST or "lv2" in request.POST) else None)
    if form2.is_valid():
        if "supprimer" in request.POST:
            elevesPasSuppr = []
            for eleve in form2.cleaned_data['eleve']:
                try:
                    eleve.delete()
                except Exception:
                    elevesPasSuppr.append(str(eleve))
            if elevesPasSuppr:
                messages.error(request,"les élèves suivants n'ont pas pu être supprimés:\n{}\n car ils sont reliés à des notes de colle".format("\n".join(elevesPasSuppr)))
            return redirect('gestion_eleve')
        elif "modifier" in request.POST:
            return redirect('modif_eleve', "-".join([str(eleve.pk) for eleve in form2.cleaned_data['eleve']]))
        elif "transferer" in request.POST:
            # on retire les élèves qui ne changent pas de classe
            form2.cleaned_data['eleve']=form2.cleaned_data['eleve'].exclude(classe=form2.cleaned_data['klasse'])
            # on récupère les pk des groupes des élèves qui vont changer de classe
            groupes = Groupe.objects.filter(groupeeleve__in=form2.cleaned_data['eleve']).values_list('pk',flat=True)
            # on met à jour la classe des élèves dont ce n'est pas déjà la classe, et on les enlève de leur groupe
            form2.cleaned_data['eleve'].update(classe=form2.cleaned_data['klasse'],groupe=None)
            # on essaie d'effacer les groupes devenus vides (ce qui va échouer s'ils apparaissent dans le colloscope)
            try:
                Groupe.objects.filter(pk__in=groupes).annotate(nb=Count('groupeeleve')).filter(nb=0).delete()
            except Exception:
                pass
            return redirect('gestion_eleve')
        elif "lv1" in request.POST:
            # on commence par enlever les élèves dont la classe ne possède pas la langue en question, puis on met à jour la lv1
            if form2.cleaned_data['lv1'] is not None:
                form2.cleaned_data['eleve'].filter(classe__matieres=form2.cleaned_data['lv1']).update(lv1=form2.cleaned_data['lv1'])
            else: # dans le cas contraire c'est qu'on remet à zéro la lv1
                form2.cleaned_data['eleve'].update(lv1=None)
            return redirect('gestion_eleve')
        elif "lv2" in request.POST:
            # on commence par enlever les élèves dont la classe ne possède pas la langue en question, puis on met à jour la lv1
            if form2.cleaned_data['lv2'] is not None:
                form2.cleaned_data['eleve'].filter(classe__matieres=form2.cleaned_data['lv2']).update(lv2=form2.cleaned_data['lv2'])
            else: # dans le cas contraire c'est qu'on remet à zéro la lv1
                form2.cleaned_data['eleve'].update(lv2=None)
            return redirect('gestion_eleve')
    return render (request,'administrateur/eleve.html',{'form':form,'form2':form2, 'form3': form3, 'tri':tri})

@ip_filter
def elevecsv(request):
    """Renvoie la vue de la page d'ajout d'élèves via un fichier CSV"""
    form = CsvForm(request.POST or None, request.FILES or None,initial = {'nom':'Nom','prenom':'Prénom', 'ddn': 'Date de naissance', 'ldn': 'Commune', 'ine': 'Numéro INE','email':'Adresse mail'})
    if form.is_valid():
        try:
            with TextIOWrapper(form.cleaned_data['fichier'].file,encoding = 'utf8') as fichiercsv:
                dialect = csv.Sniffer().sniff(fichiercsv.read(4096))
                nom,prenom,ddn,ldn,ine,email=form.cleaned_data['nom'],form.cleaned_data['prenom'],form.cleaned_data['ddn'],form.cleaned_data['ldn'],form.cleaned_data['ine'],form.cleaned_data['email']
                fichiercsv.seek(0)
                reader = csv.DictReader(fichiercsv, dialect=dialect)
                ligne = next(reader)
                if not(nom in ligne and prenom in ligne):
                    messages.error("Les intitulés des champs nom et/ou prénom sont inexacts")
                else:
                    fichiercsv.seek(0)
                    next(reader)
                    initial = [{'last_name': ligneLoc[nom],'first_name':ligneLoc[prenom],'ddn':None if ddn not in ligneLoc else ligneLoc[ddn],'ldn':None if ldn not in ligneLoc else ligneLoc[ldn],\
                    'ine':'' if ine not in ligneLoc else ligneLoc[ine],'email':'' if email not in ligneLoc else ligneLoc[email],'classe':form.cleaned_data['classe']} for ligneLoc in reader]
                    return eleveajout(request,initial=initial)
        except Exception:
                messages.error(request,"Le fichier doit être un fichier CSV valide, encodé en UTF-8")
                return redirect('csv_eleve')
    return render(request,'administrateur/elevecsv.html',{'form':form})

@ip_filter
def elevemodif(request, chaine_eleves):
    """Renvoie la vue de la page de modification des élèves dont l'id fait partie de chaine_eleves"""
    listeEleves = Eleve.objects.filter(pk__in=[int(i) for i in chaine_eleves.split("-")]).order_by('user__last_name','user__first_name')
    EleveFormset = formset_factory(EleveForm,extra=0,max_num=listeEleves.count(),formset=EleveFormSet)
    if request.method == 'POST':
        formset = EleveFormset(listeEleves, request.POST, request.FILES)
        if formset.is_valid():
            formset.save()
            return redirect('gestion_eleve')
    else:
        formset = EleveFormset(chaine_eleves=listeEleves,initial=[{'last_name':eleve.user.last_name,'first_name':eleve.user.first_name,'ine':eleve.ine,\
            'ldn': eleve.ldn,'ddn': None if not eleve.ddn else eleve.ddn.strftime('%d/%m/%Y'),'username':eleve.user.username,'email':eleve.user.email,\
            'classe':eleve.classe,'photo':eleve.photo,'lv1':eleve.lv1,'lv2':eleve.lv2} for eleve in listeEleves])
    return render(request,'administrateur/elevemodif.html',{'formset':formset})

@ip_filter
def elevesuppr(request, id_eleve):
    """essaie de supprimer l'élève dont l'id est id_eleve, puis redirige vers la page de gestion des élèves"""
    eleve=get_object_or_404(Eleve,pk=id_eleve)
    try:
        eleve.delete()
    except Exception:
        messages.error(request,"Impossible d'effacer l'élève car il possède des notes/colles")
    return redirect('gestion_eleve')

@ip_filter
def eleveajout(request,initial=None):
    """Renvoie la vue de la page d'ajout d'élèves"""
    if request.method=="POST":
        EleveFormset = formset_factory(EleveFormMdp,extra=0,formset=EleveFormSetMdp)
        if "csv" in request.POST:
            print(initial)
            formset = EleveFormset(initial=initial)
        else:
            formset=EleveFormset(request.POST,request.FILES)
            if formset.is_valid():
                formset.save()
                return redirect('gestion_eleve')
    else:
        try:
            classe = Classe.objects.get(pk=request.session['classe'])
        except Exception:
            classe = None
        EleveFormset = formset_factory(EleveFormMdp,extra=0)
        formset=EleveFormset( initial = [{ 'classe' : classe}])
    return render(request,'administrateur/eleveajout.html',{'formset':formset})

@ip_filter
def prof(request):
    """Renvoie la vue de la page de gestion des profs"""
    return render(request,"administrateur/prof.html",{'profs':Prof.objects.listeprofs()})

@ip_filter
def profmodif(request, id_classe):
    """Renvoie la vue de la page de modification des profs de la classe dont l'id est id_classe"""
    classe=get_object_or_404(Classe,pk=id_classe)
    matieres = classe.matieres.all()
    initial=dict()
    initial['profprincipal'] = classe.profprincipal
    for matiere in matieres:
        colleur=Prof.objects.filter(matiere=matiere,classe=classe)
        if colleur.exists():
            initial[str(matiere.pk)]=list(colleur)[0].colleur
    form=ProfForm(classe,request.POST or None,initial=initial)
    if form.is_valid():
        form.save()
        return redirect('gestion_prof')
    return render(request,"administrateur/profmodif.html",{'classe':classe,'matieres':matieres,'form':form})

@ip_filter
def rgpd_eleve(request, eleve_id):
    try:
        eleve = Eleve.objects.filter(pk=eleve_id).select_related('user')[0]
    except Exception:
        raise Http404
    return render(request,"administrateur/rgpd_eleve.html", {'eleve': eleve})

@ip_filter
def rgpd_colleur(request, colleur_id):
    try:
        colleur = Colleur.objects.filter(pk=colleur_id).select_related('user')[0]
    except Exception:
        raise Http404
    return render(request,"administrateur/rgpd_colleur.html", {'colleur': colleur})

@ip_filter
def rgpd_eleve_pdf(request, eleve_id):
    try:
        eleve = Eleve.objects.filter(pk=eleve_id).select_related('user','classe','groupe','lv1','lv2')[0]
    except Exception:
        raise Http404
    nomfichier="RGPD_eleve-{}.pdf".format(eleve.pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
    marge_y = 40
    pdfformat = A4
    titre = "Données personnelles de l'étudiant {}".format(eleve)

    def myFirstPage(canvas, doc):
        canvas.saveState()
        x=pdfformat[0]/2
        y=pdfformat[1]-marge_y
        canvas.setFont("Helvetica-Bold",12)
        canvas.drawCentredString(x,y,titre)
        y-=20
        canvas.drawCentredString(x,y,Config.objects.get_config().nom_etablissement)
        x=pdfformat[0]/2
        y=marge_y
        canvas.setFont("Helvetica-Oblique",8)
        canvas.drawCentredString(x,y,"page n°{}".format(canvas.getPageNumber()))
        canvas.restoreState()

    pdfbuffer = BytesIO()
    doc = SimpleDocTemplate(pdfbuffer)
    doc.leftMargin = doc.rightMargin = 20
    style = ParagraphStyle(name='soustitre',
        fontSize=12,
        alignment = TA_CENTER,
        fontName="Helvetica-Bold",
        borderColor='black',
        borderPadding=(2,0,6,0),
        borderWidth=0,
        backColor='#DDDDDD',
        spaceBefore=0,
        spaceAfter=20)
    stylebis = ParagraphStyle(name='commentaire',
        fontSize=9,
        alignment = TA_LEFT,
        borderColor='black',
        borderPadding=(0,2,0,2),
        borderWidth = 1,
        fontName="Helvetica-Bold")
    par1 = Paragraph("Données utilisateur", style)
    LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
                                        ,('VALIGN',(0,0),(-1,-1),'MIDDLE')
                                        ,('ALIGN',(0,0),(-1,-1),'CENTRE')
                                        ,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
                                        ,('SIZE',(0,0),(-1,-1),9)])
    data = [("Nom:", eleve.user.last_name.upper()),
    ("Prénom:", eleve.user.first_name.title()),
    ("Identifiant:", eleve.user.username)]
    if eleve.user.email:
        data.append(('Email:', eleve.user.email))
    if eleve.user.date_joined:
        data.append(('ajouté le:', eleve.user.date_joined.strftime("%d/%m/%Y à %Hh%M")))
    if eleve.user.last_login:
        data.append(('Dernière connexion le:', eleve.user.last_login.strftime("%d/%m/%Y à %Hh%M")))
    if eleve.ine:
        data.append(('Numéro INE:', eleve.ine))
    if eleve.ddn:
        data.append(('Date de naissance:', eleve.ddn.strftime("%d/%m/%Y")))
    if eleve.ldn:
        data.append(('Lieu de naissance:', eleve.ldn))
    if eleve.classe:
        data.append(('Classe:', eleve.classe.nom))
    if eleve.groupe:
        data.append(('Groupe:', eleve.groupe.nom))
    if eleve.lv1:
        data.append(('LV1:', eleve.lv1.nom.title()))
    if eleve.lv2:
        data.append(('LV2', eleve.lv2.nom.title()))
    if eleve.photo:
        image = Image(join(MEDIA_ROOT, str(eleve.photo)))
        image.drawHeight = 80
        image.drawWidth = 60
        data.append(('Photo', image))
    t=Table(data, colWidths=200, repeatRows = 1)
    t.setStyle(LIST_STYLE)
    story = [par1, t, PageBreak()]
    if Note.objects.filter(eleve = eleve).exists(): # si l'élève a des notes:
        par2 = Paragraph("Notes de colle", style)
        story.append(par2)
        notes = Note.objects.filter(eleve = eleve).select_related('eleve__user','matiere','colleur__user').order_by('-date_colle', '-heure')
        LISTE_NOTES = list(range(21)) + ["n.n", "abs."]
        for note in notes:
            data = [(note.date_colle.strftime('%d/%m/%Y'), "{}h{:02d}".format(note.heure//60, note.heure%60), str(note.colleur), str(note.matiere), str(LISTE_NOTES[note.note]))]
            t=Table(data, colWidths=(80, 60, 170, 170, 60))
            t.setStyle(LIST_STYLE)
            story.append(t)
            if note.commentaire:
                par = Paragraph("<u>commentaire:</u> " + note.commentaire.replace("\n", "<br/>"), stylebis)
                story.append(par)
        story.append(PageBreak())
    if NoteECTS.objects.filter(eleve = eleve).exists(): # si l'élève a des notes ECTS
        par2 = Paragraph("Notes ECTS", style)
        story.append(par2)
        LISTE_NOTES_ECTS = "ABCDEF"
        notesECTS = NoteECTS.objects.filter(eleve = eleve).select_related('matiereECTS').order_by('semestre','matiereECTS__nom')
        data = [("semestre", "matière", "note")]
        data += [(note.semestre, note.matiere.nom, LISTE_NOTES_ECTS[note.note]) for note in notesECTS]
        t=Table(data, colWidths=(50, 200, 50), repeatRows = 1)
        t.setStyle(LIST_STYLE)
        story.append(t)
        story.append(PageBreak())
    if Message.objects.filter(auteur = eleve.user).exists(): # si l'élève a envoyé des messages
        par2 = Paragraph("Messages envoyés", style)
        story.append(par2)
        messages = Message.objects.filter(auteur = eleve.user)
        for message in messages:
            texte = "<u>Envoyé le</u> {} <br/> <u>à</u>: {} <br/> <u>sujet</u>: {} <br/> {}".format(message.date.strftime("%d/%m/%Y à %Hh%M"),
                message.listedestinataires, message.titre, message.corps.replace("\n", "<br/>"))
            par = Paragraph(texte, stylebis)
            story.append(par)
    doc.build(story, onFirstPage=myFirstPage, onLaterPages=myFirstPage)
    fichier = pdfbuffer.getvalue()
    pdfbuffer.close()
    response.write(fichier)
    return response

@ip_filter
def eleve_force_efface(request, eleve_id):
    eleve=get_object_or_404(Eleve, pk=eleve_id)
    with transaction.atomic():# on fait tout ou rien
        # on met l'élève à None pour toutes ses notes et on efface les commentaires, l'élève devient élève fictif sur ces notes
        # il ne faut pas effacer les notes sinon le décompte des heures pour les colleurs va être faussé.
        Note.objects.filter(eleve=eleve).update(eleve=None, commentaire="")
        Colle.objects.filter(eleve=eleve).delete()
        # on efface tous ses messages envoyés
        Message.objects.filter(auteur=eleve.user).delete()
        Destinataire.objects.filter(user=eleve.user).delete()
        # on efface les éventuels crédits ECTS
        NoteECTS.objects.filter(eleve=eleve).delete()
        # on efface l'élève
        eleve.delete()
        messages.error(request,"L'élève a été définitivement effacé")
        return redirect('gestion_eleve')
    messages.error(request,"L'élève n'a pas pu être effacé")
    return redirect('gestion_eleve')

@ip_filter
def rgpd_colleur_pdf(request, colleur_id):
    try:
        colleur = Colleur.objects.filter(pk=colleur_id).select_related('user').prefetch_related('classes','matieres')[0]
    except Exception:
        raise Http404
    nomfichier="RGPD_colleur-{}.pdf".format(colleur.pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
    marge_y = 40
    pdfformat = A4
    titre = "Données personnelles du colleur {}".format(colleur)

    def myFirstPage(canvas, doc):
        canvas.saveState()
        x=pdfformat[0]/2
        y=pdfformat[1]-marge_y
        canvas.setFont("Helvetica-Bold",12)
        canvas.drawCentredString(x,y,titre)
        y-=20
        canvas.drawCentredString(x,y,Config.objects.get_config().nom_etablissement)
        x=pdfformat[0]/2
        y=marge_y
        canvas.setFont("Helvetica-Oblique",8)
        canvas.drawCentredString(x,y,"page n°{}".format(canvas.getPageNumber()))
        canvas.restoreState()

    pdfbuffer = BytesIO()
    doc = SimpleDocTemplate(pdfbuffer)
    doc.leftMargin = doc.rightMargin = 20
    style = ParagraphStyle(name='soustitre',
        fontSize=12,
        alignment = TA_CENTER,
        fontName="Helvetica-Bold",
        borderColor='black',
        borderPadding=(2,0,6,0),
        borderWidth=0,
        backColor='#DDDDDD',
        spaceBefore=0,
        spaceAfter=20)
    stylebis = ParagraphStyle(name='commentaire',
        fontSize=9,
        alignment = TA_LEFT,
        borderColor='black',
        borderPadding=(0,2,0,2),
        borderWidth = 1,
        fontName="Helvetica-Bold")
    par1 = Paragraph("Données utilisateur", style)
    LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
                                        ,('VALIGN',(0,0),(-1,-1),'MIDDLE')
                                        ,('ALIGN',(0,0),(-1,-1),'CENTRE')
                                        ,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
                                        ,('SIZE',(0,0),(-1,-1),9)])
    data = [("Nom:", colleur.user.last_name.upper()),
    ("Prénom:", colleur.user.first_name.title()),
    ("Identifiant:", colleur.user.username)]
    if colleur.user.email:
        data.append(('Email:', colleur.user.email))
    if colleur.user.date_joined:
        data.append(('ajouté le:', colleur.user.date_joined.strftime("%d/%m/%Y à %Hh%M")))
    if colleur.user.last_login:
        data.append(('Dernière connexion le:', colleur.user.last_login.strftime("%d/%m/%Y à %Hh%M")))
    if colleur.classes:
        data.append(('Classes:', ";".join([classe.nom for classe in colleur.classes.all()])))
    if colleur.matieres:
        data.append(('Matières:', ";".join([str(matiere) for matiere in colleur.matieres.all()])))
    if Prof.objects.filter(colleur = colleur).exists():
        data.append(('Professeur:', ";".join([str(prof.matiere) + "/" + prof.classe.nom for prof in Prof.objects.filter(colleur = colleur).all()])))
    t=Table(data, colWidths=200, repeatRows = 1)
    t.setStyle(LIST_STYLE)
    story = [par1, t, PageBreak()]
    if Note.objects.filter(colleur = colleur).exists(): # si le colleur a des notes:
        par2 = Paragraph("Notes de colle", style)
        story.append(par2)
        notes = Note.objects.filter(colleur = colleur).select_related('eleve__user','matiere','colleur__user').order_by('-date_colle', '-heure')
        LISTE_NOTES = list(range(21)) + ["n.n", "abs."]
        for note in notes:
            data = [(note.date_colle.strftime('%d/%m/%Y'), "{}h{:02d}".format(note.heure//60, note.heure%60), str(note.eleve), str(note.matiere), str(LISTE_NOTES[note.note]))]
            t=Table(data, colWidths=(80, 60, 170, 170, 60))
            t.setStyle(LIST_STYLE)
            story.append(t)
            if note.commentaire:
                par = Paragraph("<u>commentaire:</u> " + note.commentaire.replace("\n", "<br/>"), stylebis)
                story.append(par)
        story.append(PageBreak())
    if Message.objects.filter(auteur = colleur.user).exists(): # si le colleur a envoyé des messages
        par2 = Paragraph("Messages envoyés", style)
        story.append(par2)
        messages = Message.objects.filter(auteur = colleur.user)
        for message in messages:
            texte = "<u>Envoyé le</u> {} <br/> <u>à</u>: {} <br/> <u>sujet</u>: {} <br/> {}".format(message.date.strftime("%d/%m/%Y à %Hh%M"),
                message.listedestinataires, message.titre, message.corps.replace("\n", "<br/>"))
            par = Paragraph(texte, stylebis)
            story.append(par)
    doc.build(story, onFirstPage=myFirstPage, onLaterPages=myFirstPage)
    fichier = pdfbuffer.getvalue()
    pdfbuffer.close()
    response.write(fichier)
    return response


@ip_filter
def colleur_force_efface(request, colleur_id):
    colleur = get_object_or_404(Colleur, pk=colleur_id)
    with transaction.atomic():
        Note.objects.filter(colleur = colleur).update(colleur = None)
        Colle.objects.filter(colleur = colleur).delete()
        Message.objects.filter(auteur = colleur.user).delete()
        Destinataire.objects.filter(user = colleur.user).delete()
        colleur.delete()
        messages.error(request, "Le colleur a été définitivement effacé")
        return redirect('gestion_colleur')
    messages.error(request, "Le colleur n'a pas pu être effacé")
    return redirect('gestion_colleur')
