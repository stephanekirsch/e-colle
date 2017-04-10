from django.shortcuts import HttpResponse, get_object_or_404
from django.http import HttpResponseForbidden, Http404
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from accueil.models import Note, Programme, Colle, Message, Destinataire, Creneau, Semaine, Groupe, Matiere
from django.utils import timezone
import json
from datetime import date, datetime, time
from django.db.models import Count


def date_serial(obj):
    """convertit les dates en timestamp en vue d'une mise à plat au format json"""
    if isinstance(obj, date):
        return int(obj.strftime('%s'))
    if isinstance(obj, datetime):
        return int(obj.replace(tzinfo=timezone.utc).strftime('%s'))
    raise TypeError("Type not serializable")


def check(request):
    """renvoie la chaîne de caractère 'success'
    pour indiquer à l'app mobile que le serveur fonctionne"""
    return HttpResponse("success")


def checkeleve(user):
    """renvoie une erreur 403 si l'utilisateur n'est pas un élève connecté, avec une classe"""
    if not user.is_authenticated():
        return HttpResponseForbidden("user not authenticated")
    if not user.is_active:
        return HttpResponseForbidden("user not activated")
    if not user.eleve:
        return HttpResponseForbidden("user not a student")
    if not user.eleve.classe:
        return HttpResponseForbidden("user has no class")


@csrf_exempt
def connect(request):
    """connecte l'élève si les identifiants sont exacts, et renvoie le cookie de session"""
    if request.method == 'POST':
        user = authenticate(username=request.POST['username'],
                            password=request.POST['password'])
        if user is not None and user.eleve is not None and user.eleve.classe is not None:
            login(request, user)
            classe = user.eleve.classe
            return HttpResponse(json.dumps({'firstname': user.first_name,
                                            'lastname': user.last_name,
                                            'id': user.eleve.pk,
                                            'classe_id': classe.pk,
                                            'classe_name': classe.nom,
                                            'classe_year': classe.annee,
                                            'group': user.eleve.groupe.nom}))
        return HttpResponse("invalide")
    else:
        return HttpResponseForbidden("access denied")


def grades(request):
    """renvoie les notes de l'utilisateur connecté au format json"""
    user = request.user
    checkeleve(user)
    return HttpResponse(json.dumps(
        Note.objects.noteEleve(user.eleve), default=date_serial))


def results(request):
    """renvoie les résultats de l'utilisateur connecté au format json"""
    user = request.user
    checkeleve(user)
    return HttpResponse(json.dumps(
        list(Note.objects.bilanEleve(user.eleve, False, False))))


def colles(request):
    user = request.user
    checkeleve(user)
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
    checkeleve(user)
    programmes = Programme.objects.filter(classe=user.eleve.classe).values(
        'matiere__couleur', 'matiere__nom', 'semaine__numero', 'semaine__lundi', 'titre', 'fichier', 'detail').order_by('-semaine__lundi', 'matiere__nom')
    return HttpResponse(json.dumps(list(programmes), default=date_serial))


def agenda(request):
    """renvoie l'agenda des colles de l'utilisateur connecté au format json"""
    user = request.user
    checkeleve(user)
    agendas = Colle.objects.agendaEleve(user.eleve, False)
    return HttpResponse(json.dumps([{'time': int(datetime.combine(agenda['jour'], time(agenda['heure'] // 4, 15 * (agenda['heure'] % 4))).replace(tzinfo=timezone.utc).timestamp()),
                                     'room':agenda['salle'],
                                     'subject':agenda['nom_matiere'],
                                     'color':agenda['couleur'],
                                     'firstname':agenda['prenom'],
                                     'lastname':agenda['nom'],
                                     'program':agenda['titre'],
                                     'file':agenda['fichier']} for agenda in agendas]))


def messages(request):
    """renvoie les messages reçus par l'utilisateur connecté au format json"""
    user = request.user
    checkeleve(user)
    messagesrecus = Destinataire.objects.filter(user=user).values('lu', 'reponses', 'message__pk', 'message__date',
                                                                  'message__auteur__first_name', 'message__auteur__last_name', 'message__luPar',
                                                                  'message__listedestinataires', 'message__titre', 'message__corps').order_by('-message__date')
    return HttpResponse(json.dumps(list(messagesrecus), default=date_serial))


def sentmessages(request):
    """renvoie les messages envoyés par l'utilisateur connecté au format json"""
    user = request.user
    checkeleve(user)
    messagesenvoyes = Message.objects.filter(auteur=user, hasAuteur=True).distinct().values(
        'date', 'auteur__first_name', 'auteur__last_name', 'luPar', 'listedestinataires', 'titre', 'corps', 'pk').order_by('-date')
    return HttpResponse(json.dumps(list(messagesenvoyes), default=date_serial))


def readmessage(request, message_id):
    """marque comme lu le message d'ont l'identifiant est message_id"""
    user = request.user
    checkeleve(user)
    destinataire = get_object_or_404(
        Destinataire, message__pk=message_id, user=user)
    destinataire.lu = True
    destinataire.save()
    return HttpResponse("read")


def deletemessage(request, message_id):
    """marque comme effacé le message d'ont l'identifiant est message_id"""
    user = request.user
    checkeleve(user)
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
    à l'expéditeur du message priginal sinon"""
    user = request.user
    checkeleve(user)
    if request.method != 'POST' or 'body' not in request.POST or 'title' not in request.POST:
        raise Http404
    message = get_object_or_404(Message, pk=message_id, messagerecu__user=user)
    userdestinataire = get_object_or_404(
        Destinataire, user=user, message=message)
    if userdestinataire.reponses:
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
