from django.shortcuts import HttpResponse, get_object_or_404
from django.http import HttpResponseForbidden, Http404
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from accueil.models import Config, Note, Programme, Colle, Message, Destinataire, Creneau, Semaine, Groupe, Matiere, Classe, Eleve, User, Prof, Colleur
from django.utils import timezone
import json
from datetime import date, datetime, time, timedelta
from django.db.models import Count
from ecolle.settings import HEURE_DEBUT, HEURE_FIN, INTERVALLE


def date_serial(obj):
    """convertit les dates en timestamp en vue d'une mise à plat au format json"""
    if isinstance(obj, datetime):
        return int(obj.timestamp())
    if isinstance(obj, date):
        return int(datetime.combine(obj,time(0,0)).replace(tzinfo=timezone.utc).timestamp())
    
    raise TypeError("Type not serializable")


def check(request):
    """renvoie la version de e-colle 
    pour indiquer à l'app mobile que le serveur fonctionne"""
    config = Config.objects.get_config()
    if not config.app_mobile:
        raise Http404
    return HttpResponse("{}::{}".format(config.nom_etablissement,request.build_absolute_uri("/")[:-1]))


def checkeleve(user):
    """renvoie False si l'utilisateur n'est pas un élève connecté, avec une classe, True sinon et lève une erreur 404
    si l'app_mobile n'est pas activée dans la configuration"""
    if not Config.objects.get_config().app_mobile:
        raise Http404
    if not user.is_authenticated:
        return False
    if not user.is_active:
        return False
    if not user.eleve:
        return False
    if not user.eleve.classe:
        return False
    return True

def checkcolleur(user):
    """renvoie False si l'utilisateur n'est pas un colleur connecté, True sinon et lève une erreur 404
    si l'app_mobile n'est pas activée dans la configuration"""
    if not Config.objects.get_config().app_mobile:
        raise Http404
    if not user.is_authenticated:
        return False
    if not user.is_active:
        return False
    if not user.colleur:
        return False
    return True


@csrf_exempt
def connect(request):
    """connecte l'élève/le colleur si les identifiants sont exacts, et renvoie le cookie de session
    ainsi que certaines données de l'utilisateur"""
    if not Config.objects.get_config().app_mobile:
        raise Http404
    if request.method == 'POST':
        user = authenticate(username=request.POST['username'],
                            password=request.POST['password'])
        if user is not None:
            if user.eleve is not None and user.eleve.classe is not None:
                login(request, user)
                classe = user.eleve.classe
                return HttpResponse(json.dumps({'name': user.first_name.title() + " " + user.last_name.upper(),
                                                'student_id': user.eleve.pk,
                                                'classe_id': classe.pk,
                                                'classe_name': classe.nom,
                                                'classe_year': classe.annee,
                                                'group': "" if user.eleve.groupe is None else user.eleve.groupe.nom,
                                                'version': "2.1",
                                                'compose': Config.objects.get_config().message_eleves,
                                                'heure_debut': HEURE_DEBUT,
                                                'heure_fin': HEURE_FIN,
                                                'intervalle': INTERVALLE}))
            if user.colleur is not None and user.is_active:
                login(request, user)
                matieres = user.colleur.matieres.order_by('pk')
                classes = user.colleur.classes.order_by('pk')
                return HttpResponse(json.dumps({'name': user.first_name.title() + " " + user.last_name.upper(),
                                                'colleur_id': user.colleur.pk,
                                                'classes_id': "__".join([str(classe.pk) for classe in classes]),
                                                'classes_name': "__".join([classe.nom for classe in classes]),
                                                'subjects_id': "__".join([str(matiere.pk) for matiere in matieres]),
                                                'subjects_name': "__".join([str(matiere) for matiere in matieres]),
                                                'subjects_color': "__".join([matiere.couleur for matiere in matieres]),
                                                'version': "2.1",
                                                'heure_debut': HEURE_DEBUT,
                                                'heure_fin': HEURE_FIN,
                                                'intervalle': INTERVALLE}))
        return HttpResponse("invalide")
    else:
        return HttpResponseForbidden("access denied")

# ------------------------- PARTIE ELEVES ----------------------------

def agendaprograms(request):
    """renvoie l'agenda des colles de l'utilisateur connecté au format json"""
    user = request.user
    if not checkeleve(user):
        return HttpResponseForbidden("not authenticated")
    agendas = Colle.objects.agendaEleveApp(user.eleve)
    programmes = Programme.objects.filter(classe=user.eleve.classe).values('pk',
        'matiere__couleur', 'matiere__nom', 'semaine__numero', 'semaine__lundi', 'titre', 'fichier', 'detail').order_by('-semaine__lundi', 'matiere__nom')

    return HttpResponse(json.dumps({'agendas': agendas, 'programs': list(programmes)}, default=date_serial))

def grades(request):
    """renvoie les notes de l'utilisateur connecté au format json"""
    user = request.user
    if not checkeleve(user):
        return HttpResponseForbidden("not authenticated")
    return HttpResponse(json.dumps([{'subject':x['nom_matiere'].title(),
        'color':x['couleur'],
        'date':x['date_colle'],
        'colleur':x['prenom'].title()+" "+x['nom'].upper(),
        'title':x['titre'],
        'program':x['programme'],
        'grade':x['note'],
        'comment':x['commentaire']} for x in Note.objects.noteEleve(user.eleve)]
        , default=date_serial))

def results(request):
    """renvoie les résultats de l'utilisateur connecté au format json"""
    user = request.user
    if not checkeleve(user):
        return HttpResponseForbidden("not authenticated")
    return HttpResponse(json.dumps(
        list(Note.objects.bilanEleve(user.eleve, False, False))))


def colles(request):
    user = request.user
    if not checkeleve(user):
        return HttpResponseForbidden("not authenticated")
    classe = user.eleve.classe
    creneaux = list(Creneau.objects.filter(classe=classe).annotate(nb=Count(
        'colle')).filter(nb__gt=0).values_list('pk', 'jour', 'heure', 'salle'))
    semaines = list(Semaine.objects.filter(
        colle__creneau__classe=classe).distinct().values_list('pk', 'numero', 'lundi'))
    colles = Colle.objects.filter(creneau__classe=classe).values_list(
        'pk', 'creneau', 'semaine', 'groupe', 'matiere', 'colleur', 'eleve')
    colles = [[pk, creneau, semaine, groupe or 0, matiere, colleur, eleve or 0]
    for pk, creneau, semaine, groupe, matiere, colleur, eleve in colles]
    groupes = list(Groupe.objects.filter(
        classe=classe).values_list('pk', 'nom'))
    matieres = list(Matiere.objects.filter(
        matieresclasse=classe).values_list('pk', 'nom', 'couleur', 'lv'))
    eleves = [[eleve.pk, eleve.user.first_name.title() + " " + eleve.user.last_name.upper(), login, 0 if not eleve.groupe else eleve.groupe.pk,
               0 if not eleve.lv1 else eleve.lv1.pk, 0 if not eleve.lv2 else eleve.lv2.pk] for eleve, login in classe.loginsEleves()]
    colleurs = [[colleur.pk, colleur.user.first_name.title() + " " + colleur.user.last_name.upper(), login]
                for colleur, login in classe.loginsColleurs()]
    return HttpResponse(json.dumps({'creneaux': creneaux, 'semaines': semaines, 'colles': colles,
                                    'groupes': groupes, 'matieres': matieres, 'eleves': eleves, 'colleurs': colleurs}, default=date_serial))

# ------------------------- PARTIE MESSAGES ----------------------------

def messages(request):
    """renvoie les messages reçus par l'utilisateur connecté au format json"""
    user = request.user
    if not checkeleve(user) and not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    messagesrecusQuery = Destinataire.objects.filter(user=user).values('lu', 'reponses', 'message__pk', 'message__date',
                                                                  'message__auteur__first_name', 'message__auteur__last_name', 'message__luPar',
                                                                  'message__listedestinataires', 'message__titre', 'message__corps').order_by('-message__date')
    messagesrecus = [{'read':x['lu'],
            'answers':x['reponses'],
            'pk':x['message__pk'],
            'date':x['message__date'],
            'author':x['message__auteur__first_name'].title()+" "+x['message__auteur__last_name'].upper(),
            'readBy':x['message__luPar'],
            'recipients':x['message__listedestinataires'],
            'title':x['message__titre'],
            'body':x['message__corps']} for x in messagesrecusQuery]
    messagesenvoyesQuery = Message.objects.filter(auteur=user, hasAuteur=True).distinct().values(
        'date', 'auteur__first_name', 'auteur__last_name', 'luPar', 'listedestinataires', 'titre', 'corps', 'pk').order_by('-date')
    messagesenvoyes = [{'pk':x['pk'],
            'date':x['date'],
            'author':x['auteur__first_name'].title()+" "+x['auteur__last_name'].upper(),
            'readBy':x['luPar'],
            'recipients':x['listedestinataires'],
            'title':x['titre'],
            'body':x['corps']} for x in messagesenvoyesQuery]
    return HttpResponse(json.dumps({'messagesrecus':messagesrecus, 'messagesenvoyes': messagesenvoyes}, default=date_serial))

def readmessage(request, message_id):
    """marque comme lu le message d'ont l'identifiant est message_id"""
    user = request.user
    if not checkeleve(user) and not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    destinataire = get_object_or_404(
        Destinataire, message__pk=message_id, user=user)
    message = get_object_or_404(Message, pk = message_id)
    if not destinataire.lu:
        destinataire.lu = True
        destinataire.save()
        message.luPar += "{} {};".format(user.first_name.title(),user.last_name.upper())
        message.save()
    return HttpResponse("read")


def deletemessage(request, message_id):
    """marque comme effacé le message d'ont l'identifiant est message_id"""
    user = request.user
    if not checkeleve(user) and not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    message = get_object_or_404(Message, pk=message_id)
    if message.hasAuteur and message.auteur == user:
        if not message.messagerecu.all().count():
            message.delete()
        else:
            message.hasAuteur = False
            message.save()
    else:
        destinataire = get_object_or_404(
            Destinataire, message=message, user=user)
        destinataire.delete()
        if not message.hasAuteur and not message.messagerecu.all().count():
            message.delete()
    return HttpResponse("deleted")


@csrf_exempt
def answer(request, message_id, answerAll):
    """répond au message dont l'identifiant est message_id, avec les champs POST title et body.
    La réponse est envoyée à tous si la variable booléenne answerAll vaut True, et uniquement
    à l'expéditeur du message original sinon"""
    user = request.user
    if not checkeleve(user) and not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    if request.method != 'POST' or 'body' not in request.POST or 'title' not in request.POST:
        raise Http404
    message = get_object_or_404(Message, pk=message_id, messagerecu__user=user)
    userdestinataire = get_object_or_404(
        Destinataire, user=user, message=message)
    if userdestinataire.reponses and user.eleve is not None and not Config.objects.get_config().message_eleves:
        return HttpResponseForbidden("already answered")
    listedestinataires = message.auteur.first_name.title() + " " + \
        message.auteur.last_name.upper()
    reponse = Message(auteur=user, titre=request.POST['title'], corps=request.POST[
                      'body'], listedestinataires=listedestinataires)
    reponse.save()
    destinataire = Destinataire(
        message=reponse, user=message.auteur)
    destinataire.save()
    userdestinataire.reponses += 1
    userdestinataire.save()
    if answerAll == '1':
        for destinataireUser in message.messagerecu.all():
            if destinataireUser.user != user:
                destinataire = Destinataire(
                    message=reponse, user=destinataireUser.user, reponses=0)
                destinataire.save()
                listedestinataires += "; " + destinataireUser.user.first_name.title() + " " + \
                    destinataireUser.user.last_name.upper()
        reponse.listedestinataires = listedestinataires
        reponse.save()
    return HttpResponse(json.dumps({'pk': reponse.pk, 'date': int(reponse.date.strftime(
        '%s')), 'listedestinataires': reponse.listedestinataires, 'titre': reponse.titre, 'corps': reponse.corps}))

# ------------------------- PARTIE COLLEURS ----------------------------

def colleurDonnees(request):
    """renvoie les colles des classes de l'utilisateur connecté au format json"""
    user = request.user
    if not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    classes = user.colleur.classes.all()
    colleurclasses = Colleur.objects.listeColleurClasse(user.colleur)
    colleurmatieres = Colleur.objects.listeColleurMatiere(user.colleur)
    creneaux = list(Creneau.objects.filter(classe__in=classes).annotate(nb=Count(
        'colle')).filter(nb__gt=0).values_list('pk', 'classe__pk', 'jour', 'heure', 'salle'))
    semaines = list(Semaine.objects.values_list('pk', 'numero', 'lundi'))
    colles = Colle.objects.filter(creneau__classe__in=classes).values_list(
        'pk', 'creneau', 'semaine', 'groupe', 'matiere', 'colleur', 'eleve')
    colles = [[pk, creneau, semaine, groupe or 0, matiere, colleur, eleve or 0]
    for pk, creneau, semaine, groupe, matiere, colleur, eleve in colles]
    groupes = list(Groupe.objects.filter(
        classe__in=classes).values_list('pk', 'nom','classe__pk'))
    matieres = list(Matiere.objects.filter(
        matieresclasse__in=classes).distinct().values_list('pk', 'nom', 'couleur', 'lv'))
    eleves = []
    for classe in classes:
        eleves_classe = [[eleve[0].pk, eleve[0].user.first_name.title() + " " + eleve[0].user.last_name.upper(), eleve[1], 0 if not eleve[0].groupe else eleve[0].groupe.pk,
               0 if not eleve[0].lv1 else eleve[0].lv1.pk, 0 if not eleve[0].lv2 else eleve[0].lv2.pk, classe.pk, order] for order, eleve in enumerate(classe.loginsEleves())]
        eleves.extend(eleves_classe)
    colleurs = [[colleur[0].pk, colleur[0].user.first_name.title() + " " + colleur[0].user.last_name.upper(), colleur[1], order]
                for order, colleur in enumerate(classe.loginsColleurs(colleur = user.colleur))]
    pp = Classe.objects.filter(profprincipal = user.colleur)
    profs = Prof.objects.filter(classe__in = user.colleur.classes.all(), matiere__in = user.colleur.matieres.all()).values_list('colleur__pk','classe__pk','matiere__pk')
    profspp = Prof.objects.filter(classe__in = pp).values_list('colleur__pk','classe__pk','matiere__pk')

    return HttpResponse(json.dumps({'colleurmatieres': colleurmatieres, 'colleurclasses': colleurclasses,'classes': list(classes.values_list('id','nom')),'pp': list(pp.values_list('id')), 'profs': list(profs | profspp), 'notes': Note.objects.listeNotesApp(user.colleur),
        'programmes': list(Programme.objects.filter(classe__in=user.colleur.classes.all()).order_by('-semaine__lundi').values_list('matiere__pk',
        'classe__pk', 'semaine__numero', 'semaine__lundi', 'titre', 'detail', 'fichier')), 'creneaux': creneaux, 'semaines': semaines, 'colles': colles,
                                    'groupes': groupes, 'matieres': matieres, 'eleves': eleves, 'colleurs': colleurs}, default=date_serial))

def deletegrade(request, note_id):
    """efface la note dont l'identifiant est note_id"""
    user = request.user
    if not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    note = get_object_or_404(Note, pk=note_id)
    if note.colleur != user.colleur:
        return HttpResponseForbidden("not your grade")
    note.delete()
    return HttpResponse("deleted")

@csrf_exempt
def addsinglegrade(request):
    """ajoute une note dans la base de donnée"""
    user = request.user
    if not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    if request.method != 'POST' or 'week' not in request.POST or 'day' not in request.POST or 'hour' not in request.POST \
        or 'student' not in request.POST or 'catchup' not in request.POST or 'date' not in request.POST or 'grade' not in request.POST \
        or 'comment' not in request.POST or 'subject' not in request.POST or 'classe' not in request.POST or 'pk' not in request.POST \
        or 'draft_id' not in request.POST:
        raise Http404
    if request.POST['pk'] != "0":
        note = get_object_or_404(Note, pk=int(request.POST['pk']))
    elif request.POST['draft_id'] != "0":
        try:
            note = Note.objects.get(pk=int(request.POST['draft_id']))
        except Exception:
            note = Note()
    else:
        note = Note()
    note.semaine = get_object_or_404(Semaine, numero = int(request.POST['week']))
    note.matiere = get_object_or_404(Matiere, pk = int(request.POST['subject']))
    note.classe = get_object_or_404(Classe, pk = int(request.POST['classe']))
    if note.classe not in user.colleur.classes.all():
        return HttpResponse("vous ne collez pas dans cette classe")
    if note.matiere not in user.colleur.matieres.all():
        return HttpResponse("vous ne collez pas dans cette matière")
    note.jour = int(request.POST['day'])
    note.heure = int(request.POST['hour'])
    note.colleur = user.colleur
    note.note = request.POST['grade']
    if request.POST['student'] == "0":
        note.eleve = None
        note.note = 21
    else:
        note.eleve = get_object_or_404(Eleve, pk=request.POST['student'])
    note.rattrapee = False if request.POST['catchup'] == "false" else True
    if not note.rattrapee:
        note.date_colle = note.semaine.lundi + timedelta(days = note.jour)
    else:
        note.date_colle = datetime.utcfromtimestamp(int(request.POST['date']))
    note.commentaire = request.POST['comment']
    nbNotesColleur=Note.objects.filter(date_colle=note.date_colle,colleur=note.colleur,heure=note.heure)
    if note.pk:
        nbNotesColleur = nbNotesColleur.exclude(pk=note.pk)
    nbNotesColleur = nbNotesColleur.count()
    if nbNotesColleur >= 3:
        return HttpResponse("Vous avez plus de 3 notes sur ce créneau")
    nbNotesEleve=Note.objects.filter(semaine=note.semaine,matiere=note.matiere,colleur=user.colleur,eleve=note.eleve).count()
    if nbNotesEleve !=0 and note.eleve is not None and not note.pk:
        return HttpResponse('Vous avez déjà collé cet élève dans cette matière cette semaine')
    note.save()
    try:
        program = Programme.objects.get(classe = note.classe, semaine = note.semaine, matiere = note.matiere).titre
    except Exception:
        program = ""
    date_colle = int(datetime.combine(note.date_colle, time(note.heure // 60, note.heure % 60)).replace(tzinfo=timezone.utc).timestamp())
    return HttpResponse(json.dumps({'pk': note.pk, 'program': program, 'date': date_colle}, default=date_serial))

@csrf_exempt
def addgroupgrades(request):
    """ajoute les notes d'un groupe dans la base de donnée"""
    user = request.user
    if not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    if request.method != 'POST' or 'week' not in request.POST or 'day' not in request.POST or 'hour' not in request.POST \
        or 'catchup' not in request.POST or 'date' not in request.POST or 'grade1' not in request.POST \
        or 'comment1' not in request.POST or 'grade2' not in request.POST or 'grade3' not in request.POST or 'subject' not in request.POST\
        or 'comment2' not in request.POST or 'comment3' not in request.POST or 'classe' not in request.POST\
        or 'student1' not in request.POST or 'student2' not in request.POST or 'student3' not in request.POST:
        raise Http404
    note1, note2, note3 = Note(), Note(), Note()
    note1.semaine = note2.semaine = note3.semaine = get_object_or_404(Semaine, numero = int(request.POST['week']))
    note1.matiere = note2.matiere = note3.matiere = get_object_or_404(Matiere, pk = int(request.POST['subject']))
    note1.classe = note2.classe = note3.classe = get_object_or_404(Classe, pk = int(request.POST['classe']))
    if note1.classe not in user.colleur.classes.all():
        return HttpResponse("vous ne collez pas dans cette classe")
    if note1.matiere not in user.colleur.matieres.all():
        return HttpResponse("vous ne collez pas dans cette matière")
    note1.jour = note2.jour = note3.jour = int(request.POST['day'])
    note1.heure = note2.heure = note3.heure = int(request.POST['hour'])
    note1.colleur = note2.colleur = note3.colleur = user.colleur
    note1.rattrapee = note2.rattrapee = note3.rattrapee = False if request.POST['catchup'] == "false" else True
    if not note1.rattrapee:
        note1.date_colle = note2.date_colle = note3.date_colle = note1.semaine.lundi + timedelta(days = note1.jour)
    else:
        note1.date_colle = note2.date_colle = note3.date_colle = datetime.utcfromtimestamp(int(request.POST['date']))
    note1.note = int(request.POST['grade1'])
    note2.note = int(request.POST['grade2'])
    note3.note = int(request.POST['grade3'])
    note1.eleve = None if request.POST['student1'] == "0" else get_object_or_404(Eleve, pk=request.POST['student1'])
    note2.eleve = None if request.POST['student2'] == "0" else get_object_or_404(Eleve, pk=request.POST['student2'])
    note3.eleve = None if request.POST['student3'] == "0" else get_object_or_404(Eleve, pk=request.POST['student3'])
    if note1.eleve is None and note1.note != -1:
        note1.note = 21
    if note2.eleve is None and note2.note != -1:
        note2.note = 21
    if note3.eleve is None and note3.note != -1:
        note3.note = 21
    nbNotesColleur=Note.objects.filter(date_colle=note1.date_colle,colleur=note1.colleur,heure=note1.heure).count()
    if nbNotesColleur >= 1:
        return HttpResponse("Vous avez déjà des notes sur ce créneau")
    if note1.note != -1:
        nbNotesEleve1=Note.objects.filter(semaine=note1.semaine,matiere=note1.matiere,colleur=user.colleur,eleve=note1.eleve).count()
        if nbNotesEleve1 !=0 and note1.eleve is not None:
            return HttpResponse("Vous avez déjà collé {} dans cette matière cette semaine".format(note1.eleve))
    if note2.note != -1:
        nbNotesEleve2=Note.objects.filter(semaine=note2.semaine,matiere=note2.matiere,colleur=user.colleur,eleve=note2.eleve).count()
        if nbNotesEleve2 !=0 and note2.eleve is not None:
            return HttpResponse("Vous avez déjà collé {} dans cette matière cette semaine".format(note2.eleve))
    if note3.note != -1:
        nbNotesEleve3=Note.objects.filter(semaine=note3.semaine,matiere=note3.matiere,colleur=user.colleur,eleve=note3.eleve).count()
        if nbNotesEleve3 !=0 and note3.eleve is not None:
            return HttpResponse("Vous avez déjà collé {} dans cette matière cette semaine".format(note3.eleve))
    if note1.note != -1:
        note1.commentaire = request.POST['comment1']
        note1.save()
    if note2.note != -1:
        note2.commentaire = request.POST['comment2']
        note2.save()
    if note3.note != -1:
        note3.commentaire = request.POST['comment3']
        note3.save()
    try:
        program = Programme.objects.get(classe = note1.classe, semaine = note1.semaine, matiere = note1.matiere).titre
    except Exception:
        program = ""
    date_colle = int(datetime.combine(note1.date_colle, time(note1.heure // 60, note1.heure % 60)).replace(tzinfo=timezone.utc).timestamp())
    return HttpResponse(json.dumps({'pk1': note1.pk, 'pk2': note2.pk, 'pk3': note3.pk, 'program': program, 'date': date_colle}, default=date_serial))

@csrf_exempt
def adddraftgrades(request):
    """ajoute les brouillons de notes dans la base de donnée en insérant / mettant à jour"""
    user = request.user
    if not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    if request.method != 'POST' or 'draftCount' not in request.POST:
        raise Http404
    listeNotesRow = [] # rowid des brouillons sucessifs
    listeNotesId = [] # id des brouillons une fois sauvegardés (si ils le sont, sinon 0)
    try:
        nbNotes = int(request.POST['draftCount'])
        for i in range(nbNotes):
            rowid = int(request.POST['row{}'.format(i)])
            listeNotesRow.append(rowid)
            draft_id = int(request.POST['draft{}'.format(i)])
            if draft_id in listeNotesId: # si on a déjà enregistré un brouillon pour cette note, on n'enregistre pas le suivant
                listeNotesId.append(0)
            else: # sinon on essaie d'enregistrer la note
                if draft_id != 0:
                    try:
                        note = Note.objects.get(pk=draft_id)
                    except Exception:
                        note = Note()
                else:
                    note = Note()
                try:
                    note.semaine = Semaine.objects.get(numero = int(request.POST['week{}'.format(i)]))
                    note.matiere = Matiere.objects.get(pk = int(request.POST['subject{}'.format(i)]))
                    note.classe = Classe.objects.get(pk = int(request.POST['classe{}'.format(i)]))
                    note.jour = int(request.POST['day{}'.format(i)])
                    note.heure = int(request.POST['hour{}'.format(i)])
                    note.note = int(request.POST['grade{}'.format(i)])
                    note.rattrapee = False if request.POST['catchup{}'.format(i)] == "false" else True
                    eleve_id = int(request.POST['student{}'.format(i)])
                    note.eleve = None if eleve_id == 0 else Eleve.objects.get(pk = eleve_id)
                    date_colle = int(request.POST['date{}'.format(i)])
                except Exception:
                    listeNotesId.append(0)
                    continue
                note.colleur = user.colleur
                if note.classe not in user.colleur.classes.all() or note.matiere not in user.colleur.matieres.all():
                    listeNotesId.append(0)
                    continue
                if not note.rattrapee:
                    note.date_colle = note.semaine.lundi + timedelta(days = note.jour)
                else:
                    note.date_colle = datetime.utcfromtimestamp(date_colle)
                nbNotesColleur=Note.objects.filter(date_colle=note.date_colle,colleur=note.colleur,heure=note.heure)
                if note.pk:
                    nbNotesColleur = nbNotesColleur.exclude(pk=note.pk)
                nbNotesColleur = nbNotesColleur.count()
                if nbNotesColleur >= 3:
                    listeNotesId.append(0)
                    continue
                nbNotesEleve=Note.objects.filter(semaine=note.semaine,matiere=note.matiere,colleur=user.colleur,eleve=note.eleve).count()
                if nbNotesEleve !=0 and note.eleve is not None and not note.pk:
                    listeNotesId.append(0)
                    continue
                try:
                    note.commentaire = request.POST['comment{}'.format(i)]
                except Exception:
                    listeNotesId.append(0)
                    continue
                note.save()
                listeNotesId.append(note.pk)
    except Exception :
        raise Http404
    return HttpResponse(json.dumps([listeNotesRow,listeNotesId]))

@csrf_exempt
def addmessage(request):
    """ajoute un message envoyé par l"utilisateur"""
    user = request.user
    if not checkcolleur(user) and not (checkeleve(user) and Config.objects.get_config().message_eleves):
        return HttpResponseForbidden("not authenticated")
    if request.method != 'POST' or 'title' not in request.POST or 'body' not in request.POST or 'recipients' not in request.POST:
        raise Http404
    destinataires = set()
    try:
        destinataireList = [[int(x) for x in y.split("-")] for y in request.POST['recipients'].split("_")]
    except Exception:
        raise Http404
    for genre, pk, matiere_pk in destinataireList:
        if genre == 1: # élève
            try:
                destinataires.add(User.objects.get(eleve__pk = pk))
            except Exception:
                pass
        elif genre == 2: # colleur
            try:
                destinataires.add(User.objects.get(colleur__pk = pk))
            except Exception:
                pass
        elif genre == 3: # groupe
            try:
                destinataires |= {eleve.user for eleve in Eleve.objects.filter(groupe__pk = pk)}
            except Exception as e:
                return HttpResponse(str(e))
        elif genre == 4: # tous les élèves d'une classe
            try:
                destinataires |= {eleve.user for eleve in Eleve.objects.filter(classe__pk = pk)}
            except Exception:
                pass
        elif genre == 5: # tous les profs d'une classe
            try:
                destinataires |= {colleur.user for colleur in Colleur.objects.filter(colleurprof__classe__pk = pk)}
            except Exception:
                pass
        elif genre == 6: # tous les colleurs d'une classe et d'une matière
            try:
                destinataires |= {colleur.user for colleur in Colleur.objects.filter(classes__pk = pk, matieres__pk = matiere_pk)}
            except Exception:
                pass
    if not destinataires:
            return HttpResponse("Il faut au moins un destinataire")
    else:
        destinataires.discard(user)
        message = Message(auteur=user,listedestinataires="; ".join(["{} {}".format(destinataire.first_name.title(),destinataire.last_name.upper()) for destinataire in destinataires]),titre=request.POST['title'],corps=request.POST['body'])
        message.save()
        for personne in destinataires:
            Destinataire(user=personne,message=message).save()
    return HttpResponse(json.dumps({'pk': message.pk, 'date': int(message.date.strftime(
        '%s')), 'listedestinataires': message.listedestinataires, 'titre': message.titre, 'corps': message.corps}))
