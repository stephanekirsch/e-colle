from django.shortcuts import HttpResponse
from django.http import HttpResponseForbidden
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from accueil.models import Note, Programme, Colle
# from accueil.forms import ConnexionForm
import json
from datetime import date, datetime, time, timezone


def date_serial(obj):
    if isinstance(obj, date):
        return 1000*int(obj.strftime('%s'))
    raise TypeError ("Type not serializable")

def check(request):
    """renvoie la chaîne de caractère 'success'
    pour indiquer à l'app mobile que le serveur fonctionne"""
    return HttpResponse("success")


@csrf_exempt
def connect(request):
    if request.method == 'POST':
        user = authenticate(username=request.POST['username'],
                            password=request.POST['password'])
        if user is not None and user.eleve is not None and user.eleve.classe is not None:
            login(request, user)
            classe = user.eleve.classe
            return HttpResponse(json.dumps({'firstname':user.first_name,
                                            'lastname':user.last_name,
                                            'id':user.eleve.pk,
                                            'classe_id':classe.pk,
                                            'classe_name':classe.nom,
                                            'classe_year':classe.annee,
                                            'group':user.eleve.groupe.nom}))
        return HttpResponse("invalide")
    else:
        return HttpResponseForbidden("access denied")



def grades(request):
    user = request.user
    if not user.is_authenticated():
        return HttpResponseForbidden("user not authenticated")
    if  not user.is_active:
        return HttpResponseForbidden("user not activated")
    if not user.eleve:
        return HttpResponseForbidden("user not a student")
    return HttpResponse(json.dumps(Note.objects.noteEleve(user.eleve),default=date_serial))

def results(request):
    user = request.user
    if not user.is_authenticated():
        return HttpResponseForbidden("user not authenticated")
    if  not user.is_active:
        return HttpResponseForbidden("user not activated")
    if not user.eleve:
        return HttpResponseForbidden("user not a student")
    return HttpResponse(json.dumps(list(Note.objects.bilanEleve(user.eleve,False,False))))

def programs(request):
    user = request.user
    if not user.is_authenticated():
        return HttpResponseForbidden("user not authenticated")
    if  not user.is_active:
        return HttpResponseForbidden("user not activated")
    if not user.eleve:
        return HttpResponseForbidden("user not a student")
    if not user.eleve.classe:
        return HttpResponseForbidden("user has no class")
    programmes = Programme.objects.filter(classe=user.eleve.classe).values('matiere__couleur','matiere__nom','semaine__numero','semaine__lundi','titre','fichier','detail').order_by('-semaine__lundi','matiere__nom')
    return HttpResponse(json.dumps(list(programmes),default=date_serial))

def agenda(request):
    user = request.user
    if not user.is_authenticated():
        return HttpResponseForbidden("user not authenticated")
    if  not user.is_active:
        return HttpResponseForbidden("user not activated")
    if not user.eleve:
        return HttpResponseForbidden("user not a student")
    if not user.eleve.classe:
        return HttpResponseForbidden("user has no class")
    agendas =Colle.objects.agendaEleve(user.eleve,False)
    return HttpResponse(json.dumps([ {'time':int(datetime.combine(agenda['jour'],time(agenda['heure']//4,15*(agenda['heure']%4))).replace(tzinfo=timezone.utc).timestamp()),
        'room':agenda['salle'],
        'subject':agenda['nom_matiere'],
        'color':agenda['couleur'],
        'firstname':agenda['prenom'],
        'lastname':agenda['nom'],
        'program':agenda['titre'],
        'file':agenda['fichier']}  for agenda in agendas]))