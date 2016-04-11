#-*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from . import views

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
url(r'^action/ramassage/pdf/(\d+)$', views.ramassagePdf, name="ramassagepdf")
]