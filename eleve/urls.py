#-*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
url(r'^$', views.connec,name="login_eleve"),
url(r'^action$', views.action,name="action_eleve"),
url(r'^action/bilan$', views.bilan,name="bilan_eleve"),
url(r'^action/note$', views.note,name="note_eleve"),
url(r'^action/programme$', views.programme,name="programme_eleve"),
url(r'^action/colloscope$', views.colloscope,name="colloscope_eleve"),
url(r'^action/colloscope/pdf/(\d+)/(\d+)$', views.colloscopePdf,name="colloscopepdf_eleve"),
url(r'^action/agenda$', views.agenda,name="agenda_eleve"),
]