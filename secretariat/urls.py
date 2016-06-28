#-*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from . import views
from ecolle.settings import ECTS

urlpatterns = [
url(r'^$', views.connec, name="login_secret"),
url(r'^action$', views.action, name="action_secret"),
url(r'^action/resultats$', views.resultats, name="resultats_secret"),
url(r'^action/resultatcsv/(\d+)/(\d+)/(\d+)/(\d+)$', views.resultatcsv, name="resultatcsv_secret"),
url(r'^action/colloscope/(\d+)$', views.colloscope, name="colloscope_secret"),
url(r'^action/colloscope/(\d+)/(\d+)/(\d+)$', views.colloscope2, name="colloscope2_secret"),
url(r'^action/colloscopepdf/(\d+)/(\d+)/(\d+)$', views.colloscopePdf, name="colloscopepdf_secret"),
url(r'^action/recapitulatif$', views.recapitulatif, name="recapitulatif"),
url(r'^action/ramassage$', views.ramassage, name="ramassage"),
url(r'^action/ramassage/suppr/(\d+)$', views.ramassageSuppr, name="ramassagesuppr"),
url(r'^action/ramassage/pdf/(\d+)$', views.ramassagePdf, name="ramassagepdf")]

if ECTS: # si les crédits activés, on ajoute les urls pour les ECTS
	urlpatterns.extend([url(r'^action/ects/credits/(\d+)$', views.ectscredits,name="secret_ects_credits"),
	url(r'^action/ects/fiche/(\d+)$', views.ficheectspdf,name="secret_ects_fiche"),
	url(r'^action/ects/attestation/(\d+)$', views.attestationectspdf,name="secret_ects_attestation"),
	url(r'^action/ects/fiche/classe/(\d+)$', views.ficheectsclassepdf,name="secret_ects_fiche_classe"),
	url(r'^action/ects/attestation/classe/(\d+)$', views.attestationectsclassepdf,name="secret_ects_attestation_classe")])