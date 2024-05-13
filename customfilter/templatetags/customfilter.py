#-*- coding: utf-8 -*-
from django import template
from datetime import timedelta, date
from accueil.models import Classe, Config, Destinataire, Matiere, Information
from ecolle.settings import DEFAULT_CSS, GESTION_ADMIN_BDD, MEDIA_URL

register = template.Library()

@register.filter
def media(url):
    return MEDIA_URL + url

@register.filter
def nometab(d):
	return Config.objects.get_config().nom_etablissement

@register.filter
def fromiso(d):
    return date.fromisoformat(d).strftime("%d/%m/%Y")

@register.filter
def lookup(d,key):
    try:
        return d[key]
    except Exception:
        return ""

@register.filter
def integer(n):
    return int(n)

@register.filter
def addtime(temps, ajout):
    return temps+timedelta(days=ajout)

@register.filter
def heurecolle(temps):
	temps = temps or 0 # car une somme sur un ensemble vide peut renvoyer None
	return "{}h{:02d}".format(temps//60,temps%60)

@register.filter
def heure(heure):
	return "{}h{:02d}".format(heure//60,(heure%60))

@register.filter
def get_matiere(matiere_id):
    if Matiere.objects.filter(pk=matiere_id).exists():
        return Matiere.objects.get(pk=matiere_id)

@register.filter
def image(fichier):
    return fichier.replace('programme','image').replace('pdf','jpg')

@register.filter
def tzip(l1, l2):
    return zip(l1,l2)

@register.simple_tag
def get_admin_bdd():
    return GESTION_ADMIN_BDD

@register.simple_tag
def get_info():
    infos = Information.objects.filter(destinataire=3).order_by('-date')
    return "<br />".join(["[{}/{}]<br />{}".format(info.date.strftime("%A %d %B %Y"),"Administrateur" if info.expediteur == 1 else "Secrétariat",info.message) for info in infos])

@register.simple_tag
def get_mathjax():
    return Config.objects.get_config().mathjax

@register.simple_tag
def get_app_mobile():
    return Config.objects.get_config().app_mobile

@register.simple_tag
def get_ects():
    return Config.objects.get_config().ects

@register.simple_tag
def get_modifgroupe():
    return Config.objects.get_config().modif_secret_groupe

@register.simple_tag
def get_classes():
    return Classe.objects.all()


@register.simple_tag
def get_css():
    return 'css/' + DEFAULT_CSS

@register.filter
def titer(obj):
    return iter(obj)

@register.filter
def tnext(iterable):
    try:
        return next(iterable)
    except Exception:
        return None

@register.filter
def hasMatiere(l,matiere_pk):
    try:
        return any(x == matiere_pk for x,y in l)
    except Exception:
        return False

@register.filter
def getLu(message,user):
    if message.auteur == user:
        return True, False
    else:
        return Destinataire.objects.filter(message=message,user=user).values_list("lu",flat=True).first(), True

@register.filter
def option(matiere,classe):
    if matiere.lv == 0 and (classe.option1 == matiere or classe.option2 == matiere):
        return "{} ({}min/opt))".format(matiere.nom.title(), matiere.temps)
    return str(matiere)