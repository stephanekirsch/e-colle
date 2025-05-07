#-*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import user_passes_test
from administrateur.forms import AdminConnexionForm, InformationForm
from colleur.forms import ECTSForm, MatiereECTSForm
from secretariat.forms import MoisForm, RamassageForm, MatiereClasseSemaineSelectForm, ColleurSelectForm
from accueil.models import Config, Note, Semaine, Matiere, Colleur, Ramassage, Classe, Eleve, Groupe, Creneau, mois, MatiereECTS, NoteECTS, Information
from mixte.mixte import mixtegroupe, mixtegroupesuppr, mixtegroupeSwap, mixtegroupemodif, mixtecolloscope,mixtecolloscopemodif, mixtecreneaudupli, mixtecreneausuppr, mixteajaxcompat, mixteajaxcolloscope, mixteajaxcolloscopeeleve, mixteajaxmajcolleur, mixteajaxcolloscopeeffacer, mixteajaxcolloscopemulti, mixteajaxcolloscopemulticonfirm, mixteRamassagePdfParClasse, mixteRamassagePdfParColleur, mixteCSV, mixtegroupeCreer, mixtegroupecsv, mixteColloscopeImport
from django.http import Http404, HttpResponse,  HttpResponseForbidden
from pdf.pdf import Pdf, easyPdf, creditsects, attestationects, publipostage
from reportlab.platypus import Table, TableStyle
from datetime import timedelta
from django.db.models import Max, Min
import csv
SECRETARIAT = 2

def is_secret(user):
    """Renvoie True si l'utilisateur est le secrétariat, False sinon"""
    return user.is_authenticated and user.username=="Secrétariat"

def is_secret_ects(user):
    """Renvoie True si l'utilisateur est le secrétariat et ECTS activé, False sinon"""
    return is_secret(user) and Config.objects.get_config().ects

def is_secret_modif_ects(user):
    """Renvoie True si l'utilisateur est le secrétariat et ECTS activé avec droits  de modification des matires et des coeffs, False sinon"""
    return is_secret_ects(user) and Config.objects.get_config().ects_modif&SECRETARIAT!=0

def connec(request):
    """Renvoie la vue de la page de connexion du secrétariat. Si le secrétariat est déjà connecté, redirige vers la page d'accueil du secrétariat"""
    if is_secret(request.user):
        return redirect('action_secret')
    error = False
    form = AdminConnexionForm(request.POST or None, initial={'username':"Secrétariat"})
    if form.is_valid():
        password = form.cleaned_data['password']
        user = authenticate(username="Secrétariat",password=password)
        if user:
            login(request,user)
            return redirect('action_secret')
        else:
            error = True
    form.fields['username'].widget.attrs['readonly'] = True
    return render(request,'secretariat/home.html',{'form':form,'error':error})

@user_passes_test(is_secret, login_url='login_secret')
def action(request):
    """Renvoie la vue de la page d'accueil du secrétariat"""
    return render(request,"secretariat/action.html",{'classes':Classe.objects.all()})

@user_passes_test(is_secret, login_url='login_secret')
def resultats(request):
    """Renvoie la vue de la page de consultation des résultats des classes"""
    form = MatiereClasseSemaineSelectForm(request.POST or None)
    if request.method=="POST":
        if form.is_valid():
            classe = form.cleaned_data['classe']
            matiere = form.cleaned_data['matiere']
            semin = form.cleaned_data['semin']
            semax = form.cleaned_data['semax']
            request.session['classe'] = classe.pk
            request.session['matiere'] = matiere.pk
            request.session['semin'] = semin.pk
            request.session['semax'] = semax.pk
            return redirect('resultats_secret')
        classe=matiere=semin=semax=semaines=generateur=None
    else:   
        try:
            classe = Classe.objects.get(pk=request.session['classe'])
            matiere = Matiere.objects.get(pk=request.session['matiere'])
            semin = Semaine.objects.get(pk=request.session['semin'])
            semax = Semaine.objects.get(pk=request.session['semax'])
        except Exception:
            classe=matiere=semin=semax=semaines=generateur=None
            form = MatiereClasseSemaineSelectForm(request.POST or None)
        else:
            generateur = Note.objects.classe2resultat(matiere,classe,semin,semax)
            semaines = next(generateur)
            form = MatiereClasseSemaineSelectForm(initial = {'classe':classe,'matiere':matiere,'semin':semin,'semax':semax})        
    return render(request,"secretariat/resultats.html",{'form':form,'classe':classe,'matiere':matiere,'semaines':semaines,'notes':generateur, 'semin':semin,'semax':semax,'classes':Classe.objects.all()})

@user_passes_test(is_secret, login_url='login_secret')
def resultatcsv(request,id_classe,id_matiere,id_semin,id_semax):
    """Renvoie le fichier CSV des résultats de la classe dont l'id est id_classe, dans la matière dont l'id est id_matiere
    entre les semaines dont l'id est id_semin et id_semax"""
    classe=get_object_or_404(Classe,pk=id_classe)
    matiere = get_object_or_404(Matiere,pk=id_matiere)
    semin = get_object_or_404(Semaine,pk=id_semin)
    semax = get_object_or_404(Semaine,pk=id_semax)
    generateur = Note.objects.classe2resultat(matiere,classe,semin,semax)
    semaines = next(generateur)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="resultats_{}_{}.csv"'.format(classe.nom,matiere.nom)
    writer = csv.writer(response)
    writer.writerow(['Élève','rang','moyenne']+['S{}'.format(semaine.numero) for semaine in semaines])
    notation = {i:str(i) for i in range(21)}
    notation[21]="n.n."
    notation[22]="abs"
    for note in generateur:
        writer.writerow([note['eleve'],note['rang'],note['moyenne']]+["|".join([notation[note['note']] for note in value]) for value in note['semaine']])
    return response

@user_passes_test(is_secret, login_url='login_secret')
def information(request):
    """Renvoie la vue de la page où l'on déterminer l'éventuel message d'Accueil des colleurs et/ou élèves"""
    infos = Information.objects.filter(expediteur = 2)
    form = InformationForm(request.POST or None, instance = Information(expediteur=2))
    if form.is_valid():
        form.save()
        return redirect('information_secret')
    return render(request,'mixte/information.html', {'form':form, 'infos': infos, 'expe':{1:"Colleurs", 2:"Élèves", 3:"Tout le monde"} , 'isadmin':False})

@user_passes_test(is_secret, login_url='login_secret')
def informationSuppr(request, id_info):
    """Supprime l'info dont l"id est id_info"""
    info = get_object_or_404(Information, pk=id_info)
    info.delete()
    return redirect('information_secret')

@user_passes_test(is_secret, login_url='login_secret')
def informationModif(request, id_info):
    """Modifie l'info dont l"id est id_info"""
    if id_info != "0":
        info = get_object_or_404(Information, pk=id_info)
    else:
        info = Information(expediteur = 2, destinataire = 3)
    form = InformationForm(request.POST or None, instance = info)
    if form.is_valid():
        form.save()
        return redirect('information_secret')
    return render(request, 'mixte/informationmodif.html', {'form':form, 'isadmin': False, "modif": id_info != "0"})

@user_passes_test(is_secret, login_url='login_secret')
def notes(request):
    form = ColleurSelectForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            request.session["colleur"] = form.cleaned_data["colleur"].pk
            request.session["matierenote"] = False if not form.cleaned_data["matiere"] else form.cleaned_data["matiere"].pk
            request.session["classenote"] = False if not form.cleaned_data["classe"] else form.cleaned_data["classe"].pk
            return redirect('notes_secret')
    else:
        try:
            colleur = Colleur.objects.get(pk=request.session["colleur"])
            matiere = False if not request.session["matierenote"] else request.session["matierenote"]
            classe = False if not request.session["classenote"] else request.session["classenote"]
        except Exception:
            colleur = notes = False
        else:
            notes = Note.objects.filter(colleur = colleur)
            if matiere:
                notes = notes.filter(matiere = matiere)
            if classe:
                notes = notes.filter(classe = classe)
            notes = notes.select_related("eleve","eleve__user","matiere","classe","semaine").order_by('-date_colle','-heure')
            form = ColleurSelectForm(initial = {"colleur":colleur, "matiere":matiere, "classe":classe})
    return render(request,"secretariat/notes.html",{"form": form, "colleur": colleur, "notes": notes})

@user_passes_test(is_secret, login_url='login_secret')
def colloscope(request,transpose,id_classe):
    """Renvoie la vue de la page du colloscope de la classe dont l'id est id_classe"""
    semaines=list(Semaine.objects.all())
    try:
        semin,semax=semaines[0],semaines[-1]
    except Exception:
        raise Http404
    if transpose == "0" and "transpose" in request.session and request.session["transpose"] is True:
        transpose = "1" 
    return colloscope2(request,transpose,id_classe,semin.pk,semax.pk)

@user_passes_test(is_secret, login_url='login_secret')
def colloscope2(request,transpose,id_classe,id_semin,id_semax):
    """Renvoie la vue de la page du colloscope de la classe dont l'id est id_classe entre les semaines dont l'id est id_semin et id_semax"""
    classe=get_object_or_404(Classe,pk=id_classe)
    semin=get_object_or_404(Semaine,pk=id_semin)
    semax=get_object_or_404(Semaine,pk=id_semax)
    isprof = Config.objects.get_config().modif_secret_col
    return mixtecolloscope(request,classe,semin,semax,isprof,int(transpose))

@user_passes_test(is_secret, login_url='login_secret')
def colloscopePdf(request,id_classe,id_semin,id_semax):
    """Renvoie le fichier PDF du colloscope de la classe dont l'id est id_classe, entre les semaines d'id id_semin et id_semax"""
    classe=get_object_or_404(Classe,pk=id_classe)
    semin=get_object_or_404(Semaine,pk=id_semin)
    semax=get_object_or_404(Semaine,pk=id_semax)
    return Pdf(classe,semin,semax)

@user_passes_test(is_secret, login_url='login_secret')
def colloscopeCsv(request,id_classe,id_semin,id_semax):
    """Renvoie le fichier PDF du colloscope de la classe dont l'id est id_classe, entre les semaines d'id id_semin et id_semax"""
    classe=get_object_or_404(Classe,pk=id_classe)
    semin=get_object_or_404(Semaine,pk=id_semin)
    semax=get_object_or_404(Semaine,pk=id_semax)
    return mixteCSV(request,classe,semin,semax)

@user_passes_test(is_secret, login_url='accueil')
def colloscopeModif(request,id_classe,id_semin,id_semax,creneaumodif=None):
    """Renvoie la vue de la page de modification du colloscope de la classe dont l'id est id_classe,
    dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    classe=get_object_or_404(Classe,pk=id_classe)
    semin=get_object_or_404(Semaine,pk=id_semin)
    semax=get_object_or_404(Semaine,pk=id_semax)
    return mixtecolloscopemodif(request,classe,semin,semax,creneaumodif)

@user_passes_test(is_secret, login_url='accueil')
def colloscopeImport(request,id_classe):
    """Renvoie la vue de la page d'import' du colloscope de la classe dont l'id est id_classe"""
    classe=get_object_or_404(Classe,pk=id_classe)
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    return mixteColloscopeImport(request,classe)
    
@user_passes_test(is_secret, login_url='accueil')
def creneauSuppr(request,id_creneau,id_semin,id_semax):
    """Essaie de supprimer le créneau dont l'id est id_creneau puis redirige vers la page de modification du colloscope
    dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    return mixtecreneausuppr(request,creneau,id_semin,id_semax)

@user_passes_test(is_secret, login_url='accueil')
def creneauModif(request,id_creneau,id_semin,id_semax):
    """Renvoie la vue de la page de modification du creneau dont l'id est id_creneau"""
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    return colloscopeModif(request,creneau.classe.pk,id_semin,id_semax,creneaumodif=creneau)

@user_passes_test(is_secret, login_url='accueil')
def creneauDupli(request,id_creneau,id_semin,id_semax):
    """Renvoie la vue de la page de duplication du creneau dont l'id est id_creneau"""
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    return mixtecreneaudupli(request.user,creneau,id_semin,id_semax)

@user_passes_test(is_secret, login_url='accueil')
def ajaxcompat(request,id_classe):
    """Renvoie une chaîne de caractères récapitulant les incompatibilités du colloscope de la classe dont l'id est id_classe"""
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    classe=get_object_or_404(Classe,pk=id_classe)
    return mixteajaxcompat(classe)

@user_passes_test(is_secret, login_url='accueil')
def ajaxmajcolleur(request, id_matiere, id_classe):
    """Renvoie la liste des colleurs de la classe dont l'id est id_classe et de la matière dont l'id est id_matiere, au format json"""
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    classe=get_object_or_404(Classe,pk=id_classe)
    matiere=get_object_or_404(Matiere,pk=id_matiere)
    return mixteajaxmajcolleur(matiere,classe)
    

@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscope(request, id_matiere, id_colleur, id_groupe, numero_semaine, id_creneau):
    """Ajoute la colle propre au quintuplet (matière,colleur,groupe,semaine,créneau) et renvoie le username du colleur
    en effaçant au préalable toute colle déjà existante sur ce couple créneau/semaine"""
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    matiere=get_object_or_404(Matiere,pk=id_matiere)
    colleur=get_object_or_404(Colleur,pk=id_colleur)
    groupe=get_object_or_404(Groupe,pk=id_groupe)
    semaine=get_object_or_404(Semaine,numero=numero_semaine)
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    return mixteajaxcolloscope(matiere,colleur,groupe,semaine,creneau)
    

@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscopeeleve(request, id_matiere, id_colleur, id_eleve, numero_semaine, id_creneau, login):
    """Ajoute la colle propre au quintuplet (matière,colleur,eleve,semaine,créneau) et renvoie le username du colleur
    en effaçant au préalable toute colle déjà existante sur ce couple créneau/semaine"""
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    matiere=get_object_or_404(Matiere,pk=id_matiere)
    colleur=get_object_or_404(Colleur,pk=id_colleur)
    semaine=get_object_or_404(Semaine,numero=numero_semaine)
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    return mixteajaxcolloscopeeleve(matiere,colleur, id_eleve,semaine,creneau,login)

@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscopeeffacer(request, numero_semaine, id_creneau):
    """Efface la colle sur le créneau dont l'id est id_creneau et la semaine dont le numéro est numero_semaine
    puis renvoie la chaine de caractères "efface" """
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    semaine=get_object_or_404(Semaine,numero=numero_semaine)
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    return mixteajaxcolloscopeeffacer(semaine,creneau)

@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscopemulti(request, id_matiere, id_colleur, id_groupe, id_eleve, numero_semaine, id_creneau, duree, frequence, permutation):
    """Compte le nombre de colles présente sur les couples créneau/semaine sur le créneau dont l'id est id_creneau
    et les semaines dont le numéro est compris entre celui de la semaine d'id id_semaine et ce dernier + duree
    et dont le numéro est congru à celui de la semaine d'id id_semaine modulo frequence
    S'il n'y en a aucune, ajoute les colles sur les couples créneau/semaine précédents, avec le colleur dont l'id est id_colleur
    le groupe démarre au groupe dont l'id est id_groupe puis va de permutation en permutation, et la matière dont l'id est id_matière"""
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    if id_matiere != "-1": # si on n'efface pas des colles
        matiere=get_object_or_404(Matiere,pk=id_matiere)
        colleur=get_object_or_404(Colleur,pk=id_colleur)
    else:
        matiere = -1
        colleur = 0
    semaine=get_object_or_404(Semaine,numero=numero_semaine)
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    return mixteajaxcolloscopemulti(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation)
    
@user_passes_test(is_secret, login_url='accueil')
def ajaxcolloscopemulticonfirm(request, id_matiere, id_colleur, id_groupe, id_eleve, numero_semaine, id_creneau, duree, frequence, permutation):
    """ajoute les colles sur les couples créneau/semaine sur le créneau dont l'id est id_creneau
    et les semaines dont le numéro est compris entre celui de la semaine d'id id_semaine et ce dernier + duree
    et dont le numéro est congru à celui de la semaine d'id id_semaine modulo frequence, avec le colleur dont l'id est id_colleur
    le groupe démarre au groupe dont l'id est id_groupe puis va de permutation en permutation, et la matière dont l'id est id_matière"""
    if not Config.objects.get_config().modif_secret_col:
        return HttpResponseForbidden("Accès non autorisé")
    matiere=get_object_or_404(Matiere,pk=id_matiere)
    colleur=get_object_or_404(Colleur,pk=id_colleur)
    semaine=get_object_or_404(Semaine,numero=numero_semaine)
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    return mixteajaxcolloscopemulticonfirm(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation)

@user_passes_test(is_secret, login_url='login_secret')
def recapitulatif(request):
    """Renvoie la vue de la page de récapitulatif des heures de colle"""
    moisMin,moisMax=mois()
    form = MoisForm(moisMin,moisMax,request.POST or None)
    if form.is_valid():
        moisMin=form.cleaned_data['moisMin']
        moisMax=form.cleaned_data['moisMax']
    listeDecompte,effectifs=Ramassage.objects.decompte(moisMin,moisMax)
    return render(request,"secretariat/recapitulatif.html",{'form':form,'decompte':listeDecompte,'effectifs':effectifs})

@user_passes_test(is_secret, login_url='login_secret')
def compta(request):
    LISTE_NOTES = list(range(21)) + ["n.n","Abs"]
    notes = Note.objects.select_related("colleur__user","eleve__user", "semaine","classe").order_by('colleur__user__last_name', 'colleur__user__first_name', 'date_colle')
    nomfichier="compta.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
    writer = csv.writer(response)
    writer.writerow(["Nom","prénom","Matière","classe","étudiant","semaine","date","heure","note","temps (min)"])
    for note in notes:
        # writer.writerow([note["colleur__user__last_name"].upper(), note["colleur__user__first_name"].title(), note["matiere__nom"].title(),
        #     "élève fictif" if note["eleve"] is None else "{} {}".format(note["eleve__user__last_name"].upper,note["eleve__user__first_name"].title()),
        #     note["semaine__numero"], note["date_colle"].strftime("%d/%m/%Y"), "{}h{:02d}".format(note["heure"]//60,note["heure"]%60), LISTE_NOTES[note["note"]]])
        writer.writerow([note.colleur.user.last_name.upper(), note.colleur.user.first_name.title(), note.matiere.nom.title(), note.classe.nom,
            "élève fictif" if note.eleve is None else "{} {}".format(note.eleve.user.last_name.upper(),note.eleve.user.first_name.title()),
            note.semaine.numero, note.date_colle.strftime("%d/%m/%Y"), "{}h{:02d}".format(note.heure//60,note.heure%60), LISTE_NOTES[note.note], note.matiere.temps])

    return response

@user_passes_test(is_secret, login_url='login_secret')
def ramassage(request):
    """Renvoie la vue de la page de ramassage des heures de colle"""
    form = RamassageForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('ramassage')
    ramassages=Ramassage.objects.all()
    return render(request,"secretariat/ramassage.html",{'form':form,'ramassages':ramassages,'hauteur':len(ramassages)})

@user_passes_test(is_secret, login_url='login_secret')
def ramassageSuppr(request,id_ramassage):
    """Essaie d'effacer le ramassage dont l'id est id_ramassage, puis redirige vers la page de gestion des ramassages"""
    ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
    ramassage.delete()
    return redirect('ramassage')

@user_passes_test(is_secret, login_url='login_secret')
def ramassageCSV(request,id_ramassage,parMois = 0, full = 0):
    """Renvoie le fichier CSV du ramassage par année/effectif correspondant au ramassage dont l'id est id_ramassage"""
    parMois = int(parMois)
    full = int(full)
    ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
    LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
    response = HttpResponse(content_type='text/csv')
    if Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).exists() and not full: #s'il existe un ramassage antérieur
        debut = Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).aggregate(Max('moisFin'))['moisFin__max']
    else:
        debut = Semaine.objects.aggregate(Min('lundi'))['lundi__min']
    fin = ramassage.moisFin
    listeDecompte, effectifs = Ramassage.objects.decompteRamassage(ramassage, csv = True, parClasse = False, parMois =parMois, full = full)
    nomfichier="ramassage{}-{}-{}_{}-{}-{}.csv".format(debut.year,debut.month,debut.day,fin.year,fin.month,fin.day)
    response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
    writer = csv.writer(response)
    writer.writerow(["Matière","Établissement","Grade","Nom","Prénom"]+ (["mois"] if parMois else []) +["{}è. ann.  {}".format(annee,effectif) for annee,effectif in effectifs])
    LISTE_GRADES=["inconnu","certifié","bi-admissible","agrégé","chaire sup"]
    if parMois:
        for matiere, etablissement, grade, colleur_nom, colleur_prenom, _, moi, heures in listeDecompte:
            writer.writerow([matiere.title(), etablissement.title(),
                                LISTE_GRADES[grade], colleur_nom.upper(), colleur_prenom.title(), LISTE_MOIS[moi%12+1]] + ["{:.2f}".format(heures[i]/60).replace('.',',') for i in range(len(effectifs))])
    else:
        for matiere, etablissement, grade, colleur_nom, colleur_prenom, _, heures in listeDecompte:
            writer.writerow([matiere.title(), etablissement.title(),
                                LISTE_GRADES[grade], colleur_nom.upper(), colleur_prenom.title()] + ["{:.2f}".format(heures[i]/60).replace('.',',') for i in range(len(effectifs))])
    return response

@user_passes_test(is_secret, login_url='login_secret')
def ramassagePdf(request, id_ramassage, parMois = 0, full = 0):
    """Renvoie le fichier PDF du ramassage par année/effectif correspondant au ramassage dont l'id est id_ramassage"""
    parMois = int(parMois) // 2
    full=int(full)
    ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
    LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
    LISTE_MOIS_COURT=["jan","fev","mar","avr","mai","juin","juil","aou","sep","oct","nov","dec"]
    response = HttpResponse(content_type='application/pdf')
    if Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).exists() and not full: #s'il existe un ramassage antérieur
        debut = Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).aggregate(Max('moisFin'))['moisFin__max']+timedelta(days=1)
    else:
        debut = Semaine.objects.aggregate(Min('lundi'))['lundi__min']
    fin = ramassage.moisFin
    moisdebut = 12*debut.year+debut.month-1
    listeDecompte, effectifs = Ramassage.objects.decompteRamassage(ramassage, csv = False, parClasse = False, parMois=parMois, full = full)
    nomfichier="ramassage{}-{}-{}_{}-{}-{}.pdf".format(debut.year,debut.month,debut.day,fin.year,fin.month,fin.day)
    response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
    pdf = easyPdf(titre="Ramassage des colles du {} au {}".format(debut.strftime("%d/%m/%Y"),fin.strftime("%d/%m/%Y")),marge_x=30,marge_y=30)
    largeurcel=(pdf.format[0]-2*pdf.marge_x)/(9+parMois+len(effectifs))
    hauteurcel=30
    nbKolleurs=sum([z for x,y,z in listeDecompte])
    pdf.debutDePage()
    LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
                                        ,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
                                        ,('VALIGN',(0,0),(-1,-1),'MIDDLE')
                                        ,('ALIGN',(0,0),(-1,-1),'CENTRE')
                                        ,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
                                        ,('SIZE',(0,0),(-1,-1),8)])
    data = [["Matière","Établissement","Grade","Colleur"] + (["Mois"] if parMois else []) + ["{}è. ann.\n{}".format(annee,effectif) for annee,effectif in effectifs]]+[[""]*(4+parMois+len(effectifs)) for i in range(min(23,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
    ligneMat=ligneEtab=ligneGrade=ligneColleur=ligneMois=1
    for matiere, listeEtabs, nbEtabs in listeDecompte:
        data[ligneMat][0]=matiere.title()
        if nbEtabs>1:
            LIST_STYLE.add('SPAN',(0,ligneMat),(0,min(ligneMat+nbEtabs-1,23)))
        ligneMat+=nbEtabs
        for etablissement, listeGrades, nbGrades in listeEtabs:
            data[ligneEtab][1]=etablissement.title()
            if nbGrades>1:
                LIST_STYLE.add('SPAN',(1,ligneEtab),(1,min(ligneEtab+nbGrades-1,23)))
            ligneEtab+=nbGrades
            for grade, listeColleurs, nbColleurs in listeGrades:
                data[ligneGrade][2]=grade
                if nbColleurs>1:
                    LIST_STYLE.add('SPAN',(2,ligneGrade),(2,min(ligneGrade+nbColleurs-1,23)))
                ligneGrade+=nbColleurs
                if parMois:
                    for colleur, listeMois, nbMois in listeColleurs:
                        data[ligneColleur][3]=colleur
                        if nbMois>1:
                            LIST_STYLE.add('SPAN',(3,ligneColleur),(3,min(ligneColleur+nbMois-1,23)))
                        ligneColleur+=nbMois
                        for moi, decomptes in listeMois:
                            if moi < moisdebut:
                                LIST_STYLE.add('TEXTCOLOR',(4,ligneMois),(4+len(effectifs),ligneMois),(1,0,0))
                            data[ligneMois][4]=LISTE_MOIS_COURT[moi%12]
                            for i in range(len(effectifs)):
                                data[ligneMois][i+5]="{:.2f}h".format(decomptes[i]/60).replace('.',',')
                            ligneMois+=1
                            if ligneMois==24 and nbKolleurs>23: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
                                t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel,largeurcel]+[largeurcel]*len(effectifs),rowHeights=min((1+nbKolleurs),24)*[hauteurcel])
                                t.setStyle(LIST_STYLE)
                                w,h=t.wrapOn(pdf,0,0)
                                t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
                                pdf.finDePage()
                                # on redémarre sur une nouvelle page
                                pdf.debutDePage()
                                LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
                                                ,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
                                                ,('VALIGN',(0,0),(-1,-1),'MIDDLE')
                                                ,('ALIGN',(0,0),(-1,-1),'CENTRE')
                                                ,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
                                                ,('SIZE',(0,0),(-1,-1),8)])
                                nbKolleurs-=23
                                data = [["Matière","Établissement","Grade","Colleur","Mois"]+["{}è. ann.\n{}".format(annee,effectif) for annee,effectif in effectifs]]+[[""]*(5+len(effectifs)) for i in range(min(23,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
                                ligneEtab-=23
                                ligneGrade-=23
                                ligneMat-=23
                                ligneColleur-=23
                                ligneMois=1
                                if ligneMat>1:
                                    data[1][0]=matiere.title()
                                    if ligneMat>2:
                                        LIST_STYLE.add('SPAN',(0,1),(0,min(ligneMat-1,23)))
                                    if ligneEtab>1:
                                        data[1][1]=etablissement.title()
                                        if ligneEtab>2:
                                            LIST_STYLE.add('SPAN',(1,1),(1,min(ligneEtab-1,23)))
                                        if ligneGrade>1:
                                            data[1][2]=grade
                                            if ligneGrade>2:
                                                LIST_STYLE.add('SPAN',(2,1),(2,min(ligneGrade-1,23)))
                                            if ligneColleur>1:
                                                data[1][3]= colleur
                                                if ligneColleur>2:
                                                    LIST_STYLE.add('SPAN',(3,1),(3,min(ligneColleur-1,23)))
                else:
                    for colleur, decomptes in listeColleurs:
                        data[ligneColleur][3]=colleur
                        for i in range(len(effectifs)):
                            data[ligneColleur][i+4]="{:.2f}h".format(decomptes[i]/60).replace('.',',')
                        ligneColleur+=1
                        if ligneColleur==24 and nbKolleurs>23: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
                            t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel]+[largeurcel]*len(effectifs),rowHeights=min((1+nbKolleurs),24)*[hauteurcel])
                            t.setStyle(LIST_STYLE)
                            w,h=t.wrapOn(pdf,0,0)
                            t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
                            pdf.finDePage()
                            # on redémarre sur une nouvelle page
                            pdf.debutDePage()
                            LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
                                            ,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
                                            ,('VALIGN',(0,0),(-1,-1),'MIDDLE')
                                            ,('ALIGN',(0,0),(-1,-1),'CENTRE')
                                            ,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
                                            ,('SIZE',(0,0),(-1,-1),8)])
                            nbKolleurs-=23
                            data = [["Matière","Établissement","Grade","Colleur"]+["{}è. ann.\n{}".format(annee,effectif) for annee,effectif in effectifs]]+[[""]*(4+len(effectifs)) for i in range(min(23,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
                            ligneEtab-=23
                            ligneGrade-=23
                            ligneMat-=23
                            ligneColleur=1
                            if ligneMat>1:
                                data[1][0]=matiere.title()
                                if ligneMat>2:
                                    LIST_STYLE.add('SPAN',(0,1),(0,min(ligneMat-1,23)))
                                if ligneEtab>1:
                                    data[1][1]=etablissement.title()
                                    if ligneEtab>2:
                                        LIST_STYLE.add('SPAN',(1,1),(1,min(ligneEtab-1,23)))
                                    if ligneGrade>1:
                                        data[1][2]=grade
                                        if ligneGrade>2:
                                            LIST_STYLE.add('SPAN',(2,1),(2,min(ligneGrade-1,23)))
    t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel]+[largeurcel]*(parMois+len(effectifs)),rowHeights=min((1+nbKolleurs),24)*[hauteurcel])
    t.setStyle(LIST_STYLE)
    w,h=t.wrapOn(pdf,0,0)
    t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
    pdf.finDePage()
    pdf.save()
    fichier = pdf.buffer.getvalue()
    pdf.buffer.close()
    response.write(fichier)
    return response

@user_passes_test(is_secret, login_url='login_secret')
def ramassageCSVParClasse(request, id_ramassage, totalParmois, full = 0):
    """Renvoie le fichier CSV du ramassage par classe correspondant au ramassage dont l'id est id_ramassage
    si total vaut 1, les totaux par classe et matière sont calculés"""
    parmois, total = divmod(int(totalParmois),2)
    full = int(full)
    ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
    if Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).exists() and not full:# s'il existe un ramassage antérieur
        moisDebut = Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).aggregate(Max('moisFin'))['moisFin__max'] + timedelta(days=1)
    else:
        moisDebut = Semaine.objects.aggregate(Min('lundi'))['lundi__min']
    LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
    response = HttpResponse(content_type='text/csv')
    decomptes = Ramassage.objects.decompteRamassage(ramassage, csv = True, parClasse = True, parMois = bool(parmois), full = full)
    print(decomptes)
    LISTE_GRADES=["inconnu","certifié","bi-admissible","agrégé","chaire sup"]
    nomfichier="ramassageCSVParclasse{}_{}-{}_{}.csv".format(moisDebut.month,moisDebut.year,ramassage.moisFin.month,ramassage.moisFin.year)
    response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
    writer = csv.writer(response)
    entete = ["Classe","Matière","Établissement","Grade","Nom","Prénom","heures"]
    if parmois:
        entete[-1:-1] = ["mois"]
    writer.writerow(entete)
    if not total:
        for decompte in decomptes:
            heures = int(decompte[-1])
            writer.writerow([decompte[1], decompte[3], decompte[4].title(),
                            LISTE_GRADES[decompte[5]], decompte[6].upper(), decompte[7].title()] + ([LISTE_MOIS[decompte[9]%12+1]] if parmois else []) + ["{:.2f}".format(heures/60).replace('.',',')])
    elif len(decomptes) > 0:
        last_classe, last_classe_nom, last_matiere = decomptes[0][0], decomptes[0][1], decomptes[0][3]
        total_classe, total_matiere = 0, 0
        for decompte in decomptes:
            classe, matiere = decompte[0], decompte[3]
            heures = decompte[-1]
            if matiere != last_matiere or classe != last_classe: # si on change de matière ou de classe, on met le total matière
                writer.writerow([""]*(6+parmois))
                writer.writerow([last_classe_nom, "total {}".format(last_matiere.title())]+[""]*(4+parmois) +["{:.2f}".format(total_matiere/60).replace('.',',')])
                writer.writerow([""]*(6+parmois))
                total_classe += total_matiere
                total_matiere = 0
            if classe != last_classe: # si on change de classe, on met le total classe
                writer.writerow(["total {}".format(last_classe_nom)]+[""]*(5+parmois) +["{:.2f}".format(total_classe/60).replace('.',',')])
                writer.writerow([""]*(6+parmois))
                writer.writerow([""]*(6+parmois))
                total_classe = 0
            heures = int(decompte[-1])
            writer.writerow([decompte[1], decompte[3], decompte[4].title(),
                        LISTE_GRADES[decompte[5]], decompte[6].upper(), decompte[7].title()] + ([LISTE_MOIS[decompte[-2]%12+1]] if parmois else []) + ["{:.2f}".format(heures/60).replace('.',',')])
            total_matiere += heures
            last_classe, last_classe_nom, last_matiere = decompte[0], decompte[1], decompte[3]
        writer.writerow([""]*(6+parmois))
        writer.writerow([last_classe_nom, "total {}".format(last_matiere.title())]+[""]*(4+parmois) +["{:.2f}".format(total_matiere/60).replace('.',',')])
        writer.writerow([""]*(6+parmois))
        total_classe += total_matiere
        writer.writerow(["total {}".format(last_classe_nom)]+[""]*(5+parmois) +["{:.2f}".format(total_classe/60).replace('.',',')])
        writer.writerow([""]*(6+parmois))
        writer.writerow([""]*(6+parmois))
    return response


@user_passes_test(is_secret, login_url='login_secret')
def ramassagePdfParClasse(request,id_ramassage,totalParmois,full=0):
    """Renvoie le fichier PDF du ramassage par classe correspondant au ramassage dont l'id est id_ramassage
    si total vaut 1, les totaux par classe et matière sont calculés"""
    full = int(full)
    parmois, total = divmod(int(totalParmois),2)
    ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
    return mixteRamassagePdfParClasse(ramassage,total,parmois,full,colleur=False)

@user_passes_test(is_secret, login_url='login_secret')
def ramassagePdfParColleur(request,id_ramassage,parmois,full=0):
    """Renvoie le fichier PDF du ramassage par classe correspondant au ramassage dont l'id est id_ramassage
    si total vaut 1, les totaux par classe et matière sont calculés"""
    full = int(full)
    parmois = int(parmois) // 2
    ramassage=get_object_or_404(Ramassage,pk=id_ramassage)
    return mixteRamassagePdfParColleur(ramassage,parmois,full)

@user_passes_test(is_secret, login_url='accueil')
def groupe(request,id_classe):
    """Renvoie la vue de la page de gestion des groupes de la classe dont l'id est id_classe"""
    if not Config.objects.get_config().modif_secret_groupe:
        return HttpResponseForbidden("Accès non autorisé")
    classe=get_object_or_404(Classe,pk=id_classe)
    groupes = Groupe.objects.filter(classe=classe).prefetch_related('groupeeleve__user')
    return mixtegroupe(request,classe,groupes)

@user_passes_test(is_secret, login_url='accueil')
def groupeCreer(request,id_classe):
    """Renvoie la vue de la page de création d'un groupe de la classe dont l'id est id_classe"""
    if not Config.objects.get_config().modif_secret_groupe:
        return HttpResponseForbidden("Accès non autorisé")
    classe=get_object_or_404(Classe,pk=id_classe)
    return mixtegroupeCreer(request,classe)


@user_passes_test(is_secret, login_url='accueil')
def groupeSuppr(request,id_groupe):
    """Essaie de supprimer la groupe dont l'id est id_groupe, puis redirige vers la page de gestion des groupes"""
    if not Config.objects.get_config().modif_secret_groupe:
        return HttpResponseForbidden("Accès non autorisé")
    groupe=get_object_or_404(Groupe,pk=id_groupe)
    return mixtegroupesuppr(request,groupe)

@user_passes_test(is_secret, login_url='accueil')
def groupeModif(request,id_groupe):
    """Renvoie la vue de la page de modification du groupe dont l'id est id_groupe"""
    if not Config.objects.get_config().modif_secret_groupe:
        return HttpResponseForbidden("Accès non autorisé")
    groupe=get_object_or_404(Groupe,pk=id_groupe)
    return mixtegroupemodif(request,groupe)

@user_passes_test(is_secret, login_url='accueil')
def groupeSwap(request, id_classe):
    """change pour la classe dont l'id est id_classe la propriété de groupes différents ou égaux chaque semestres et renvoie la page des groupes"""
    if not Config.objects.get_config().modif_secret_groupe:
        return HttpResponseForbidden("Accès non autorisé")
    classe = get_object_or_404(Classe, pk=id_classe)
    return mixtegroupeSwap(request,classe)

@user_passes_test(is_secret, login_url='accueil')
def groupecsv(request, id_classe):
    """change pour la classe dont l'id est id_classe la propriété de groupes différents ou égaux chaque semestres et renvoie la page des groupes"""
    if not Config.objects.get_config().modif_secret_groupe:
        return HttpResponseForbidden("Accès non autorisé")
    classe = get_object_or_404(Classe, pk=id_classe)
    return mixtegroupecsv(request,classe)

@user_passes_test(is_secret_modif_ects, login_url='login_secret')
def ectsmatieres(request,id_classe):
    """Renvoie la vue de la page de gestion des matières ects de la classe"""
    classe = get_object_or_404(Classe,pk=id_classe)
    matieresECTS = MatiereECTS.objects.filter(classe=classe).prefetch_related('profs').order_by('nom','precision')
    newMatiere = MatiereECTS(classe=classe)
    form = MatiereECTSForm(request.POST or None,instance=newMatiere)
    form.fields['profs'].queryset=Colleur.objects.filter(classes=classe,colleurprof__classe=classe).order_by('user__last_name','user__first_name')
    if form.is_valid():
        form.save()
        return redirect('secret_ects_matieres',classe.pk)
    return render(request,'mixte/ectsmatieres.html',{'classe':classe,'matieresECTS':matieresECTS,'form':form})

@user_passes_test(is_secret_modif_ects, login_url='login_secret')
def ectsmatieremodif(request,id_matiere):
    """Renvoie la vue de la page de modification des matières ects de la classe"""
    matiere = get_object_or_404(MatiereECTS,pk=id_matiere)
    form = MatiereECTSForm(request.POST or None,instance=matiere)
    form.fields['profs'].queryset=Colleur.objects.filter(classes=matiere.classe,colleurprof__classe=matiere.classe).order_by('user__last_name','user__first_name')
    if form.is_valid():
        form.save()
        return redirect('secret_ects_matieres',matiere.classe.pk)
    return render(request,'mixte/ectsmatieremodif.html',{'matiere':matiere, 'classe':matiere.classe, 'form':form})

@user_passes_test(is_secret_modif_ects, login_url='login_secret')
def ectsmatieresuppr(request,id_matiere):
    """Supprime la matière ects dont l'id est id_matiere puis renvoie la page des matières ECTS"""
    matiere = get_object_or_404(MatiereECTS,pk=id_matiere)
    try:
        matiere.delete()
    except Exception:
        messages.error(request,"Impossible de l'effacer (des élèves y ont des notes)")
    return redirect('secret_ects_matieres',matiere.classe.pk)

@user_passes_test(is_secret_ects, login_url='login_secret')
def ectsnotes(request,id_classe):
    """Renvoie la vue de la page des notes ECTS ects de la classe"""
    classe = get_object_or_404(Classe,pk=id_classe)
    matieres = MatiereECTS.objects.filter(classe=classe).order_by('nom','precision')
    listNotes = list("ABCDEF")
    nomat, listeNotes = NoteECTS.objects.note(classe,matieres)
    nbsemestres=[]
    for matiere in matieres:
        nbsemestres.append(int(matiere.semestre1 is not None)+int(matiere.semestre2 is not None))
    return render(request,'secretariat/ectsnotes.html',{'eleves':Eleve.objects.filter(classe=classe),'nomat': nomat,'classe':classe, 'annee2':classe.annee == 2,'matieres':matieres,'listeNotes':listeNotes,'listNotes':listNotes,'nbsemestres':nbsemestres})

@user_passes_test(is_secret_ects, login_url='login_secret')
def ectscredits(request,id_classe,form=None):
    classe =get_object_or_404(Classe,pk=id_classe)
    eleves = Eleve.objects.filter(classe=classe).order_by('user__last_name','user__first_name')
    if not form:
        form=ECTSForm(classe,request.POST or None)
    credits,total = NoteECTS.objects.credits(classe)
    return render(request,'mixte/ectscredits.html',{'modif':is_secret_modif_ects(request.user),'classe':classe,'credits':credits,'form':form,'total':total,"nbeleves":eleves.order_by().count()})

@user_passes_test(is_secret_ects, login_url='login_secret')
def ficheectspdf(request,id_eleve):
    eleve = get_object_or_404(Eleve,pk=id_eleve)
    form = ECTSForm(eleve.classe, request.POST)
    if request.method=="POST":
        if form.is_valid():
            return creditsects(form,eleve,eleve.classe)
        else:
            return ectscredits(request,eleve.classe.pk,form)
    else:
        raise Http404

@user_passes_test(is_secret_ects, login_url='login_secret')
def attestationectspdf(request,id_eleve):
    eleve = get_object_or_404(Eleve,pk=id_eleve)
    form = ECTSForm(eleve.classe, request.POST)
    if request.method=="POST":
        if form.is_valid():
            return attestationects(form,eleve,eleve.classe)
        else:
            return ectscredits(request,eleve.classe.pk,form)
    else:
        raise Http404

@user_passes_test(is_secret_ects, login_url='login_secret')
def ficheectsclassepdf(request,id_classe):
    classe = get_object_or_404(Classe,pk=id_classe)
    form = ECTSForm(classe, request.POST)
    if request.method=="POST":
        if form.is_valid():
            return creditsects(form,None,classe)
        else:
            return ectscredits(request,classe.pk,form)
    else:
        raise Http404

@user_passes_test(is_secret_ects, login_url='login_secret')
def attestationectsclassepdf(request,id_classe):
    classe = get_object_or_404(Classe,pk=id_classe)
    form = ECTSForm(classe, request.POST)
    if request.method=="POST":
        if form.is_valid():
            return attestationects(form,None,classe)
        else:
            return ectscredits(request,classe.pk,form)
    else:
        raise Http404

@user_passes_test(is_secret_ects, login_url='login_secret')
def publipostageects(request,id_classe):
    classe = get_object_or_404(Classe,pk=id_classe)
    form = ECTSForm(classe, request.POST)
    if request.method=="POST":
        if form.is_valid():
            return publipostage(form,classe)
        else:
            return ectscredits(request,classe.pk,form)
    else:
        raise Http404
