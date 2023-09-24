#-*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from colleur.forms import ColleurConnexionForm, ProgrammeForm, SemaineForm, EleveForm, MatiereECTSForm, SelectEleveForm, NoteEleveForm, NoteGlobaleEleveForm, NoteEleveFormSet, NoteGlobaleEleveFormSet, ECTSForm, SelectEleveNoteForm, NoteElevesHeadForm, NoteElevesTailForm, NoteElevesFormset, DevoirForm, CopieForm, CopiesForm, TDForm, CoursForm, DocumentForm
from accueil.models import Config, Colleur, Matiere, Prof, Classe, Note, Eleve, Semaine, Programme, Groupe, Creneau, Colle, MatiereECTS, NoteECTS, NoteGlobaleECTS, Devoir, DevoirCorrige, DevoirRendu, Ramassage, Decompte, TD, Cours, Document
from mixte.mixte import mixtegroupe, mixtegroupesuppr, mixtegroupemodif, mixtecolloscope, mixtecolloscopemodif, mixtecreneaudupli, mixtecreneausuppr, mixteajaxcompat, mixteajaxcolloscope, mixteajaxcolloscopeeleve, mixteajaxmajcolleur, mixteajaxcolloscopeeffacer, mixteajaxcolloscopemulti, mixteajaxcolloscopemulticonfirm, mixteRamassagePdfParClasse, mixteCSV, mixtegroupeSwap, mixtegroupeCreer, mixtegroupecsv, mixteColloscopeImport
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Avg, Min, Max, StdDev, Sum, Count, F
from django.db.models.functions import Lower
from datetime import date
from django.http import Http404, HttpResponse, HttpResponseForbidden, FileResponse
from django.forms.formsets import formset_factory
from pdf.pdf import Pdf, creditsects, attestationects, trombinoscopePdf
import os
import csv
from zipfile import ZipFile
from ecolle.settings import MEDIA_ROOT, MEDIA_URL, IMAGEMAGICK
from io import BytesIO
PROF = 1

def is_colleur(user):
    """Renvoie True si l'utilisateur est authentifié et est un colleur, False sinon"""
    if user.is_authenticated and user.is_active:
        return bool(user.colleur)
    return False

def is_colleur_ects(user):
    """Renvoie True si l'utilisateur est authentifié et est un colleur et ECTS est activé, False sinon"""
    return is_colleur and Config.objects.get_config().ects

def is_colleur_modif_ects(user):
    """Renvoie True si l'utilisateur est authentifié et est un colleur et ECTS est activé et si les professeurs principaux ont le droit de modifier les matières ECTS, False sinon"""
    return is_colleur_ects(user) and Config.objects.get_config().ects_modif&PROF!=0

def is_prof(user,matiere,classe):
    """Renvoie True si l'utilisateur est un prof de la classe classe et dans la matière matière et eut modifier les matières/coefficients ECTS, False sinon"""
    if matiere==None:
        return Prof.objects.filter(classe=classe,colleur=user.colleur).exists()
    else:
        return Prof.objects.filter(classe=classe,matiere=matiere,colleur=user.colleur).exists()

def modifgroupe(colleur,classe):
    """Renvoie True si colleur a les drois en modification des groupes dans la classe classe, False sinon"""
    return Config.objects.get_config().modif_prof_groupe and  (classe.profprincipal==colleur or (colleur in Colleur.objects.filter(colleurprof__classe=classe,colleurprof__modifgroupe=True)))

def modifcolloscope(colleur,classe):
    """Renvoie True si colleur a les drois en modification du colloscope dans la classe classe, False sinon"""
    return Config.objects.get_config().modif_prof_col and (classe.profprincipal==colleur or (colleur in Colleur.objects.filter(colleurprof__classe=classe,colleurprof__modifcolloscope=True)))

def is_profprincipal(user,classe=False):
    """Renvoie True si user est professeur principal de la classe classe, False sinon"""
    if classe:
        return classe.profprincipal == user.colleur
    else:
        return bool(user.colleur.classeprofprincipal.all())

def connec(request):
    """Renvoie la vue de la page de connexion des colleurs. Si le colleur est déjà connecté, redirige vers la page d'accueil des colleurs"""
    if is_colleur(request.user):
        return redirect('action_colleur')
    error = False
    form = ColleurConnexionForm(request.POST or None)
    if form.is_valid():
        user = authenticate(username=form.cleaned_data['username'],password=form.cleaned_data['password'])
        if user is not None and user.is_active and user.colleur and user.colleur.matieres.all():
            login(request,user)
            request.session['matiere']=user.colleur.matieres.all()[0].pk
            return redirect('action_colleur')
        else:
            error = True
    return render(request,'colleur/home.html',{'form':form, 'error':error})

@user_passes_test(is_colleur, login_url='accueil')
def changemat(request,id_mat):
    """La matière courante du colleur devient la matière dont l'id est id_mat, puis redirige vers la page d'accueil des colleurs"""
    matiere=get_object_or_404(Matiere,pk=id_mat,colleur=request.user.colleur)
    request.session['matiere']=matiere.pk
    return redirect('action_colleur')

@user_passes_test(is_colleur, login_url='accueil')
def action(request):
    """Renvoie la vue de la page d'accueil des colleurs"""
    return render(request,"colleur/action.html")

@user_passes_test(is_colleur, login_url='accueil')
def note(request,id_classe):
    """Renvoie la vue de la page avec le récapitulaitf des notes données + des liens pour noter"""
    classe=get_object_or_404(Classe,pk=id_classe)
    colleur=request.user.colleur
    matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
    if classe not in colleur.classes.all() or matiere.pk not in classe.matierespk():
        raise Http404
    return render(request,"colleur/note.html",{'classe':classe, 'notes':Note.objects.listeNotes(colleur,classe,matiere)})

@user_passes_test(is_colleur, login_url='accueil')
def notation(request,id_classe,groupeeleve):
    """Renvoie la vue de sélection du ou des élèves à coller en fonction de groupe / élève et de l'éventuel semestre"""
    classe=get_object_or_404(Classe,pk=id_classe)
    groupeeleve = int(groupeeleve)
    colleur=request.user.colleur
    matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
    if classe not in colleur.classes.all() or matiere.pk not in classe.matierespk():
        raise Http404
    form = SelectEleveNoteForm(classe, groupeeleve, request.POST or None)
    if form.is_valid():
        return redirect('noteeleves_colleur', id_classe, "-".join([str(max(int(eleve),0)) for eleve in form.cleaned_data['eleve']]))
    return render(request,"colleur/notation.html",{'form':form,'classe':classe,'groupeeleve':groupeeleve})


@user_passes_test(is_colleur, login_url='accueil')
def noteEleves(request, id_classe, eleves_str, noteColle=None):
    matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=request.user.colleur)
    classe = get_object_or_404(Classe, pk=id_classe, matieres=matiere)
    if classe not in request.user.colleur.classes.all():
        raise Http404
    ids = [int(x) for x in eleves_str.split("-")]
    nbFictifs = ids.count(0)
    eleves = Eleve.objects.filter(pk__in = ids, classe = classe)
    total = eleves.count()+nbFictifs
    form = NoteElevesHeadForm(matiere, request.user.colleur, classe, request.POST or None, instance = noteColle)
    if total == 1 and noteColle is not None and noteColle.pk: # si on modifie une note
        NoteElevesformset = formset_factory(NoteElevesTailForm,extra=0,max_num=1,formset=NoteElevesFormset)
        formset = NoteElevesformset(form, list(eleves) + [None]*nbFictifs, request.POST or None, initial=[{'note':noteColle.note, 'commentaire':noteColle.commentaire}])
    elif noteColle is None: # si on ne note pas depuis l'agenda
        initial = dict()
        if 'semaine' in request.session:
            initial['semaine'] = request.session['semaine']
        if 'jour' in request.session:
            initial['jour'] = request.session['jour']
        if 'heure' in request.session:
            initial['heure'] = request.session['heure']
        form.initial = initial
        NoteElevesformset = formset_factory(NoteElevesTailForm,extra=total,max_num=3,formset=NoteElevesFormset)
        formset = NoteElevesformset(form, list(eleves) + [None]*nbFictifs, request.POST or None)
    else:
        NoteElevesformset = formset_factory(NoteElevesTailForm,extra=total,max_num=3,formset=NoteElevesFormset)
        formset = NoteElevesformset(form, list(eleves) + [None]*nbFictifs, request.POST or None)
    if request.method == 'POST':
        if formset.is_valid():
            formset.save()
            request.session['semaine']=form.cleaned_data['semaine'].pk
            request.session['jour']=form.cleaned_data['jour']
            request.session['heure']=form.cleaned_data['heure']
            return redirect('note_colleur',id_classe)
    return render(request,"colleur/noteEleves.html", {'form':form, 'formset':formset, 'classe':classe.nom, 'matiere':matiere})

@user_passes_test(is_colleur, login_url='accueil')
def noteModif(request,id_note):
    """Renvoie la vue de la page de modifcation de la note dont l'id est id_note"""
    note=get_object_or_404(Note,pk=id_note)
    colleur=request.user.colleur
    if note.colleur != colleur:
        messages.error(request,"Vous n'êtes pas le colleur de cette colle")
        return redirect('note_colleur')
    elif note.matiere.pk != request.session['matiere']:
        messages.error(request,"Ce n'est pas la bonne matière")
        return redirect('note_colleur')
    elif note.classe not in request.user.colleur.classes.all():
        messages.error(request,"Ce n'est pas la bonne classe")
        return redirect('note_colleur')
    return noteEleves(request, note.classe.pk, "0" if note.eleve is None else str(note.eleve.pk), note)

@user_passes_test(is_colleur, login_url='accueil')
def noteSuppr(request,id_note):
    """Essaie de supprimer la note dont l'id est id_note puis redirige vers la page de gestion des notes"""
    note=get_object_or_404(Note,pk=id_note)
    if note.colleur != request.user.colleur:
        messages.error(request,"Vous n'êtes pas le colleur de cette colle")
        return redirect('action_colleur')
    elif note.matiere.pk != request.session['matiere']:
        messages.error(request,"Ce n'est pas la bonne matière")
        return redirect('action_colleur')
    note.delete()
    return redirect('note_colleur', note.classe.pk)

@user_passes_test(is_colleur, login_url='accueil')
def trombinoscope(request,id_classe):
    return trombinoscopePdf(id_classe)

@user_passes_test(is_colleur, login_url='accueil')
def resultat(request,id_classe):
    """Renvoie la vue de la page des résultats de la classe dont l'id est id_classe"""
    semaines=Semaine.objects.all()
    try:
        semin=semaines[0]
    except Exception:
        raise Http404
    try:
        semax=semaines[semaines.count()-1]
    except Exception:
        raise Http404
    return redirect('resultat2_colleur',id_classe,semin.pk,semax.pk)

@user_passes_test(is_colleur, login_url='accueil')
def resultat2(request,id_classe,id_semin,id_semax):
    """Renvoie la vue de la page des résultats de la classe dont l'id est id_classe, entre les semaine dont l'id est id_semin et id_semax"""
    classe=get_object_or_404(Classe,pk=id_classe)
    semin=get_object_or_404(Semaine,pk=id_semin)
    semax=get_object_or_404(Semaine,pk=id_semax)
    if classe not in request.user.colleur.classes.all():
        raise Http404
    form=SemaineForm(request.POST or None,initial={'semin':semin,'semax':semax})
    if form.is_valid():
        return redirect('resultat2_colleur',id_classe,form.cleaned_data['semin'].pk,form.cleaned_data['semax'].pk)
    matiere = get_object_or_404(Matiere,pk=request.session['matiere'])
    generateur = Note.objects.classe2resultat(matiere,classe,semin,semax)
    nbSemaines = Note.objects.nbSemaines(matiere,classe,semin,semax)
    semaines = next(generateur)
    isprof = is_prof(request.user,matiere,classe)
    stat_colleurs = Note.objects.filter(classe=classe,matiere=matiere,semaine__lundi__range=(semin.lundi,semax.lundi)).exclude(note__gt=20).values('colleur__user__first_name','colleur__user__last_name').distinct().order_by('colleur__user__last_name','colleur__user__first_name').annotate(moy=Avg('note'),minimum=Min('note'),maximum=Max('note'),ecarttype=StdDev('note')) if isprof else False
    heures_colleurs = Note.objects.filter(classe=classe,matiere=matiere,semaine__lundi__range=(semin.lundi,semax.lundi)).values('colleur').order_by('colleur__user__last_name','colleur__user__first_name').annotate(nb=Count('pk')).annotate(heures = matiere.temps*F('nb')) if isprof else False
    stat_global = Note.objects.filter(classe=classe,matiere=matiere,semaine__lundi__range=(semin.lundi,semax.lundi)).exclude(note__gt=20).aggregate(moy=Avg('note'),minimum=Min('note'),maximum=Max('note'),ecarttype=StdDev('note')) if isprof else False
    heures_global = Note.objects.filter(classe=classe,matiere=matiere,semaine__lundi__range=(semin.lundi,semax.lundi)).aggregate(nb=Count('pk'))['nb']*matiere.temps if isprof else False
    return render(request,"colleur/resultat.html",{'largeur': 450+41*nbSemaines,'form':form,'classe':classe,'semaines':semaines,'matiere':matiere,'notes':generateur,'isprof':isprof,'semin':semin,'semax':semax,'stats':zip(stat_colleurs,heures_colleurs) if isprof else False, 'stat_global':stat_global, 'heures_global': heures_global })

@user_passes_test(is_colleur, login_url='accueil')
def resultatcsv(request,id_classe,id_semin,id_semax):
    """Renvoie le fichier csv des résultats de la classe dont l'id est id_classe, entre les semaine dont l'id est id_semin et id_semax"""
    classe=get_object_or_404(Classe,pk=id_classe)
    if classe not in request.user.colleur.classes.all():
        raise Http404
    semin=get_object_or_404(Semaine,pk=id_semin)
    semax=get_object_or_404(Semaine,pk=id_semax)
    matiere = get_object_or_404(Matiere,pk=request.session['matiere'])
    generateur = Note.objects.classe2resultat(matiere,classe,semin,semax)
    semaines = next(generateur)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="resultats_{}_{}_s{}-s{}.csv"'.format(classe.nom,matiere.nom,semin.numero,semax.numero)
    writer = csv.writer(response)
    writer.writerow(['Nom','Prénom','rang','moyenne']+['S{}'.format(semaine.numero) for semaine in semaines])
    notation = {i:str(i) for i in range(21)}
    notation[21]="n.n."
    notation[22]="abs"
    for note in generateur:
        writer.writerow([note['eleve'].user.last_name,note['eleve'].user.first_name,note['rang'],note['moyenne']]+["|".join([notation[note['note']] for note in value]) for value in note['semaine']])
    return response

@user_passes_test(is_colleur, login_url='accueil')
def programme(request,id_classe):
    """Renvoie la vue de la page de gestion des programmes de la classe dont l'id est id_classe"""
    classe=get_object_or_404(Classe,pk=id_classe)
    colleur=request.user.colleur
    matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
    if classe not in request.user.colleur.classes.all() or matiere.pk not in classe.matierespk():
        raise Http404
    programmes=Programme.objects.filter(classe=classe,matiere=matiere).prefetch_related('semaine').annotate(smax = Max('semaine__numero')).order_by('-smax')
    print(programmes)
    isprof=False
    if is_prof(request.user,matiere,classe):
        isprof=True
        programme=Programme(matiere=matiere,classe=classe)
        form = ProgrammeForm(request.POST or None,request.FILES or None,instance=programme)
        if form.is_valid():
            form.save()
            return redirect('programme_colleur',classe.pk)
    else:
        form=False
    return render(request,"colleur/programme.html",{'programmes':programmes,'classe':classe,'matiere':matiere,'form':form,'isprof':isprof,'jpeg':IMAGEMAGICK})

@user_passes_test(is_colleur, login_url='accueil')
def programmeSuppr(request,id_programme):
    """Essaie de supprimer le programme dont l'id est id_classe puis redirige vers la page de gestion des programmes"""
    programme=get_object_or_404(Programme,pk=id_programme)
    if not is_prof(request.user,programme.matiere,programme.classe):
        raise Http404
    programme.delete()
    return redirect('programme_colleur', programme.classe.pk)

@user_passes_test(is_colleur, login_url='accueil')
def programmeModif(request,id_programme):
    """Renvoie la vue de la page de modification du programme dont l'id est id_programme"""
    programme=get_object_or_404(Programme,pk=id_programme)
    if not is_prof(request.user,programme.matiere,programme.classe):
        raise Http404
    form=ProgrammeForm(request.POST or None,request.FILES or None, instance=programme)
    oldfile=os.path.join(MEDIA_ROOT,programme.fichier.name) if programme.fichier else False
    if form.is_valid():
        if request.FILES and oldfile:
            if os.path.isfile(oldfile):
                os.remove(oldfile)
            nomimage=oldfile.replace('programme','image').replace('pdf','jpg')
            if os.path.isfile(nomimage):
                os.remove(nomimage)
        form.save()
        return redirect('programme_colleur', programme.classe.pk)
    return render(request,"colleur/programmeModif.html",{'programme':programme,'form':form})

@user_passes_test(is_colleur, login_url='accueil')
def groupe(request,id_classe):
    """Renvoie la vue de la page de gestion des groupes de la classe dont l'id est id_classe"""
    classe=get_object_or_404(Classe,pk=id_classe)
    if not modifgroupe(request.user.colleur,classe):
        return HttpResponseForbidden("Accès non autorisé")
    groupes = Groupe.objects.filter(classe=classe).prefetch_related('groupeeleve__user')
    return mixtegroupe(request,classe,groupes)

@user_passes_test(is_colleur, login_url='accueil')
def groupeCreer(request,id_classe):
    """Renvoie la vue de la page de création d'un groupe de la classe dont l'id est id_classe"""
    classe=get_object_or_404(Classe,pk=id_classe)
    if not modifgroupe(request.user.colleur,classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixtegroupeCreer(request,classe)

@user_passes_test(is_colleur, login_url='accueil')
def groupeSuppr(request,id_groupe):
    """Essaie de supprimer la groupe dont l'id est id_groupe, puis redirige vers la page de gestion des groupes"""
    groupe=get_object_or_404(Groupe,pk=id_groupe)
    if not modifgroupe(request.user.colleur,groupe.classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixtegroupesuppr(request,groupe)

@user_passes_test(is_colleur, login_url='accueil')
def groupeModif(request,id_groupe):
    """Renvoie la vue de la page de modification du groupe dont l'id est id_groupe"""
    groupe=get_object_or_404(Groupe,pk=id_groupe)
    if not modifgroupe(request.user.colleur,groupe.classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixtegroupemodif(request,groupe)

@user_passes_test(is_colleur, login_url='accueil')
def groupeSwap(request, id_classe):
    """change pour la classe dont l'id est id_classe la propriété de groupes différents ou égaux chaque semestres et renvoie la page des groupes"""
    classe = get_object_or_404(Classe, pk=id_classe)
    if not modifgroupe(request.user.colleur,classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixtegroupeSwap(request,classe)

@user_passes_test(is_colleur, login_url='accueil')
def groupecsv(request, id_classe):
    """change pour la classe dont l'id est id_classe la propriété de groupes différents ou égaux chaque semestres et renvoie la page des groupes"""
    classe = get_object_or_404(Classe, pk=id_classe)
    if not modifgroupe(request.user.colleur,classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixtegroupecsv(request,classe)
    
@user_passes_test(is_colleur, login_url='accueil')
def colloscope(request,transpose,id_classe):
    """Renvoie la vue de la page de gestion du colloscope de la classe dont l'id est id_classe"""
    semaines=list(Semaine.objects.all())
    try:
        semin,semax=semaines[0],semaines[-1]
    except Exception:
        raise Http404
    if transpose == "0" and "transpose" in request.session and request.session["transpose"] is True:
        transpose = "1" 
    return colloscope2(request,transpose,id_classe,semin.pk,semax.pk)


@user_passes_test(is_colleur, login_url='accueil')
def colloscope2(request,transpose,id_classe,id_semin,id_semax):
    """Renvoie la vue de la page de gestion du colloscope de la classe dont l'id est id_classe,
    dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
    classe=get_object_or_404(Classe,pk=id_classe)
    semin=get_object_or_404(Semaine,pk=id_semin)
    semax=get_object_or_404(Semaine,pk=id_semax)
    isprof = modifcolloscope(request.user.colleur,classe)
    if classe not in request.user.colleur.classes.all():
        raise Http404
    return mixtecolloscope(request,classe,semin,semax,isprof,int(transpose))

@user_passes_test(is_colleur, login_url='accueil')
def colloscopeModif(request,id_classe,id_semin,id_semax,creneaumodif=None):
    """Renvoie la vue de la page de modification du colloscope de la classe dont l'id est id_classe,
    dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
    classe=get_object_or_404(Classe,pk=id_classe)
    semin=get_object_or_404(Semaine,pk=id_semin)
    semax=get_object_or_404(Semaine,pk=id_semax)
    if not modifcolloscope(request.user.colleur,classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixtecolloscopemodif(request,classe,semin,semax,creneaumodif)

@user_passes_test(is_colleur, login_url='accueil')
def colloscopeImport(request,id_classe):
    """Renvoie la vue de la page d'import' du colloscope de la classe dont l'id est id_classe"""
    classe=get_object_or_404(Classe,pk=id_classe)
    if not modifcolloscope(request.user.colleur,classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixteColloscopeImport(request,classe)
    
@user_passes_test(is_colleur, login_url='accueil')
def creneauSuppr(request,id_creneau,id_semin,id_semax):
    """Essaie de supprimer le créneau dont l'id est id_creneau puis redirige vers la page de modification du colloscope
    dont les semaines sont entre la semaine d'id id_semin et celle d'id id_semax"""
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    if not modifcolloscope(request.user.colleur,creneau.classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixtecreneausuppr(request,creneau,id_semin,id_semax)

@user_passes_test(is_colleur, login_url='accueil')
def creneauModif(request,id_creneau,id_semin,id_semax):
    """Renvoie la vue de la page de modification du creneau dont l'id est id_creneau"""
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    if not modifcolloscope(request.user.colleur,creneau.classe):
        return HttpResponseForbidden("Accès non autorisé")
    return colloscopeModif(request,creneau.classe.pk,id_semin,id_semax,creneaumodif=creneau)

@user_passes_test(is_colleur, login_url='accueil')
def creneauDupli(request,id_creneau,id_semin,id_semax):
    """Renvoie la vue de la page de duplication du creneau dont l'id est id_creneau"""
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    if not modifcolloscope(request.user.colleur,creneau.classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixtecreneaudupli(request.user,creneau,id_semin,id_semax)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcompat(request,id_classe):
    """Renvoie une chaîne de caractères récapitulant les incompatibilités du colloscope de la classe dont l'id est id_classe"""
    classe=get_object_or_404(Classe,pk=id_classe)
    return mixteajaxcompat(classe)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxmajcolleur(request, id_matiere, id_classe):
    """Renvoie la liste des colleurs de la classe dont l'id est id_classe et de la matière dont l'id est id_matiere, au format json"""
    classe=get_object_or_404(Classe,pk=id_classe)
    matiere=get_object_or_404(Matiere,pk=id_matiere)
    if not modifcolloscope(request.user.colleur,classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixteajaxmajcolleur(matiere,classe)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcolloscope(request, id_matiere, id_colleur, id_groupe, numero_semaine, id_creneau):
    """Ajoute la colle propre au quintuplet (matière,colleur,groupe,semaine,créneau) et renvoie le username du colleur
    en effaçant au préalable toute colle déjà existante sur ce couple créneau/semaine"""
    matiere=get_object_or_404(Matiere,pk=id_matiere)
    colleur=get_object_or_404(Colleur,pk=id_colleur)
    groupe=get_object_or_404(Groupe,pk=id_groupe)
    semaine=get_object_or_404(Semaine,numero=numero_semaine)
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    if not modifcolloscope(request.user.colleur,creneau.classe) or matiere not in colleur.matieres.all() or matiere not in creneau.classe.matieres.all():
        return HttpResponseForbidden("Accès non autorisé")
    return mixteajaxcolloscope(matiere,colleur,groupe,semaine,creneau)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcolloscopeeleve(request, id_matiere, id_colleur, id_eleve, numero_semaine, id_creneau, login):
    """Ajoute la colle propre au quintuplet (matière,colleur,eleve,semaine,créneau) et renvoie le login du colleur
    en effaçant au préalable toute colle déjà existante sur ce couple créneau/semaine"""
    matiere=get_object_or_404(Matiere,pk=id_matiere)
    colleur=get_object_or_404(Colleur,pk=id_colleur)
    semaine=get_object_or_404(Semaine,numero=numero_semaine)
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    if not modifcolloscope(request.user.colleur,creneau.classe) or matiere not in colleur.matieres.all() or matiere not in creneau.classe.matieres.all():
        return HttpResponseForbidden("Accès non autorisé")
    return mixteajaxcolloscopeeleve(matiere,colleur, id_eleve,semaine,creneau,login)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcolloscopeeffacer(request, numero_semaine, id_creneau):
    """Efface la colle sur le créneau dont l'id est id_creneau et la semaine dont le numéro est numero_semaine
    puis renvoie la chaine de caractères "efface" """
    semaine=get_object_or_404(Semaine,numero=numero_semaine)
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    if not modifcolloscope(request.user.colleur,creneau.classe):
        return HttpResponseForbidden("Accès non autorisé")
    return mixteajaxcolloscopeeffacer(semaine,creneau)

@user_passes_test(is_colleur, login_url='accueil')
def ajaxcolloscopemulti(request, id_matiere, id_colleur, id_groupe, id_eleve, numero_semaine, id_creneau, duree, frequence, permutation):
    """Compte le nombre de colles présente sur les couples créneau/semaine sur le créneau dont l'id est id_creneau
    et les semaines dont le numéro est compris entre celui de la semaine d'id id_semaine et ce dernier + duree
    et dont le numéro est congru à celui de la semaine d'id id_semaine modulo frequence
    S'il n'y en a aucune, ajoute les colles sur les couples créneau/semaine précédents, avec le colleur dont l'id est id_colleur
    le groupe démarre au groupe dont l'id est id_groupe puis va de permutation en permutation, et la matière dont l'id est id_matière"""
    if id_matiere != "-1": # si on n'efface pas des colles
        matiere=get_object_or_404(Matiere,pk=id_matiere)
        colleur=get_object_or_404(Colleur,pk=id_colleur)
    else:
        matiere = -1
        colleur = 0
    semaine=get_object_or_404(Semaine,numero=numero_semaine)
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    if not modifcolloscope(request.user.colleur,creneau.classe) or matiere !=-1 and (matiere not in colleur.matieres.all() or matiere not in creneau.classe.matieres.all()):
        return HttpResponseForbidden("Accès non autorisé")
    return mixteajaxcolloscopemulti(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation)
    
@user_passes_test(is_colleur, login_url='accueil')
def ajaxcolloscopemulticonfirm(request, id_matiere, id_colleur, id_groupe, id_eleve, numero_semaine, id_creneau, duree, frequence, permutation):
    """ajoute les colles sur les couples créneau/semaine sur le créneau dont l'id est id_creneau
    et les semaines dont le numéro est compris entre celui de la semaine d'id id_semaine et ce dernier + duree
    et dont le numéro est congru à celui de la semaine d'id id_semaine modulo frequence, avec le colleur dont l'id est id_colleur
    le groupe démarre au groupe dont l'id est id_groupe puis va de permutation en permutation, et la matière dont l'id est id_matière"""
    if id_matiere != "-1": # si on n'efface pas des colles
        matiere=get_object_or_404(Matiere,pk=id_matiere)
        colleur=get_object_or_404(Colleur,pk=id_colleur)
    else:
        matiere = -1
        colleur = 0
    semaine=get_object_or_404(Semaine,numero=numero_semaine)
    creneau=get_object_or_404(Creneau,pk=id_creneau)
    if not modifcolloscope(request.user.colleur,creneau.classe) or matiere != -1 and (matiere not in colleur.matieres.all() or matiere not in creneau.classe.matieres.all()):
        return HttpResponseForbidden("Accès non autorisé")
    return mixteajaxcolloscopemulticonfirm(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation)

@user_passes_test(is_colleur, login_url='accueil')
def agenda(request):
    """Renvoie la vue de la page de l'agenda"""
    jour=date.today()
    colles = Colle.objects.agenda(request.user.colleur)
    return render(request,"colleur/agenda.html",{'colles':colles,'media_url':MEDIA_URL,'jour':jour})

@user_passes_test(is_colleur, login_url='accueil')
def colleNote(request,id_colles):
    """Récupère la colle dont l'id est id_colle puis redirige vers la page de notation des groupes sur la colle concernée"""
    colles=list(Colle.objects.filter(pk__in=id_colles.split(","),colleur=request.user.colleur,matiere__in=request.user.colleur.matieres.all())) # on récupère la colle ou les colles
    if not colles:
        raise Http404
    groupes = [colle.groupe for colle in colles]
    colle = colles[0]
    request.session['matiere']=colles[0].matiere.pk # on met à jour la matière courante
    semestre2 = Config.objects.get_config().semestre2
    semaine = colle.semaine.numero
    classe = colle.creneau.classe
    if classe.semestres and semaine >= semestre2:
        eleves = Eleve.objects.filter(groupe2__in = groupes)
    else:
        eleves = Eleve.objects.filter(groupe__in = groupes)
    if classe.semestres and semaine >= semestre2 and colle.matiere in (classe.option1,classe.option2):
        eleves = eleves.filter(option = colle.matiere)
    elif colles[0].matiere.lv == 1:
        eleves = eleves.filter(lv1 = colle.matiere)
    elif colles[0].matiere.lv == 2:
        eleves = eleves.filter(lv2 = colle.matiere)
    eleves_str = "-".join([str(x.pk) for x in eleves] + ["0"]*(3-eleves.count()))
    note = Note(semaine = colle.semaine, jour = colle.creneau.jour, heure = colle.creneau.heure)
    return noteEleves(request,classe.pk,eleves_str,note)

@user_passes_test(is_colleur, login_url='accueil')
def colleNoteEleve(request,id_colle):
    """Récupère la colle dont l'id est id_colle puis redirige vers la page de notation de l'élève sur la colle concernée"""
    colle=get_object_or_404(Colle,pk=id_colle,colleur=request.user.colleur,matiere__in=request.user.colleur.matieres.all())
    request.session['matiere']=colle.matiere.pk # on met à jour la matière courante
    note = Note(semaine = colle.semaine, jour = colle.creneau.jour, heure = colle.creneau.heure)
    return noteEleves(request, colle.creneau.classe.pk, "0" if not colle.eleve else str(colle.eleve.pk), note)
    
@user_passes_test(is_colleur, login_url='accueil')
def decompte(request):
    """Renvoie la vue de la page du décompte des colles"""
    colleur=request.user.colleur
    matieres=colleur.matieres.annotate(inom = Lower('nom')).order_by('inom').values_list('inom',flat=True).distinct()
    classes=colleur.classes.all()
    listematieres=[]
    lastpkramassage = Ramassage.objects.aggregate(pkmax = Max('pk'))['pkmax']
    if lastpkramassage is None:
        lastpkramassage = 0
    for matiere in matieres:
        listemois = Note.objects.filter(colleur=colleur,matiere__nom__iexact=matiere).dates('date_colle','month').distinct()
        listeclasses=[]
        for classe in classes:
            nbcolles=[]
            for mois in listemois:
                nbcolles.append((Note.objects.filter(colleur=colleur,matiere__nom__iexact=matiere,classe=classe,date_colle__month=mois.month,date_colle__year=mois.year).aggregate(temps=Sum('matiere__temps'))['temps'],
                Decompte.objects.filter(ramassage = lastpkramassage, colleur = colleur, matiere__nom__iexact=matiere, classe = classe, mois = mois.year*12 + mois.month - 1).aggregate(temps=Sum('temps'))['temps']))
            total=Note.objects.filter(colleur=colleur,matiere__nom__iexact=matiere,classe=classe).aggregate(temps=Sum('matiere__temps'))
            totalramassage = Decompte.objects.filter(ramassage = lastpkramassage, colleur = colleur, matiere__nom__iexact = matiere, classe = classe).aggregate(temps=Sum('temps'))
            listeclasses.append((classe,nbcolles,total,totalramassage))
        listematieres.append((matiere,listeclasses,listemois))
        listematieres.sort(key=lambda x:x[0])
    ramassages = Ramassage.objects.values('pk','moisFin')
    return render(request,"colleur/decompte.html",{'listematieres':listematieres, 'ramassages':ramassages})

@user_passes_test(is_colleur, login_url='accueil')
def ramassage(request,id_ramassage):
    ramassage = get_object_or_404(Ramassage, pk=id_ramassage)
    return mixteRamassagePdfParClasse(ramassage, False, True, False, colleur = request.user.colleur)

@user_passes_test(is_colleur, login_url='accueil')
def colloscopePdf(request,id_classe,id_semin,id_semax):
    """Renvoie le fichier PDF du colloscope de la classe dont l'id est id_classe, entre les semaines d'id id_semin et id_semax"""
    classe=get_object_or_404(Classe,pk=id_classe)
    semin=get_object_or_404(Semaine,pk=id_semin)
    semax=get_object_or_404(Semaine,pk=id_semax)
    if classe not in request.user.colleur.classes.all():
        raise Http404
    return Pdf(classe,semin,semax)

@user_passes_test(is_colleur, login_url='accueil')
def colloscopeCsv(request,id_classe,id_semin,id_semax):
    """Renvoie le fichier CSV du colloscope de la classe dont l'id est id_classe, entre les semaines d'id id_semin et id_semax"""
    classe=get_object_or_404(Classe,pk=id_classe)
    semin=get_object_or_404(Semaine,pk=id_semin)
    semax=get_object_or_404(Semaine,pk=id_semax)
    if classe not in request.user.colleur.classes.all():
        raise Http404
    return mixteCSV(request,classe,semin,semax)

@user_passes_test(is_colleur, login_url='accueil')
def eleves(request,id_classe):
    """Renvoie la vue de la page de gestion des élèves"""
    classe = get_object_or_404(Classe,pk=id_classe)
    if not is_profprincipal(request.user,classe):
        return HttpResponseForbidden("Accès non autorisé")
    try:
        eleve = Eleve.objects.get(pk=request.session['eleve'])
    except Exception:
        eleve = None
    try:
        semin = Semaine.objects.get(pk=request.session['semin'])
        semax = Semaine.objects.get(pk=request.session['semax'])
    except Exception:
        try:
            semaines = list(Semaine.objects.all())
            semin,semax = semaines[0],semaines[-1]
        except Exception:
            semin=semax=None
    if request.method == 'POST':
         if 'semaines' in request.POST:
            form2 = SemaineForm(request.POST)
            form = EleveForm(classe, initial = {"eleve":eleve})
            if form2.is_valid():
                request.session['semin'] = form2.cleaned_data['semin'].pk
                request.session['semax'] = form2.cleaned_data['semax'].pk
                return redirect('eleves_colleur',classe.pk)
         elif 'eleveselect' in request.POST:
            form2 = SemaineForm(initial = {'semin':semin,'semax':semax})
            form = EleveForm(classe,request.POST) 
            if form.is_valid():
                request.session['eleve'] = form.cleaned_data['eleve'].pk
                return redirect('eleves_colleur',classe.pk)
    else:
        form = EleveForm(classe, initial = {"eleve":eleve})
        form2 = SemaineForm(initial = {'semin':semin,'semax':semax})
    if eleve and semin and semax:
        semaines = Note.objects.filter(eleve=eleve,semaine__lundi__range=(semin.lundi,semax.lundi)).values('semaine','semaine__numero').distinct().order_by('semaine__lundi')
        matieres = classe.matieres.all().order_by('nom')
        matierenote=[]
        for matiere in matieres:
            moyenne = Note.objects.filter(eleve=eleve,semaine__lundi__range=(semin.lundi,semax.lundi),matiere=matiere).exclude(note__gt=20).aggregate(moy=Avg('note'))
            if moyenne['moy']:
                rang=Note.objects.exclude(note__gt=20).filter(classe=classe,eleve__isnull=False,matiere=matiere,semaine__lundi__range=(semin.lundi,semax.lundi)).values('eleve').annotate(Avg('note')).filter(note__avg__gt=moyenne['moy']+0.001).count()+1
            else:
                rang=""
            notes = []
            for semaine in semaines:
                note = Note.objects.filter(eleve=eleve,matiere=matiere,semaine__pk=semaine['semaine']).select_related('colleur__user')
                notes.append(note)
            matierenote.append((matiere,moyenne,rang,notes))
    else:
        semaines = matierenote = None
    return render(request,'colleur/eleves.html',{'eleve':eleve,'semin':semin,'semax':semax,'form':form,'form2':form2,'matierenote':matierenote,'semaines':semaines})

@user_passes_test(is_colleur_modif_ects, login_url='accueil')
def ectsmatieres(request,id_classe):
    """Renvoie la vue de la page de gestion des matières ects de la classe"""
    classe = get_object_or_404(Classe,pk=id_classe)
    if not is_profprincipal(request.user,classe):
        return redirect('ects_notes',classe.pk)
    matieresECTS = MatiereECTS.objects.filter(classe=classe).prefetch_related('profs').order_by('nom','precision')
    newMatiere = MatiereECTS(classe=classe)
    form = MatiereECTSForm(request.POST or None,instance=newMatiere)
    form.fields['profs'].queryset=Colleur.objects.filter(classes=classe,colleurprof__classe=classe).order_by('user__last_name','user__first_name')
    if form.is_valid():
        form.save()
        return redirect('ects_matieres',classe.pk)
    return render(request,'mixte/ectsmatieres.html',{'classe':classe,'matieresECTS':matieresECTS,'form':form})

@user_passes_test(is_colleur_modif_ects, login_url='accueil')
def ectsmatieremodif(request,id_matiere):
    """Renvoie la vue de la page de modification des matières ects de la classe"""
    matiere = get_object_or_404(MatiereECTS,pk=id_matiere)
    if not is_profprincipal(request.user,matiere.classe):
        return HttpResponseForbidden("Accès non autorisé")
    form = MatiereECTSForm(request.POST or None,instance=matiere)
    form.fields['profs'].queryset=Colleur.objects.filter(classes=matiere.classe,colleurprof__classe=matiere.classe).order_by('user__last_name','user__first_name')
    if form.is_valid():
        form.save()
        return redirect('ects_matieres',matiere.classe.pk)
    return render(request,'mixte/ectsmatieremodif.html',{'matiere':matiere,'form':form})

@user_passes_test(is_colleur_modif_ects, login_url='accueil')
def ectsmatieresuppr(request,id_matiere):
    """Supprime la matière ects dont l'id est id_matiere puis renvoie la page des matières ECTS"""
    matiere = get_object_or_404(MatiereECTS,pk=id_matiere)
    if not is_profprincipal(request.user,matiere.classe):
        return HttpResponseForbidden("Accès non autorisé")
    if not is_profprincipal(request.user,matiere.classe):
        return HttpResponseForbidden("Accès non autorisé")
    try:
        matiere.delete()
    except Exception:
        messages.error(request,"Impossible de l'effacer (des élèves y ont des notes)")
    return redirect('ects_matieres',matiere.classe.pk)

@user_passes_test(is_colleur_ects, login_url='accueil')
def ectsnotes(request,id_classe):
    """Renvoie la vue de la page de gestion des matières ects de la classe"""
    classe = get_object_or_404(Classe,pk=id_classe)
    pp = is_profprincipal(request.user,classe)
    matieres = MatiereECTS.objects.filter(classe=classe,profs=request.user.colleur).order_by('nom','precision')
    if not matieres.exists() and not pp:
        return HttpResponseForbidden("Vous n'êtes pas habilité à attribuer des crédits ECTS aux élèves de cette classe")
    listNotes = list("ABCDEF")
    nomat, listeNotes = NoteECTS.objects.note(classe,matieres)
    form = SelectEleveForm(classe,request.POST or None)
    if form.is_valid():
        if 'global' in request.POST:
            return redirect('ects_noteglobale_modif',classe.pk,classe.annee,"-".join([str(eleve.pk) for eleve in form.cleaned_data['eleve']]))
        if 'global2' in request.POST:
            return redirect('ects_noteglobale_modif',classe.pk,1,"-".join([str(eleve.pk) for eleve in form.cleaned_data['eleve']]))
        for matiere in matieres:
            if str(matiere.pk) in request.POST:
                return redirect('ects_notes_modif',matiere.pk,"-".join([str(eleve.pk) for eleve in form.cleaned_data['eleve']]))
    nbsemestres=[]
    for matiere in matieres:
        nbsemestres.append(int(matiere.semestre1 is not None)+int(matiere.semestre2 is not None))
    return render(request,'colleur/ectsnotes.html',{'modif':is_colleur_modif_ects(request.user),'annee2': classe.annee == 2, 'nomat': nomat,'pp':pp,'classe':classe,'matieres':matieres,'listeNotes':listeNotes,'listNotes':listNotes,'form':form,'nbsemestres':nbsemestres})

@user_passes_test(is_colleur_ects, login_url='accueil')
def ectsnotesmodif(request,id_matiere,chaine_eleves):
    """Renvoie la vue de la page de modification des notes ECTS des élèves sélectionnés, dont l'id fait partie de chaine_eleves, dans la matiere dont l"id est id_matiere"""
    matiere = get_object_or_404(MatiereECTS,pk=id_matiere,profs=request.user.colleur)
    listeEleves = Eleve.objects.filter(pk__in=[int(i) for i in chaine_eleves.split("-")],classe=matiere.classe).order_by('user__last_name','user__first_name').select_related('user')
    NoteEleveformset = formset_factory(NoteEleveForm,extra=0,max_num=listeEleves.count(),formset=NoteEleveFormSet)
    if request.method == 'POST':
        formset = NoteEleveformset(listeEleves,matiere,request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('ects_notes',matiere.classe.pk)
    else:
        initial = NoteECTS.objects.noteEleves(matiere,listeEleves)
        formset = NoteEleveformset(listeEleves,matiere,initial=initial)
    nbsemestres = 1+int(matiere.semestre1 is not None)+int(matiere.semestre2 is not None)
    return render(request,'colleur/ectsnotesmodif.html',{'modif':is_colleur_modif_ects(request.user),'formset':formset,'matiere':matiere,'nbsemestres':nbsemestres})

@user_passes_test(is_colleur_ects, login_url='accueil')
def ectsnoteglobalemodif(request,id_classe,annee,chaine_eleves):
    """Renvoie la vue de la page de modification de la note globale ECTS des élèves sélectionnés, dont l'id fait partie de chaine_eleves, dans la classe indiquée et pour l'année indiquée"""
    classe = get_object_or_404(Classe,pk=id_classe)
    if not is_profprincipal(request.user,classe):
        return HttpResponseForbidden("Accès non autorisé")
    listeEleves = Eleve.objects.filter(pk__in=[int(i) for i in chaine_eleves.split("-")],classe=classe).order_by('user__last_name','user__first_name').select_related('user')
    NoteGlobaleEleveformset = formset_factory(NoteGlobaleEleveForm,extra=0,max_num=listeEleves.count(),formset=NoteGlobaleEleveFormSet)
    if request.method == 'POST':
        formset = NoteGlobaleEleveformset(annee,listeEleves,request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('ects_notes',classe.pk)
    else:
        initial = NoteGlobaleECTS.objects.noteEleves(classe,annee,listeEleves)
        formset = NoteGlobaleEleveformset(annee,listeEleves,initial=initial)
    return render(request,'colleur/ectsnoteglobalemodif.html',{'modif':is_colleur_modif_ects(request.user),'formset':formset,"annee": int(annee), 'classe': classe})

@user_passes_test(is_colleur_modif_ects, login_url='accueil')
def ectscredits(request,id_classe,form=None):
    classe =get_object_or_404(Classe,pk=id_classe)
    if not is_profprincipal(request.user,classe):
        return HttpResponseForbidden("Accès non autorisé")
    eleves = Eleve.objects.filter(classe=classe).order_by('user__last_name','user__first_name')
    if form is None:
        form=ECTSForm(classe,request.POST or None)
    credits,total = NoteECTS.objects.credits(classe)        
    return render(request,'mixte/ectscredits.html',{'classe':classe,'credits':credits,'form':form,'total':total,"nbeleves":eleves.order_by().count()})

@user_passes_test(is_colleur_modif_ects, login_url='accueil')
def ficheectspdf(request,id_eleve):
    eleve = get_object_or_404(Eleve,pk=id_eleve)
    if not is_profprincipal(request.user,eleve.classe):
        return HttpResponseForbidden("Accès non autorisé")
    form = ECTSForm(eleve.classe, request.POST)
    if request.method=="POST":
        if form.is_valid():
            return creditsects(form,eleve,eleve.classe)
        else:
            return ectscredits(request,eleve.classe.pk,form)
    else:
        raise Http404

@user_passes_test(is_colleur_modif_ects, login_url='accueil')
def attestationectspdf(request,id_eleve):
    eleve = get_object_or_404(Eleve,pk=id_eleve)
    if not is_profprincipal(request.user,eleve.classe):
        return HttpResponseForbidden("Accès non autorisé")
    form = ECTSForm(eleve.classe, request.POST)
    if request.method=="POST":
        if form.is_valid():
            return attestationects(form,eleve,eleve.classe)
        else:
            return ectscredits(request,eleve.classe.pk,form)
    else:
        raise Http404

@user_passes_test(is_colleur_ects, login_url='accueil')
def ficheectsclassepdf(request,id_classe):
    classe = get_object_or_404(Classe,pk=id_classe)
    if not is_profprincipal(request.user,classe):
        return HttpResponseForbidden("Accès non autorisé")
    form = ECTSForm(classe, request.POST)
    if request.method=="POST":
        if form.is_valid():
            return creditsects(form,None,classe)
        else:
            return ectscredits(request,classe.pk,form)
    else:
        raise Http404

@user_passes_test(is_colleur_modif_ects, login_url='accueil')
def attestationectsclassepdf(request,id_classe):
    classe = get_object_or_404(Classe,pk=id_classe)
    if not is_profprincipal(request.user,classe):
        return HttpResponseForbidden("Accès non autorisé")
    form = ECTSForm(classe, request.POST)
    if request.method=="POST":
        if form.is_valid():
            return attestationects(form,None,classe)
        else:
            return ectscredits(request,classe.pk,form)
    else:
        raise 

@user_passes_test(is_colleur, login_url='accueil')
def devoirs(request,id_classe):
    """renvoie la page des devoirs de la classe dont l'id est id_classe, dans la matière courante du professeur"""
    classe=get_object_or_404(Classe,pk=id_classe)
    colleur=request.user.colleur
    matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
    if not is_prof(request.user,matiere,classe):
        raise Http404
    devoirs=Devoir.objects.filter(classe=classe,matiere=matiere).order_by('-a_rendre_jour','-a_rendre_heure')
    devoir = Devoir(classe=classe,matiere=matiere)
    form = DevoirForm(matiere, classe, request.POST or None,request.FILES or None,instance=devoir)
    if form.is_valid():
        form.save()
        return redirect('colleur_devoirs',classe.pk)
    return render(request,"colleur/devoirs.html", {'matiere':matiere , 'form':form, 'devoirs':devoirs})

@user_passes_test(is_colleur, login_url='accueil')
def devoir(request, id_devoir):
    """Renvoie la vue de la page du devoir dont l'id est id_devoir, pour consuler/rendre les copies"""
    devoir=get_object_or_404(Devoir,pk=id_devoir)
    if not is_prof(request.user,devoir.matiere,devoir.classe):
        raise Http404
    copies = Devoir.objects.devoirsrendus(devoir)
    return render(request, "colleur/devoir.html", {'devoir': devoir ,'copies': copies})

@user_passes_test(is_colleur, login_url='accueil')
def devoirModif(request,id_devoir):
    """Renvoie la vue de la page de modification du devoir dont l'id est id_devoir"""
    devoir=get_object_or_404(Devoir,pk=id_devoir)
    if not is_prof(request.user,devoir.matiere,devoir.classe):
        raise Http404
    form=DevoirForm(devoir.matiere, devoir.classe, request.POST or None,request.FILES or None, instance=devoir)
    oldfile=os.path.join(MEDIA_ROOT,devoir.fichier.name) if devoir.fichier else False
    oldfilecorrige=os.path.join(MEDIA_ROOT,devoir.corrige.name) if devoir.corrige else False
    if form.is_valid():
        if (request.FILES and 'fichier' in request.FILES or form.cleaned_data['fichier'] is False) and oldfile:
            if os.path.isfile(oldfile):
                os.remove(oldfile)
        if (request.FILES and 'corrige' in request.FILES or form.cleaned_data['corrige'] is False) and oldfilecorrige:
            if os.path.isfile(oldfilecorrige):
                os.remove(oldfilecorrige)
        form.save()
        return redirect('colleur_devoirs', devoir.classe.pk)
    return render(request,"colleur/devoirModif.html",{'devoir':devoir,'form':form})


@user_passes_test(is_colleur, login_url='accueil')
def devoirSuppr(request,id_devoir):
    """Essaie de supprimer le devoir dont l'id est id_devoir puis redirige vers la page de gestion des devoirs"""
    devoir=get_object_or_404(Devoir,pk=id_devoir)
    if not is_prof(request.user,devoir.matiere,devoir.classe):
        raise Http404
    try:
        devoir.delete()
    except Exception:
        messages.error(request, "impossible d'effacer le devoir car certains élèves ont déposé leur copie")
    return redirect('colleur_devoirs', devoir.classe.pk)

@user_passes_test(is_colleur, login_url='accueil')
def depotCopie(request, id_devoir, id_eleve):
    """envoie vers un formulaire pour deposer la copie corrigée de l'élève dont l'id est id_eleve pour le devoir dont l'id est id_devoir"""
    devoir = get_object_or_404(Devoir, pk=id_devoir)
    eleve = get_object_or_404(Eleve, pk=id_eleve)
    copiecorrige = DevoirCorrige.objects.filter(eleve = eleve, devoir = devoir)
    oldfile = False
    if copiecorrige.exists():
        copie = copiecorrige.first()
        oldfile=os.path.join(MEDIA_ROOT,copie.fichier.name) 
    else:
        copie = DevoirCorrige(eleve = eleve, devoir = devoir)
    form=CopieForm(request.POST or None,request.FILES or None, instance=copie)
    if form.is_valid():
        if (request.FILES or form.cleaned_data['fichier'] is False) and oldfile:
            if os.path.isfile(oldfile):
                os.remove(oldfile)
        form.save()
        return redirect("colleur_devoir", devoir.pk)
    return render(request, "colleur/renducopie.html", {'form': form, 'devoir': devoir, 'eleve':eleve})

@user_passes_test(is_colleur, login_url='accueil')
def depotCopies(request, id_devoir):
    """envoie vers un formulaire pour deposer sous forme de zip les copies corrigés de certains élèves (voire tous)"""
    devoir = get_object_or_404(Devoir, pk=id_devoir)
    form=CopiesForm(devoir, request.POST or None,request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect("colleur_devoir", devoir.pk)
    return render(request, "colleur/renducopies.html", {'form': form, 'devoir': devoir})

@user_passes_test(is_colleur, login_url='accueil')
def ramasseCopies(request, id_devoir):
    """renvoie une achive zip de toutes les copies du devoir dont l'id est id_devoir"""
    devoir = get_object_or_404(Devoir,pk=id_devoir)
    if all(not is_prof(request.user,devoir.matiere,devoir.classe) for matiere in request.user.colleur.matieres.all()):
        raise Http404
    copies = DevoirRendu.objects.filter(devoir=devoir)
    if copies.exists():
        temp_file = BytesIO()
        with ZipFile(temp_file, 'w') as myzip:
            for copie in copies:
                if copie.fichier:
                    nomfichier = copie.fichier.url[1:].split("/")
                    nomfichier = os.path.join(MEDIA_ROOT,*nomfichier[1:])
                    myzip.write(nomfichier,os.path.basename(nomfichier))
        temp_file.seek(0)
        return FileResponse(temp_file, content_type='application/zip', filename="copies_devoir_{}_{}_{}.zip".format(devoir.numero,devoir.matiere.nom,devoir.classe.nom))
    else:
        raise Http404


@user_passes_test(is_colleur, login_url='accueil')
def td(request,id_classe):
    """renvoie la page des tds de la classe dont l'id est id_classe, dans la matière courante du professeur"""
    classe=get_object_or_404(Classe,pk=id_classe)
    colleur=request.user.colleur
    matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
    if not is_prof(request.user,matiere,classe):
        raise Http404
    tds=TD.objects.filter(classe=classe,matiere=matiere).all()
    td = TD(classe=classe,matiere=matiere)
    form = TDForm(matiere, classe, request.POST or None,request.FILES or None,instance=td)
    if form.is_valid():
        form.save()
        return redirect('colleur_td',classe.pk)
    return render(request,"colleur/tds.html", {'matiere':matiere , 'form':form, 'tds':tds})

@user_passes_test(is_colleur, login_url='accueil')
def tdModif(request,id_td):
    """Renvoie la vue de la page de modification du td dont l'id est id_td"""
    td=get_object_or_404(TD,pk=id_td)
    if not is_prof(request.user,td.matiere,td.classe):
        raise Http404
    form=TDForm(td.matiere, td.classe, request.POST or None,request.FILES or None, instance=td)
    oldfile=os.path.join(MEDIA_ROOT,td.fichier.name) if td.fichier else False
    oldfilecorrige=os.path.join(MEDIA_ROOT,td.corrige.name) if td.corrige else False
    if form.is_valid():
        if (request.FILES and 'fichier' in request.FILES or form.cleaned_data['fichier'] is False) and oldfile:
            if os.path.isfile(oldfile):
                os.remove(oldfile)
        if (request.FILES and 'corrige' in request.FILES or form.cleaned_data['corrige'] is False) and oldfilecorrige:
            if os.path.isfile(oldfilecorrige):
                os.remove(oldfilecorrige)
        form.save()
        return redirect('colleur_td', td.classe.pk)
    return render(request,"colleur/tdModif.html",{'td':td,'form':form})

@user_passes_test(is_colleur, login_url='accueil')
def tdSuppr(request,id_td):
    """Essaie de supprimer le devoir dont l'id est id_devoir puis redirige vers la page de gestion des tds"""
    td=get_object_or_404(TD,pk=id_td)
    if not is_prof(request.user,td.matiere,td.classe):
        raise Http404
    td.delete()
    return redirect('colleur_td', td.classe.pk)

@user_passes_test(is_colleur, login_url='accueil')
def cours(request,id_classe):
    """renvoie la page des cours de la classe dont l'id est id_classe, dans la matière courante du professeur"""
    classe=get_object_or_404(Classe,pk=id_classe)
    colleur=request.user.colleur
    matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
    if not is_prof(request.user,matiere,classe):
        raise Http404
    cours=Cours.objects.filter(classe=classe,matiere=matiere).all()
    cour = Cours(classe=classe,matiere=matiere)
    form = CoursForm(matiere, classe, request.POST or None,request.FILES or None,instance=cour)
    if form.is_valid():
        form.save()
        return redirect('colleur_cours',classe.pk)
    return render(request,"colleur/cours.html", {'matiere':matiere , 'form':form, 'cours':cours})

@user_passes_test(is_colleur, login_url='accueil')
def coursModif(request,id_cours):
    """Renvoie la vue de la page de modification du cours dont l'id est id_cours"""
    cours=get_object_or_404(Cours,pk=id_cours)
    if not is_prof(request.user,cours.matiere,cours.classe):
        raise Http404
    form=CoursForm(cours.matiere, cours.classe, request.POST or None,request.FILES or None, instance=cours)
    oldfile=os.path.join(MEDIA_ROOT,cours.fichier.name) if cours.fichier else False
    if form.is_valid():
        if (request.FILES and 'fichier' in request.FILES or form.cleaned_data['fichier'] is False) and oldfile:
            if os.path.isfile(oldfile):
                os.remove(oldfile)
        form.save()
        return redirect('colleur_cours', cours.classe.pk)
    return render(request,"colleur/coursModif.html",{'cours':cours,'form':form})

@user_passes_test(is_colleur, login_url='accueil')
def coursSuppr(request,id_cours):
    """Essaie de supprimer le cours dont l'id est id_cours puis redirige vers la page de gestion des cours"""
    cours=get_object_or_404(Cours,pk=id_cours)
    if not is_prof(request.user,cours.matiere,cours.classe):
        raise Http404
    cours.delete()
    return redirect('colleur_cours', cours.classe.pk)

@user_passes_test(is_colleur, login_url='accueil')
def autre(request,id_classe):
    """renvoie la page des documents de la classe dont l'id est id_classe, dans la matière courante du professeur"""
    classe=get_object_or_404(Classe,pk=id_classe)
    colleur=request.user.colleur
    matiere=get_object_or_404(Matiere,pk=request.session['matiere'],colleur=colleur)
    if not is_prof(request.user,matiere,classe):
        raise Http404
    docs=Document.objects.filter(classe=classe,matiere=matiere).all()
    doc = Document(classe=classe,matiere=matiere)
    form = DocumentForm(matiere, classe, request.POST or None,request.FILES or None,instance=doc)
    if form.is_valid():
        form.save()
        return redirect('colleur_autre',classe.pk)
    return render(request,"colleur/autre.html", {'matiere':matiere , 'form':form, 'docs':docs})

@user_passes_test(is_colleur, login_url='accueil')
def autreModif(request,id_doc):
    """Renvoie la vue de la page de modification du document dont l'id est id_doc"""
    doc=get_object_or_404(Document,pk=id_doc)
    if not is_prof(request.user,doc.matiere,doc.classe):
        raise Http404
    form=DocumentForm(doc.matiere, doc.classe, request.POST or None,request.FILES or None, instance=doc)
    oldfile=os.path.join(MEDIA_ROOT,doc.fichier.name) if doc.fichier else False
    if form.is_valid():
        if (request.FILES and 'fichier' in request.FILES or form.cleaned_data['fichier'] is False) and oldfile:
            if os.path.isfile(oldfile):
                os.remove(oldfile)
        form.save()
        return redirect('colleur_autre', doc.classe.pk)
    return render(request,"colleur/autreModif.html",{'doc':doc,'form':form})

@user_passes_test(is_colleur, login_url='accueil')
def autreSuppr(request,id_doc):
    """Essaie de supprimer le document dont l'id est id_doc puis redirige vers la page de gestion des documents"""
    doc=get_object_or_404(Document,pk=id_doc)
    if not is_prof(request.user,doc.matiere,doc.classe):
        raise Http404
    doc.delete()
    return redirect('colleur_autre', doc.classe.pk)