from django.shortcuts import HttpResponse, get_object_or_404
from django.http import HttpResponseForbidden, Http404
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from accueil.models import Note, Programme, Colle, Message, Destinataire, Creneau, Semaine, Groupe, Matiere, Classe, Eleve
from django.utils import timezone
import json
from datetime import date, datetime, time, timedelta
from django.db.models import Count


def date_serial(obj):
    """convertit les dates en timestamp en vue d'une mise à plat au format json"""
    if isinstance(obj, datetime):
        return int(obj.timestamp())
    if isinstance(obj, date):
        return int(datetime.combine(obj,time(0,0)).replace(tzinfo=timezone.utc).timestamp())
    
    raise TypeError("Type not serializable")


def check(request):
    """renvoie la chaîne de caractère 'success'
    pour indiquer à l'app mobile que le serveur fonctionne"""
    return HttpResponse("success")


def checkeleve(user):
    """renvoie une erreur 403 si l'utilisateur n'est pas un élève connecté, avec une classe"""
    if not user.is_authenticated():
        return False
    if not user.is_active:
        return False
    if not user.eleve:
        return False
    if not user.eleve.classe:
        return False
    return True

def checkcolleur(user):
    """renvoie une erreur 403 si l'utilisateur n'est pas un élève connecté, avec une classe"""
    if not user.is_authenticated():
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
                                                'group': "" if user.eleve.groupe is None else user.eleve.groupe.nom}))
            if user.colleur is not None:
                login(request, user)
                matieres = user.colleur.matieres.order_by('pk')
                classes = user.colleur.classes.order_by('pk')
                return HttpResponse(json.dumps({'name': user.first_name.title() + " " + user.last_name.upper(),
                                                'colleur_id': user.colleur.pk,
                                                'classes_id': "__".join([str(classe.pk) for classe in classes]),
                                                'classes_name': "__".join([classe.nom for classe in classes]),
                                                'subjects_id': "__".join([str(matiere.pk) for matiere in matieres]),
                                                'subjects_name': "__".join([str(matiere) for matiere in matieres]),
                                                'subjects_color': "__".join([matiere.couleur for matiere in matieres])})) 
        return HttpResponse("invalide")
    else:
        return HttpResponseForbidden("access denied")


# ------------------------- PARTIE MIXTE ----------------------------

def agenda(request):
    """renvoie l'agenda des colles de l'utilisateur connecté au format json"""
    user = request.user
    if checkeleve(user):
        agendas = Colle.objects.agendaEleve(user.eleve, False)
        return HttpResponse(json.dumps([{'time': int(datetime.combine(agenda['jour'], time(agenda['heure'] // 4, 15 * (agenda['heure'] % 4))).replace(tzinfo=timezone.utc).timestamp()),
                                         'room':agenda['salle'],
                                         'week':agenda['numero'],
                                         'subject':agenda['nom_matiere'],
                                         'color':agenda['couleur'],
                                         'colleur':agenda['prenom'].title() + " " + agenda['nom'].upper(),
                                         'program':agenda['titre'],
                                         'file':agenda['fichier']} for agenda in agendas]))
    if checkcolleur(user):
        return HttpResponse(json.dumps(Colle.objects.agenda(user.colleur,False), default=date_serial))
    return HttpResponseForbidden("not authenticated")

# ------------------------- PARTIE ELEVES ----------------------------

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

def programs(request):
    """renvoie les programmes de l'utilisateur connecté au format json"""
    user = request.user
    if not checkeleve(user):
        return HttpResponseForbidden("not authenticated")
    programmes = Programme.objects.filter(classe=user.eleve.classe).values(
        'matiere__couleur', 'matiere__nom', 'semaine__numero', 'semaine__lundi', 'titre', 'fichier', 'detail').order_by('-semaine__lundi', 'matiere__nom')
    return HttpResponse(json.dumps(list(programmes), default=date_serial))

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
    return HttpResponse(json.dumps(messagesrecus, default=date_serial))


def sentmessages(request):
    """renvoie les messages envoyés par l'utilisateur connecté au format json"""
    user = request.user
    if not checkeleve(user) and not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    messagesenvoyesQuery = Message.objects.filter(auteur=user, hasAuteur=True).distinct().values(
        'date', 'auteur__first_name', 'auteur__last_name', 'luPar', 'listedestinataires', 'titre', 'corps', 'pk').order_by('-date')

    messagesenvoyes = [{'pk':x['pk'],
            'date':x['date'],
            'author':x['auteur__first_name'].title()+" "+x['auteur__last_name'].upper(),
            'readBy':x['luPar'],
            'recipients':x['listedestinataires'],
            'title':x['titre'],
            'body':x['corps']} for x in messagesenvoyesQuery]
    return HttpResponse(json.dumps(list(messagesenvoyes), default=date_serial))


def readmessage(request, message_id):
    """marque comme lu le message d'ont l'identifiant est message_id"""
    user = request.user
    if not checkeleve(user) and not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    destinataire = get_object_or_404(
        Destinataire, message__pk=message_id, user=user)
    destinataire.lu = True
    destinataire.save()
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
    La réponse est envoyée à tous si la variable booléenne ansewAll vaut True, et uniquement
    à l'expéditeur du message original sinon"""
    user = request.user
    if not checkeleve(user) and not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    if request.method != 'POST' or 'body' not in request.POST or 'title' not in request.POST:
        raise Http404
    message = get_object_or_404(Message, pk=message_id, messagerecu__user=user)
    userdestinataire = get_object_or_404(
        Destinataire, user=user, message=message)
    if userdestinataire.reponses and user.eleve is not None:
        return HttpResponseForbidden("already answered")
    listedestinataires = message.auteur.first_name.title() + " " + \
        message.auteur.last_name.upper()
    reponse = Message(auteur=user, titre=request.POST['title'], corps=request.POST[
                      'body'], listedestinataires=listedestinataires)
    reponse.save()
    destinataire = Destinataire(
        message=reponse, user=message.auteur, reponses=0)
    destinataire.save()
    userdestinataire.reponses += 1
    userdestinataire.save()
    if answerAll == '1':
        for destinataireUser in message.messagerecu.all():
            if destinataireUser.user != user:
                destinataire = Destinataire(
                    message=reponse, user=destinataireUser.user, reponses=1)
                destinataire.save()
                listedestinataires += "; " + destinataireUser.user.first_name.title() + " " + \
                    destinataireUser.user.last_name.upper()
        reponse.listedestinataires = listedestinataires
        reponse.save()
    return HttpResponse(json.dumps({'pk': reponse.pk, 'date': int(reponse.date.strftime(
        '%s')), 'listedestinataires': reponse.listedestinataires, 'titre': reponse.titre, 'corps': reponse.corps}))

# ------------------------- PARTIE COLLEURS ----------------------------

def colleurGrades(request):
    """renvoie les notes de l'utilisateur connecté au format json"""
    user = request.user
    if not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    return HttpResponse(json.dumps(Note.objects.listeNotesApp(user.colleur)
        , default=date_serial))

def colleurPrograms(request):
    """renvoie les programmes de l'utilisateur connecté au format json"""
    user = request.user
    if not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    programmes = Programme.objects.filter(classe__in=user.colleur.classes.all()).values('pk',
        'matiere__pk', 'classe__pk', 'semaine__numero', 'semaine__lundi', 'titre', 'fichier', 'detail').order_by('-semaine__lundi')
    return HttpResponse(json.dumps(list(programmes), default=date_serial))

def colleurColles(request):
    """renvoie les colles des classes de l'utilisateur connecté au format json"""
    user = request.user
    if not checkcolleur(user):
        return HttpResponseForbidden("not authenticated")
    classes = user.colleur.classes.all()
    creneaux = list(Creneau.objects.filter(classe__in=classes).annotate(nb=Count(
        'colle')).filter(nb__gt=0).values_list('pk', 'classe__pk', 'jour', 'heure', 'salle'))
    semaines = list(Semaine.objects.filter(
        colle__creneau__classe__in=classes).distinct().values_list('pk', 'numero', 'lundi'))
    colles = Colle.objects.filter(creneau__classe__in=classes).values_list(
        'pk', 'creneau', 'semaine', 'groupe', 'matiere', 'colleur', 'eleve')
    colles = [[pk, creneau, semaine, groupe or 0, matiere, colleur, eleve or 0]
    for pk, creneau, semaine, groupe, matiere, colleur, eleve in colles]
    groupes = list(Groupe.objects.filter(
        classe__in=classes).values_list('pk', 'nom'))
    matieres = list(Matiere.objects.filter(
        matieresclasse__in=classes).distinct().values_list('pk', 'nom', 'couleur', 'lv'))
    eleves = []
    for classe in classes:
        eleves_classe = [[eleve[0].pk, eleve[0].user.first_name.title() + " " + eleve[0].user.last_name.upper(), eleve[1], 0 if not eleve[0].groupe else eleve[0].groupe.pk,
               0 if not eleve[0].lv1 else eleve[0].lv1.pk, 0 if not eleve[0].lv2 else eleve[0].lv2.pk, classe.pk, order] for order, eleve in enumerate(classe.loginsEleves())]
        eleves.extend(eleves_classe)
    colleurs = [[colleur.pk, colleur.user.first_name.title() + " " + colleur.user.last_name.upper(), login]
                for colleur, login in classe.loginsColleurs()]
    return HttpResponse(json.dumps({'creneaux': creneaux, 'semaines': semaines, 'colles': colles,
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
        or 'comment' not in request.POST or 'subject' not in request.POST or 'classe' not in request.POST or 'pk' not in request.POST:
        raise Http404
    if request.POST['pk'] != "0":
        note = get_object_or_404(Note, pk=int(request.POST['pk']))
    else:
        note = Note()
    note.semaine = get_object_or_404(Semaine, numero = int(request.POST['week']))
    note.matiere = get_object_or_404(Matiere, pk = int(request.POST['subject']))
    note.classe = get_object_or_404(Classe, pk = int(request.POST['classe']))
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
    note.note = request.POST['grade']
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
    date_colle = int(datetime.combine(note.date_colle, time(note.heure // 4, 15 * (note.heure % 4))).replace(tzinfo=timezone.utc).timestamp())
    return HttpResponse(json.dumps({'pk': note.pk, 'program': program, 'date': date_colle}, default=date_serial))
