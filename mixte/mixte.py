#-*- coding: utf-8 -*-
from accueil.models import Groupe, JourFerie, Colle, Semaine, Eleve, Colleur, Creneau, Ramassage, Matiere, Classe, Config
from datetime import timedelta
from django.db.models import Count, F, Min, Max, Case, Value, When
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from colleur.forms import SemaineForm, CreneauForm, ColleForm, GroupeForm, Groupe2Form, ColloscopeImportForm
from pdf.pdf import easyPdf
from reportlab.platypus import Table, TableStyle
import json
import csv

def mixtegroupe(request,classe,groupes):
    lv1 = dict(Matiere.objects.filter(matieresclasse = classe, lv = 1).values_list('pk', 'nom'))
    lv2 = dict(Matiere.objects.filter(matieresclasse = classe, lv = 2).values_list('pk', 'nom'))
    return render(request,"mixte/groupe.html",{'classe':classe,'groupes':groupes,'lv1':lv1, 'lv2':lv2})

def mixtegroupeCreer(request,classe):
    if classe.semestres:
        form = Groupe2Form(classe,None,request.POST or None)
        html = "mixte/groupe2Modif.html"
    else:
        form = GroupeForm(classe,None,request.POST or None)
        html = "mixte/groupeModif.html"
    if form.is_valid():
        form.save()
        return redirect('groupe_colleur' if request.user.colleur else 'groupe_secret', classe.pk)
    hide = json.dumps([(eleve.id,"" if not eleve.lv1 else eleve.lv1.pk,"" if not eleve.lv2 else eleve.lv2.pk) for eleve in form.fields['eleve0'].queryset])
    return render(request,html,{'modif': False, 'form':form,'classe':classe,'hide':hide})

def mixtegroupesuppr(request,groupe):
    try:
        groupe.delete()
    except Exception:
        messages.error(request,"Impossible de supprimer le groupe car il est présent dans le colloscope")
    return redirect('groupe_colleur' if request.user.colleur else 'groupe_secret',groupe.classe.pk)

def mixtegroupemodif(request,groupe):
    initial = {"eleve{}".format(i):eleve for i,eleve in enumerate(groupe.groupeeleve.all())}
    initial['nom']=groupe.nom
    classe = groupe.classe
    if classe.semestres:
        initial2 = {"eleve2{}".format(i):eleve for i,eleve in enumerate(groupe.groupe2eleve.all())}
        initial = {**initial, **initial2}
        form = Groupe2Form(classe,groupe,request.POST or None, initial=initial)
        html = "mixte/groupe2Modif.html"
    else:
        form = GroupeForm(classe,groupe,request.POST or None, initial=initial)
        html = "mixte/groupeModif.html"
    if form.is_valid():
        form.save()
        return redirect('groupe_colleur' if request.user.colleur else 'groupe_secret', groupe.classe.pk)
    hide = json.dumps([(eleve.id,"" if not eleve.lv1 else eleve.lv1.pk,"" if not eleve.lv2 else eleve.lv2.pk,"" if not eleve.option else eleve.option.pk) for eleve in form.fields['eleve0'].queryset])
    return render(request,html,{'modif':True, 'form':form,'classe':classe,'hide':hide})

def mixtegroupeSwap(request, classe):
    queryset = Classe.objects.filter(pk=classe.pk)
    queryset.update(semestres=Case(
        When(semestres=True, then=Value(False)),
        When(semestres=False, then=Value(True))))
    return redirect('groupe_colleur' if request.user.colleur else 'groupe_secret', classe.pk)

def mixtegroupecsv(request, classe):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="groupes_{}.csv"'.format(classe.nom)
    writer = csv.writer(response,delimiter=";")
    if classe.semestres:
        writer.writerow(["semestre 1","groupe","eleve 1","eleve 2","eleve 3","semestre 2","groupe","eleve 1","eleve 2","eleve 3"])
        for groupe in Groupe.objects.filter(classe = classe).order_by("nom"):
            row = ["",groupe.nom]
            for i,eleve in enumerate(groupe.groupeeleve.order_by("user__last_name", "user__first_name")):
                row.append("{} {}".format(eleve.user.last_name.upper(), eleve.user.first_name.title()))
            row += [""]*(2-i) + ["",groupe.nom]
            for eleve in groupe.groupe2eleve.order_by("user__last_name", "user__first_name"):
                row.append("{} {}".format(eleve.user.last_name.upper(), eleve.user.first_name.title()))
            writer.writerow(row)
    else:
        writer.writerow(["groupe","eleve 1","eleve 2","eleve 3"])
        for groupe in Groupe.objects.filter(classe = classe).order_by("nom"):
            row = [groupe.nom]
            for eleve in groupe.groupeeleve.order_by("user__last_name", "user__first_name"):
                row.append("{} {}".format(eleve.user.last_name.upper(), eleve.user.first_name.title()))
            writer.writerow(row)
    return response


def mixtecolloscope(request,classe,semin,semax,isprof,transpose): 
    form=SemaineForm(request.POST or None,initial={'semin':semin,'semax':semax})
    if form.is_valid():
        return redirect('colloscope2_colleur' if request.user.colleur else 'colloscope2_secret', transpose, classe.pk,form.cleaned_data['semin'].pk,form.cleaned_data['semax'].pk)
    semestre2 = Config.objects.get_config().semestre2
    semestres = classe.semestres and semestre2 <= semax.numero
    if not semestres:
        semestre2 = 1000
    dictGroupes2 = classe.dictGroupes(True, 2) if semestres else False
    if transpose:
        request.session["transpose"] = True
        creneaux, groupes, semaines = Colle.objects.classe2colloscope(classe,semin,semax,False,True)
        return render(request,'mixte/colloscopetranspose.html',
        {'semin':semin,'semax':semax,'semestre2': semestre2, 'form':form,'isprof':isprof,'classe':classe,'dictgroupes':classe.dictGroupes(), 'dictgroupes2': dictGroupes2 ,'semaines':semaines,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'creneauxgroupe':zip(creneaux,groupes),'dictColleurs':classe.dictColleurs(semin,semax)})
    else:
        request.session["transpose"] = False
        jours,creneaux,colles,semaines=Colle.objects.classe2colloscope(classe,semin,semax,False)
        return render(request,'mixte/colloscope.html',
        {'semin':semin,'semax':semax,'semestre2': semestre2, 'form':form,'isprof':isprof,'classe':classe,'jours':jours,'dictgroupes':classe.dictGroupes(), 'dictgroupes2': dictGroupes2 ,'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'dictColleurs':classe.dictColleurs(semin,semax)})

def mixteCSV(request,classe,semin,semax):
    creneaux, groupescolle, semaines = Colle.objects.classe2colloscope(classe,semin,semax,False,True)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="colloscope_{}_S{}-S{}.csv"'.format(classe.nom, semin.numero, semax.numero)
    jours=['lu', 'ma', 'me', 'je', 've', 'sa']
    writer = csv.writer(response,delimiter=",")
    writer.writerow(['Matière','Nom','Prénom','Créneau','Salle']+['S{}'.format(semaine.numero) for semaine in semaines])
    for creneau, groupes in zip(creneaux, groupescolle):
        cases = [(groupe['groupe'].replace(',',";") if groupe['groupe'] != "0" else "") if groupe['temps'] == 20  else (classe.dictEleves()[groupe['id_eleve']] if groupe['id_eleve'] is not None else "")  for groupe in groupes]
        writer.writerow([creneau['matiere_nom'] + ("(lv{})".format(creneau['lv']) if creneau['lv'] else ""), creneau['nom'].upper(), creneau['prenom'].title() ,
            "{} {}h{:02d}".format(jours[creneau['jds']], creneau['heure']//60,(creneau['heure']%60)), creneau['salle']] + cases)
    return response


def mixtecolloscopemodif(request,classe,semin,semax,creneaumodif):
    form1=SemaineForm(request.POST or None,initial={'semin':semin,'semax':semax})
    if form1.is_valid():
        return redirect('colloscopemodif_colleur' if request.user.colleur else 'colloscopemodif_secret',classe.pk,form1.cleaned_data['semin'].pk,form1.cleaned_data['semax'].pk)
    form2=ColleForm(classe,None)
    jours,creneaux,colles,semaines = Colle.objects.classe2colloscope(classe,semin,semax,True)
    creneau=creneaumodif if creneaumodif else Creneau(classe=classe)
    semestre2 = Config.objects.get_config().semestre2
    semestres = classe.semestres and semestre2 <= semax.numero
    form=CreneauForm(request.POST or None,instance=creneau)
    if form.is_valid():
        if creneaumodif:
            form.save()
        else:
            if Creneau.objects.filter(classe=classe,jour=form.cleaned_data['jour'],heure=form.cleaned_data['heure']).exists():
                messages.error(request,"Il y a déjà un créneau ce jour à cette heure, utiliser la fonction dupliquer")
            else:
                form.save()
        return redirect('colloscopemodif_colleur' if request.user.colleur else 'colloscopemodif_secret',classe.pk,semin.pk,semax.pk)
    matieres = list(classe.matieres.filter(colleur__classes=classe, colleur__user__is_active = True).order_by('nom','lv','temps').values_list('pk','nom','couleur','temps','lv').annotate(nb=Count("colleur")))
    colleurs = list(Colleur.objects.exclude(matieres = None).filter(classes=classe, matieres__in = classe.matieres.all(), user__is_active = True).values_list('pk','user__first_name','user__last_name').order_by("matieres__nom", "matieres__lv", "matieres__temps", "user__last_name", "user__first_name"))
    groupes = Groupe.objects.filter(classe=classe)
    matieresgroupes = [[groupe for groupe in groupes if groupe.haslangue(matiere)] for matiere in classe.matieres.filter(colleur__classes=classe).distinct().order_by("nom", "lv", "temps")]
    # if not any(matieresgroupes):
    #     matieresgroupes = False
    matieresgroupes2 = [[groupe for groupe in groupes if groupe.haslangue(matiere, 2)] for matiere in classe.matieres.filter(colleur__classes=classe).distinct().order_by("nom", "lv", "temps")] if semestres else []
    # if not any (matieresgroupes2):
    #     matieresgroupes2 = False
    listeColleurs = []
    for x in matieres:
        listeColleurs.append(colleurs[:x[5]])
        del colleurs[:x[5]]
    largeur=str(650+42*creneaux.count())+'px'
    hauteur=str(27*(len(matieres)+classe.classeeleve.count()+Colleur.objects.filter(classes=classe).count()))+'px'
    if not semestres:
        semestre2 = -1
    return render(request,'mixte/colloscopeModif.html',
    {'semin':semin,'semax':semax,'form1':form1,'form':form,'form2':form2,'largeur':largeur,'hauteur':hauteur,'groupes':groupes,'matieres':zip(matieres,listeColleurs,matieresgroupes),'matieres2': "" if not semestres else zip(matieres,listeColleurs,matieresgroupes2),'creneau':creneaumodif\
    ,'classe':classe,'semestre2':semestre2,'jours':jours,'creneaux':creneaux,'listejours':["lundi","mardi","mercredi","jeudi","vendredi","samedi"],'collesemaine':zip(semaines,colles),'dictColleurs':classe.dictColleurs(semin,semax), 'dictGroupes':json.dumps(classe.dictGroupes(False)), 'dictGroupes2':json.dumps(classe.dictGroupes(False, 2) if semestres else ""), 'dictEleves':json.dumps(classe.dictElevespk())})

def mixteColloscopeImport(request, classe):
    form = ColloscopeImportForm(classe, request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect('colloscope_colleur'  if request.user.colleur else 'colloscope_secret', 1, classe.pk)
    return render(request,'mixte/colloscopeimport.html',{'form':form, 'classe':classe})


def mixtecreneausuppr(request,creneau,id_semin,id_semax):
    try:
        creneau.delete()
    except Exception:
        messages.error(request,"Vous ne pouvez pas effacer un créneau qui contient des colles")
    return redirect('colloscopemodif_colleur' if request.user.colleur else 'colloscopemodif_secret',creneau.classe.pk,id_semin,id_semax)

def mixtecreneaudupli(user,creneau,id_semin,id_semax):
    creneau.pk=None
    creneau.salle=None
    creneau.save()
    return redirect('colloscopemodif_colleur' if user.colleur else 'colloscopemodif_secret',creneau.classe.pk,id_semin,id_semax)

def mixteajaxcompat(classe):
    LISTE_JOURS=['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche']
    colleurs = Colle.objects.filter(creneau__classe=classe,matiere__temps__gt=20).values('colleur__user__first_name','colleur__user__last_name','semaine__numero','creneau__jour','creneau__heure').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','creneau__jour','creneau__heure','colleur__user__last_name','colleur__user__first_name')
    colleurs="\n".join(["le colleur {} {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['colleur__user__first_name'].title(),valeur['colleur__user__last_name'].upper(),valeur['nbcolles'],valeur['semaine__numero'],LISTE_JOURS[valeur['creneau__jour']],valeur['creneau__heure']//60,valeur['creneau__heure']%60) for valeur in colleurs])
    colleurs_groupe = Colle.objects.compatColleur(classe.pk)
    colleurs += "\n".join(["le colleur {} {} colle {} étudiants en semaine {} le {} à {}h{:02d}".format(valeur['prenom'].title(),valeur['nom'].upper(),valeur['nbeleves'],valeur['numero'],LISTE_JOURS[valeur['jour']],valeur['heure']//60,valeur['heure']%60) for valeur in colleurs_groupe])
    eleves = Colle.objects.filter(groupe__classe=classe).values('groupe__nom','semaine__numero','creneau__jour','creneau__heure').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','creneau__jour','creneau__heure','groupe__nom')
    eleves="\n".join(["le groupe {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['groupe__nom'],valeur['nbcolles'],valeur['semaine__numero'],LISTE_JOURS[valeur['creneau__jour']],valeur['creneau__heure']//60,valeur['creneau__heure']%60) for valeur in eleves])
    elevesolo = Colle.objects.compatEleve(classe.pk)
    elevesolo = "\n".join(["l'élève {} {} a {} colles en semaine {} le {} à {}h{:02d}".format(valeur['prenom'].title(),valeur['nom'].upper(),valeur['nbColles'],valeur['numero'],LISTE_JOURS[valeur['jour']],valeur['heure']//60,valeur['heure']%60) for valeur in elevesolo])
    groupes=Colle.objects.filter(groupe__classe=classe).values('groupe__nom','matiere__nom','semaine__numero').annotate(nbcolles = Count('pk',distinct=True)).filter(nbcolles__gt=1).order_by('semaine__numero','matiere__nom','groupe__nom')
    groupes = "\n".join(["le groupe {} a {} colles de {} en semaine {}".format(valeur['groupe__nom'],valeur['nbcolles'],valeur['matiere__nom'].title(),valeur['semaine__numero']) for valeur in groupes])
    reponse=colleurs+"\n\n"*int(bool(colleurs))+eleves+"\n\n"*int(bool(eleves))+elevesolo+"\n\n"*int(bool(elevesolo))+groupes
    if not reponse:
        reponse="aucune incompatibilité dans le colloscope"
    return HttpResponse(reponse)

def mixteajaxcolloscope(matiere,colleur,groupe,semaine,creneau):
    if Colle.objects.filter(semaine=semaine, creneau=creneau).exclude(colleur=colleur).exists() or Colle.objects.filter(semaine=semaine, creneau=creneau).exclude(matiere=matiere).exists():
        Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
        noms = str(groupe.nom)
    else:
        # si le groupe a déjà une colle sur le couple semaine/créneau
        groupes = Colle.objects.filter(semaine=semaine,creneau=creneau).order_by('groupe__nom').values_list('groupe__nom',flat=True)
        if groupe.nom in Colle.objects.filter(semaine=semaine,creneau=creneau).values_list('groupe__nom',flat=True):
            return HttpResponse("{}:{}".format(creneau.classe.dictColleurs()[colleur.pk],",".join([str(x) for x in groupes])))
        # on vérifie si on peut cumuler les groupes ou s'il faut effacer
        semestre2 = Config.objects.get_config().semestre2
        classe = creneau.classe
        if classe.semestres and semaine.numero >= semestre2:
            options = {classe.option1, classe.option2} - {None}
            options = [x.pk for x in options]
            eleves = Colle.objects.filter(semaine=semaine,creneau=creneau).values_list('groupe__groupe2eleve','groupe__groupe2eleve__option','groupe__groupe2eleve__lv1','groupe__groupe2eleve__lv2','matiere__pk','matiere__lv').distinct()
            nbeleves = len([x for x in eleves if x[4] in options and x[1] == x[4] or x[4] not in options and x[5] == 0 or x[5] == 1 and x[2] == x[4] or x[5] == 2 and x[3] == x[4]])
            eleves2 = Eleve.objects.filter(groupe2=groupe)
            nbeleves2 = len([x for x in eleves2 if matiere.pk in options and x.option == matiere or matiere.pk not in options and matiere.lv == 0 or matiere.lv == 1 and x.lv1 == matiere or matiere.lv == 2 and x.lv2 == matiere])
        else:
            eleves = Colle.objects.filter(semaine=semaine,creneau=creneau).values_list('groupe__groupeeleve','groupe__groupeeleve__lv1','groupe__groupeeleve__lv2','matiere__pk','matiere__lv').distinct()
            nbeleves = len([x for x in eleves if x[4] == 0 or x[4] == 1 and x[1] == x[3] or x[4] == 2 and x[2] == x[3]])
            eleves2 = Eleve.objects.filter(groupe=groupe)
            nbeleves2 = len([x for x in eleves2 if matiere.lv == 0 or matiere.lv == 1 and x.lv1 == matiere or matiere.lv == 2 and x.lv2 == matiere])
        if nbeleves + nbeleves2 > 3:
            Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
            Colle(semaine=semaine,creneau=creneau,groupe=groupe,colleur=colleur,matiere=matiere).save()
            return HttpResponse("{}:{}".format(creneau.classe.dictColleurs()[colleur.pk],groupe.nom))
        noms = ",".join([str(x) for x in Colle.objects.filter(semaine=semaine,creneau=creneau).values_list('groupe__nom',flat=True)]+[str(groupe.nom)])
    Colle(semaine=semaine,creneau=creneau,groupe=groupe,colleur=colleur,matiere=matiere).save()
    return HttpResponse("{}:{}".format(creneau.classe.dictColleurs()[colleur.pk],noms))

def mixteajaxcolloscopeeleve(matiere,colleur,id_eleve,semaine,creneau,login):
    try:
        eleve = Eleve.objects.get(pk=id_eleve)
    except Exception:
        eleve = None
    Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
    feries = [dic['date'] for dic in JourFerie.objects.all().values('date')]
    colle=Colle(semaine=semaine,creneau=creneau,colleur=colleur,eleve=eleve,matiere=matiere)
    if eleve is None:
        colle.classe=creneau.classe
        colle.save()
        return HttpResponse(creneau.classe.dictColleurs()[colleur.pk]+':'+colle.classe.nom[:4])
    else:
        colle.save()
        return HttpResponse(creneau.classe.dictColleurs()[colleur.pk]+':'+login)

def mixteajaxcolloscopeeffacer(semaine,creneau):
    Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
    return HttpResponse("efface")

def mixteajaxmajcolleur(matiere,classe):
    colleurs=Colleur.objects.filter(user__is_active=True,matieres=matiere,classes=classe).values('id','user__first_name','user__last_name','user__username').order_by('user__last_name','user__first_name')
    colleurs=[{'nom': value['user__first_name'].title()+" "+value['user__last_name'].upper()+' ('+classe.dictColleurs()[value['id']]+')','id':value['id']} for value in colleurs]
    return HttpResponse(json.dumps([matiere.temps]+colleurs))

def mixteajaxcolloscopemulti(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation):
    frequence = int(frequence)
    duree = int(duree)
    modulo = semaine.numero%frequence
    ecrase = Colle.objects.filter(creneau = creneau,semaine__numero__range=(semaine.numero,semaine.numero+duree-1)).annotate(semaine_mod = F('semaine__numero') % frequence).filter(semaine_mod=modulo).count()
    nbferies = JourFerie.objects.recupFerie(creneau.jour,semaine,duree,frequence,modulo)
    semestre2 = Config.objects.get_config().semestre2
    if creneau.classe.semestres and semaine.numero < semestre2 and semaine.numero + duree > semestre2 and matiere != -1: # si à cheval sur les 2 semestres
        cheval = "Attention, les groupes des 2 semestres sont différents et vous planifiez à cheval sur les 2 semestres.\nLa planification se fera uniquement au premier semestre"
    else:
        cheval = ""
    if not(ecrase and nbferies[0]):
        return HttpResponse("{}_{}_{}".format(ecrase,nbferies[0],cheval))
    else:
        return mixteajaxcolloscopemulticonfirm(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation)

def mixteajaxcolloscopemulticonfirm(matiere,colleur,id_groupe,id_eleve,semaine,creneau,duree, frequence, permutation):
    creneaux={'creneau':creneau.pk}
    creneaux['semgroupe']=[]
    duree = int(duree)
    frequence = int(frequence)
    id_groupe = int(id_groupe)
    id_eleve = int(id_eleve)
    numsemaine=semaine.numero
    if matiere == -1: # si on ne fait qu'effacer
        i = 0
        for numero in range(numsemaine,numsemaine+duree,frequence):
            try:
                semainecolle=Semaine.objects.get(numero=numero)
                Colle.objects.filter(creneau=creneau,semaine=semainecolle).delete()
                creneaux['semgroupe'].append({'semaine':semainecolle.numero})
            except Exception:
                pass
            i+=1
        return HttpResponse(json.dumps(creneaux))
    if duree == 1 and id_groupe:
        groupe = get_object_or_404(Groupe,pk=id_groupe)
        if Colle.objects.filter(semaine=semaine, creneau=creneau).exclude(colleur=colleur).exists() or Colle.objects.filter(semaine=semaine, creneau=creneau).exclude(matiere=matiere).exists():
            Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
            noms = str(groupe.nom)
        else:
            # si le groupe a déjà une colle sur le couple semaine/créneau
            groupes = Colle.objects.filter(semaine=semaine,creneau=creneau).order_by('groupe__nom').values_list('groupe__nom',flat=True)
            if groupe.nom in Colle.objects.filter(semaine=semaine,creneau=creneau).values_list('groupe__nom',flat=True):
                return HttpResponse("{}:{}".format(creneau.classe.dictColleurs()[colleur.pk],",".join([str(x) for x in groupes])))
            # on vérifie si on peut cumuler les groupes ou s'il faut effacer
            semestre2 = Config.objects.get_config().semestre2
            classe = creneau.classe
            if classe.semestres and semaine.numero >= semestre2:
                options = {classe.option1, classe.option2} - {None}
                options = [x.pk for x in options]
                eleves = Colle.objects.filter(semaine=semaine,creneau=creneau).values_list('groupe__groupe2eleve','groupe__groupe2eleve__option','groupe__groupe2eleve__lv1','groupe__groupe2eleve__lv2','matiere__pk','matiere__lv').distinct()
                nbeleves = len([x for x in eleves if x[4] in options and x[1] == x[4] or x[4] not in options and x[5] == 0 or x[5] == 1 and x[2] == x[4] or x[5] == 2 and x[3] == x[4]])
                eleves2 = Eleve.objects.filter(groupe2=groupe)
                nbeleves2 = len([x for x in eleves2 if matiere.pk in options and x.option == matiere or matiere.pk not in options and matiere.lv == 0 or matiere.lv == 1 and x.lv1 == matiere or matiere.lv == 2 and x.lv2 == matiere])
            else:
                eleves = Colle.objects.filter(semaine=semaine,creneau=creneau).values_list('groupe__groupeeleve','groupe__groupeeleve__lv1','groupe__groupeeleve__lv2','matiere__pk','matiere__lv').distinct()
                nbeleves = len([x for x in eleves if x[4] == 0 or x[4] == 1 and x[1] == x[3] or x[4] == 2 and x[2] == x[3]])
                eleves2 = Eleve.objects.filter(groupe=groupe)
                nbeleves2 = len([x for x in eleves2 if matiere.lv == 0 or matiere.lv == 1 and x.lv1 == matiere or matiere.lv == 2 and x.lv2 == matiere])
            if nbeleves + nbeleves2 > 3:
                Colle.objects.filter(semaine=semaine,creneau=creneau).delete()
                Colle(semaine=semaine,creneau=creneau,groupe=groupe,colleur=colleur,matiere=matiere).save()
                return HttpResponse("{}:{}".format(creneau.classe.dictColleurs()[colleur.pk],groupe.nom))
            noms = ",".join([str(x) for x in Colle.objects.filter(semaine=semaine,creneau=creneau).values_list('groupe__nom',flat=True)]+[str(groupe.nom)])
        Colle(semaine=semaine,creneau=creneau,groupe=groupe,colleur=colleur,matiere=matiere).save()
        creneaux={'creneau':creneau.pk,'couleur':matiere.couleur,'colleur':creneau.classe.dictColleurs()[colleur.pk]}
        creneaux['semgroupe'] = [{'semaine':semaine.numero,'groupe':noms}]
        return HttpResponse(json.dumps(creneaux))
    permutation = int(permutation)
    groupe=None if not id_groupe else get_object_or_404(Groupe,pk=id_groupe)
    eleve=None if not id_eleve else get_object_or_404(Eleve,pk=id_eleve)
    semestre2 = Config.objects.get_config().semestre2
    if creneau.classe.semestres and semaine.numero < semestre2 and semaine.numero + duree > semestre2: # si à cheval sur les 2 semestres
        duree = semestre2-semaine.numero    
    if id_groupe:
        if creneau.classe.semestres and semaine.numero >= semestre2:
            if matiere in (creneau.classe.option1, creneau.classe.option2):
                groupeseleves=list(Groupe.objects.filter(classe=creneau.classe,groupe2eleve__option=matiere).distinct().order_by('nom'))
            elif matiere.lv == 0:
                groupeseleves=list(Groupe.objects.filter(classe=creneau.classe).order_by('nom'))
            elif matiere.lv == 1:
                groupeseleves=list(Groupe.objects.filter(classe=creneau.classe,groupe2eleve__lv1=matiere).distinct().order_by('nom'))
            elif matiere.lv == 2:
                groupeseleves=list(Groupe.objects.filter(classe=creneau.classe,groupe2eleve__lv2=matiere).distinct().order_by('nom'))
        else:
            if matiere.lv == 0:
                groupeseleves=list(Groupe.objects.filter(classe=creneau.classe).order_by('nom'))
            elif matiere.lv == 1:
                groupeseleves=list(Groupe.objects.filter(classe=creneau.classe,groupeeleve__lv1=matiere).distinct().order_by('nom'))
            elif matiere.lv == 2:
                groupeseleves=list(Groupe.objects.filter(classe=creneau.classe,groupeeleve__lv2=matiere).distinct().order_by('nom'))
        groupeseleves.sort(key = lambda x:int(x.nom))
        rang=groupeseleves.index(groupe)
    elif id_eleve:
        if matiere.lv == 0:
            groupeseleves=list(Eleve.objects.filter(classe=creneau.classe))
        elif matiere.lv == 1:
            groupeseleves=list(Eleve.objects.filter(classe=creneau.classe,lv1=matiere))
        elif matiere.lv == 2:
            groupeseleves=list(Eleve.objects.filter(classe=creneau.classe,lv2=matiere))
        rang=groupeseleves.index(eleve)
    i=0
    creneaux={'creneau':creneau.pk,'couleur':matiere.couleur,'colleur':creneau.classe.dictColleurs()[colleur.pk]}
    creneaux['semgroupe']=[]
    feries = [dic['date'] for dic in JourFerie.objects.all().values('date')]
    if id_groupe:
        for numero in range(numsemaine,numsemaine+duree,frequence):
            try:
                semainecolle=Semaine.objects.get(numero=numero)
                Colle.objects.filter(creneau=creneau,semaine=semainecolle).delete()
                groupe=groupeseleves[(rang+i*permutation)%len(groupeseleves)]
                Colle(creneau=creneau,colleur=colleur,matiere=matiere,groupe=groupe,semaine=semainecolle).save()
                creneaux['semgroupe'].append({'semaine':semainecolle.numero,'groupe':groupe.nom})
            except:
                pass
            i+=1
    elif id_eleve:
        for numero in range(numsemaine,numsemaine+duree,frequence):
            try:
                semainecolle=Semaine.objects.get(numero=numero)
                if semainecolle.lundi + timedelta(days = creneau.jour) not in feries:
                    Colle.objects.filter(creneau=creneau,semaine=semainecolle).delete()
                    eleve=groupeseleves[(rang+i*permutation)%len(groupeseleves)]
                    Colle(creneau=creneau,colleur=colleur,matiere=matiere,eleve=eleve,semaine=semainecolle).save()
                    creneaux['semgroupe'].append({'semaine':semainecolle.numero,'groupe':creneau.classe.dictEleves()[eleve.pk]})
            except Exception:
                pass
            i+=1
    else:
        for numero in range(numsemaine,numsemaine+duree,frequence):
            try:
                semainecolle=Semaine.objects.get(numero=numero)
                if semainecolle.lundi + timedelta(days = creneau.jour) not in feries:
                    Colle.objects.filter(creneau=creneau,semaine=semainecolle).delete()
                    Colle(creneau=creneau,colleur=colleur,matiere=matiere,eleve=None,semaine=semainecolle,classe = creneau.classe).save()
                    creneaux['semgroupe'].append({'semaine':semainecolle.numero,'groupe':creneau.classe.nom[:4]})
            except Exception:
                pass
    return HttpResponse(json.dumps(creneaux))
    

def mixteRamassagePdfParClasse(ramassage,total,parmois,full):
	"""Renvoie le fichier PDF du ramassage par classe correspondant au ramassage dont l'id est id_ramassage
	si total vaut 1, les totaux par classe et matière sont calculés"""
	LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
	response = HttpResponse(content_type='application/pdf')
	if Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).exists() and not full:# s'il existe un ramassage antérieur
		debut = Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).aggregate(Max('moisFin'))['moisFin__max'] + timedelta(days=1)
	else:
		debut = Semaine.objects.aggregate(Min('lundi'))['lundi__min']
	fin = ramassage.moisFin
	moisdebut = 12*debut.year+debut.month-1
	decomptes = Ramassage.objects.decompteRamassage(ramassage, csv = False, parClasse = True, parMois=bool(parmois), full = full, colleur = colleur, parColleur = parColleur)
	nomfichier="ramassagePdfParClasse{}-{}-{}_{}-{}-{}.pdf".format(debut.year,debut.month,debut.day,fin.year,fin.month,fin.day)
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	pdf = easyPdf(titre="Ramassage des colles du {} au {}".format(debut.strftime("%d/%m/%Y"),fin.strftime("%d/%m/%Y")),marge_x=30,marge_y=30)
	largeurcel=(pdf.format[0]-2*pdf.marge_x)/(10+parmois)
	hauteurcel=30
	total=int(total)
	for classe, listeClasse, nbMatieres in decomptes:
		totalclasse = 0
		pdf.debutDePage(soustitre = classe)
		nbKolleurs = nbMatieres
		if total:
			nbKolleurs += 1 + len([x for x,y,z in listeClasse]) # on rajoute le nombre de matières et 1 pour la classe
		LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
											,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
											,('VALIGN',(0,0),(-1,-1),'MIDDLE')
											,('ALIGN',(0,0),(-1,-1),'CENTRE')
											,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
											,('SIZE',(0,0),(-1,-1),8)])
		data = [["Matière","Établissement","Grade","Colleur"] + (["mois"] if parmois else []) + ["heures"]]+[[""]*(5+parmois) for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
		ligneMat=ligneEtab=ligneGrade=ligneColleur=ligneMois=1
		for matiere, listeEtabs, nbEtabs in listeClasse:
			totalmatiere = 0
			data[ligneMat][0]=matiere
			if nbEtabs>1:
				LIST_STYLE.add('SPAN',(0,ligneMat),(0,min(ligneMat+nbEtabs-1,22)))
			ligneMat+=nbEtabs
			for etablissement, listeGrades, nbGrades in listeEtabs:
				data[ligneEtab][1]='Inconnu' if not etablissement else etablissement.title()
				if nbGrades>1:
					LIST_STYLE.add('SPAN',(1,ligneEtab),(1,min(ligneEtab+nbGrades-1,22)))
				ligneEtab+=nbGrades
				for grade, listeColleurs, nbColleurs in listeGrades:
					data[ligneGrade][2]=grade
					if nbColleurs>1:
						LIST_STYLE.add('SPAN',(2,ligneGrade),(2,min(ligneGrade+nbColleurs-1,22)))
					ligneGrade+=nbColleurs
					if parmois:# si on ramassage pour chaque mois
						for colleur, listeMois, nbMois in listeColleurs:
							data[ligneColleur][3]=colleur
							if nbMois>1:
								LIST_STYLE.add('SPAN',(3,ligneColleur),(3,min(ligneColleur+nbMois-1,22)))
							ligneColleur+=nbMois
							for moi,  heures in listeMois:
								totalmatiere += heures
								if moi<moisdebut:
									LIST_STYLE.add('TEXTCOLOR',(4,ligneMois),(5,ligneMois),(1,0,0))
								data[ligneMois][4]=LISTE_MOIS[moi%12+1]
								data[ligneMois][5]="{:.2f}h".format(heures/60).replace('.',',')
								ligneMois+=1
								if ligneMois==23 and nbKolleurs>22: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
									t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel, largeurcel, largeurcel],rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
									t.setStyle(LIST_STYLE)
									w,h=t.wrapOn(pdf,0,0)
									t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
									pdf.finDePage()
									# on redémarre sur une nouvelle page
									pdf.debutDePage(soustitre = classe)
									LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
													,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
													,('VALIGN',(0,0),(-1,-1),'MIDDLE')
													,('ALIGN',(0,0),(-1,-1),'CENTRE')
													,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
													,('SIZE',(0,0),(-1,-1),8)])
									nbKolleurs-=22
									data = [["Matière","Établissement","Grade","Colleur","mois","heures"]]+[[""]*6 for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
									ligneEtab-=22
									ligneGrade-=22
									ligneMat-=22
									ligneColleur-=22
									ligneMois = 1
									if ligneMat>1:
										data[1][0]=matiere
										if ligneMat>2:
											LIST_STYLE.add('SPAN',(0,1),(0,min(ligneMat-1,22)))
										if ligneEtab>1:
											data[1][1]='Inconnu' if not etablissement else etablissement.title()
											if ligneEtab>2:
												LIST_STYLE.add('SPAN',(1,1),(1,min(ligneEtab-1,22)))
											if ligneGrade>1:
												data[1][2]=grade
												if ligneGrade>2:
													LIST_STYLE.add('SPAN',(2,1),(2,min(ligneGrade-1,22)))
												if ligneColleur>1:
													data[1][3]=colleur
													if ligneColleur>2:
														LIST_STYLE.add('SPAN',(3,1),(3,min(ligneColleur-1,22)))
			# fin matière
					else:# si on ne ramasse pas pour chaque mois mais globalement sur la période de ramassage
						for colleur, heures in listeColleurs:
							totalmatiere += heures
							data[ligneColleur][3]=colleur
							data[ligneColleur][4]="{:.2f}h".format(heures/60).replace('.',',')
							ligneColleur+=1
							if ligneColleur==23 and nbKolleurs>22: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
								t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel, largeurcel],rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
								t.setStyle(LIST_STYLE)
								w,h=t.wrapOn(pdf,0,0)
								t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
								pdf.finDePage()
								# on redémarre sur une nouvelle page
								pdf.debutDePage(soustitre = classe)
								LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
												,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
												,('VALIGN',(0,0),(-1,-1),'MIDDLE')
												,('ALIGN',(0,0),(-1,-1),'CENTRE')
												,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
												,('SIZE',(0,0),(-1,-1),8)])
								nbKolleurs-=22
								data = [["Matière","Établissement","Grade","Colleur", "heures"]]+[[""]*5 for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
								ligneEtab-=22
								ligneGrade-=22
								ligneMat-=22
								ligneColleur=1
								if ligneMat>1:
									data[1][0]=matiere.title()
									if ligneMat>2:
										LIST_STYLE.add('SPAN',(0,1),(0,min(ligneMat-1,22)))
									if ligneEtab>1:
										data[1][1]='Inconnu' if not etablissement else etablissement.title()
										if ligneEtab>2:
											LIST_STYLE.add('SPAN',(1,1),(1,min(ligneEtab-1,22)))
										if ligneGrade>1:
											data[1][2]=grade
											if ligneGrade>2:
												LIST_STYLE.add('SPAN',(2,1),(2,min(ligneGrade-1,22)))
			# fin matière
			totalclasse += totalmatiere
			if total:
				LIST_STYLE.add('SPAN',(0,ligneColleur),(3+parmois,ligneColleur))
				LIST_STYLE.add('BACKGROUND',(0,ligneColleur),(-1,ligneColleur),(.8,.8,.8))
				data[ligneColleur] = ["total {}".format(matiere.title())]+[""]*(3+parmois)+["{:.2f}h".format(totalmatiere/60).replace('.',',')]
				ligneEtab+=1
				ligneGrade+=1
				ligneMat+=1
				ligneColleur+=1
				ligneMois+=1
				if ligneColleur==23 and nbKolleurs>22: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
					t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel, largeurcel] + ([largeurcel] if parmois else []),rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
					t.setStyle(LIST_STYLE)
					w,h=t.wrapOn(pdf,0,0)
					t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
					pdf.finDePage()
					# on redémarre sur une nouvelle page
					pdf.debutDePage(soustitre = classe)
					LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
									,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
									,('VALIGN',(0,0),(-1,-1),'MIDDLE')
									,('ALIGN',(0,0),(-1,-1),'CENTRE')
									,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
									,('SIZE',(0,0),(-1,-1),8)])
					nbKolleurs-=22
					data = [["Matière","Établissement","Grade","Colleur"] + (["mois"] if parmois else []) + ["heures"]]+[[""]*(5+parmois) for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
					ligneEtab-=22
					ligneGrade-=22
					ligneMat-=22
					if parmois:
						ligneColleur-=22
						ligneMois=1
					else:
						ligneColleur=1
		# fin classe
		if total:
			LIST_STYLE.add('SPAN',(0,ligneColleur),(3+parmois,ligneColleur))
			LIST_STYLE.add('BACKGROUND',(0,ligneColleur),(-1,ligneColleur),(.7,.7,.7))
			data[ligneColleur] = ["total {}".format(classe)]+[""]*(3+parmois)+["{:.2f}h".format(totalclasse/60).replace('.',',')]
			ligneEtab+=1
			ligneGrade+=1
			ligneMat+=1
			ligneColleur+=1
		t=Table(data,colWidths=[2*largeurcel,3*largeurcel,largeurcel,3*largeurcel,largeurcel] + ([largeurcel] if parmois else []),rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
		t.setStyle(LIST_STYLE)
		w,h=t.wrapOn(pdf,0,0)
		t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
		pdf.finDePage()
	pdf.save()
	fichier = pdf.buffer.getvalue()
	pdf.buffer.close()
	response.write(fichier)
	return response

def mixteRamassagePdfParColleur(ramassage,parmois,full,colleur = False):
	"""Renvoie le fichier PDF du ramassage par classe correspondant au ramassage dont l'id est id_ramassage"""
	LISTE_MOIS=["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
	response = HttpResponse(content_type='application/pdf')
	if Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).exists() and not full:# s'il existe un ramassage antérieur
		debut = Ramassage.objects.filter(moisFin__lt=ramassage.moisFin).aggregate(Max('moisFin'))['moisFin__max'] + timedelta(days=1)
	else:
		debut = Semaine.objects.aggregate(Min('lundi'))['lundi__min']
	fin = ramassage.moisFin
	moisdebut = 12*debut.year+debut.month-1
	decomptes = Ramassage.objects.decompteRamassage(ramassage, csv = False, parClasse = True, parMois=bool(parmois), full = full, colleur = colleur, parColleur = 1)
	nomfichier="ramassagePdfParColleur{}-{}-{}_{}-{}-{}.pdf".format(debut.year,debut.month,debut.day,fin.year,fin.month,fin.day)
	response['Content-Disposition'] = "attachment; filename={}".format(nomfichier)
	pdf = easyPdf(titre="Ramassage des colles du {} au {}".format(debut.strftime("%d/%m/%Y"),fin.strftime("%d/%m/%Y")),marge_x=30,marge_y=30)
	largeurcel=(pdf.format[0]-2*pdf.marge_x)/10
	hauteurcel=30
	for colleur, etablissement, grade, listeMatieres, nbMatieres in decomptes:
		totalColleur = 0
		nbKolleurs = nbMatieres
		pdf.debutDePage(soustitre = colleur)
		pdf.setFillColorRGB(0,0,0)
		pdf.y -= 10
		pdf.x = pdf.marge_x
		pdf.setFont("Helvetica-Bold",10)
		pdf.drawString(pdf.x,pdf.y,"Établissement d'exercice: {}".format(etablissement))
		pdf.x = pdf.format[0]-pdf.marge_x
		pdf.drawRightString(pdf.x,pdf.y,"Grade: {}".format(grade))
		pdf.y += 10
		LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
											,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
											,('VALIGN',(0,0),(-1,-1),'MIDDLE')
											,('ALIGN',(0,0),(-1,-1),'CENTRE')
											,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
											,('SIZE',(0,0),(-1,-1),8)])
		data = [["Matière","Classe"] + (["mois"] if parmois else []) + ["heures"]]+[[""]*(3+parmois) for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
		ligneMat=ligneClasse=ligneMois=1
		for matiere, listeClasse, nbClasses in listeMatieres:
			totalmatiere = 0
			data[ligneMat][0] = matiere
			if nbClasses > 1:
				LIST_STYLE.add('SPAN',(0,ligneMat),(0,min(ligneMat+nbClasses-1,22)))
			ligneMat += nbClasses
			if parmois: # si on fait un ramassage pour chaque mois
				for classe, listeMois, nbMois in listeClasse:
					data[ligneClasse][1]=classe
					if nbMois>1:
						LIST_STYLE.add('SPAN',(1,ligneClasse),(1,min(ligneClasse+nbMois-1,22)))
					ligneClasse+=nbMois
					for moi,  heures in listeMois:
						totalColleur += heures
						if moi<moisdebut:
							LIST_STYLE.add('TEXTCOLOR',(2,ligneMois),(3,ligneMois),(1,0,0))
						data[ligneMois][2]=LISTE_MOIS[moi%12+1]
						data[ligneMois][3]="{:.2f}h".format(heures/60).replace('.',',')
						ligneMois+=1
						if ligneMois==23 and nbKolleurs>22: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
							t=Table(data,colWidths=[2.5*largeurcel,2.5*largeurcel,2.5*largeurcel,2.5*largeurcel],rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
							t.setStyle(LIST_STYLE)
							w,h=t.wrapOn(pdf,0,0)
							t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
							pdf.finDePage()
							# on redémarre sur une nouvelle page
							pdf.debutDePage(soustitre = colleur)
							LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
											,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
											,('VALIGN',(0,0),(-1,-1),'MIDDLE')
											,('ALIGN',(0,0),(-1,-1),'CENTRE')
											,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
											,('SIZE',(0,0),(-1,-1),8)])
							nbKolleurs-=22
							data = [["Matière","Classe","mois"] + ["heures"]]+[[""]*(3+parmois) for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
							ligneMat-=22
							ligneClasse-=22
							ligneMois = 1
							if ligneMat>1:
								data[1][0]=matiere
								if ligneMat>2:
									LIST_STYLE.add('SPAN',(0,1),(0,min(ligneMat-1,22)))
								if ligneClasse>1:
									data[1][1]=classe
									if ligneClasse>2:
										LIST_STYLE.add('SPAN',(1,1),(1,min(ligneClasse-1,22)))
			else:# si on ne ramasse pas pour chaque mois mais globalement sur la période de ramassage
				for classe, heures in listeClasse:
					totalmatiere += heures
					data[ligneClasse][1]=classe
					data[ligneClasse][2]="{:.2f}h".format(heures/60).replace('.',',')
					ligneClasse+=1
					if ligneClasse==23 and nbKolleurs>22: # si le tableau prend toute une page (et qu'il doit continuer), on termine la page et on recommence un autre tableau
						t=Table(data,colWidths=[4*largeurcel,4*largeurcel,2*largeurcel],rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
						t.setStyle(LIST_STYLE)
						w,h=t.wrapOn(pdf,0,0)
						t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
						pdf.finDePage()
						# on redémarre sur une nouvelle page
						pdf.debutDePage(soustitre = colleur)
						LIST_STYLE = TableStyle([('GRID',(0,0),(-1,-1),1,(0,0,0))
										,('BACKGROUND',(0,0),(-1,0),(.6,.6,.6))
										,('VALIGN',(0,0),(-1,-1),'MIDDLE')
										,('ALIGN',(0,0),(-1,-1),'CENTRE')
										,('FACE',(0,0),(-1,-1),"Helvetica-Bold")
										,('SIZE',(0,0),(-1,-1),8)])
						nbKolleurs-=22
						data = [["Matière","Classe"] + ["heures"]]+[[""]*(3+parmois) for i in range(min(22,nbKolleurs))] # on créé un tableau de la bonne taille, rempli de chaînes vides
						ligneMat-=22
						ligneClasse=1
						if ligneMat>1:
							data[1][0]=matiere.title()
							if ligneMat>2:
								LIST_STYLE.add('SPAN',(0,1),(0,min(ligneMat-1,22)))
			# fin matière
			totalColleur += totalmatiere
		# fin classe
		t=Table(data,colWidths=[2.5*largeurcel,2.5*largeurcel,2.5*largeurcel,2.5*largeurcel] if parmois else [4*largeurcel,4*largeurcel,2*largeurcel] ,rowHeights=min((1+nbKolleurs),23)*[hauteurcel])
		t.setStyle(LIST_STYLE)
		w,h=t.wrapOn(pdf,0,0)
		t.drawOn(pdf,(pdf.format[0]-w)/2,pdf.y-h-hauteurcel/2)
		pdf.finDePage()
	pdf.save()
	fichier = pdf.buffer.getvalue()
	pdf.buffer.close()
	response.write(fichier)
	return response

