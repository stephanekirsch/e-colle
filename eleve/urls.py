#-*- coding: utf-8 -*-
from django.urls import re_path
from . import views

urlpatterns = [
re_path(r'^$', views.connec,name="login_eleve"),
re_path(r'^action$', views.action,name="action_eleve"),
re_path(r'^action/bilan$', views.bilan,name="bilan_eleve"),
re_path(r'^action/note$', views.note,name="note_eleve"),
re_path(r'^action/programme$', views.programme,name="programme_eleve"),
re_path(r'^action/colloscope$', views.colloscope,name="colloscope_eleve"),
re_path(r'^action/colloscope/pdf/(\d+)/(\d+)$', views.colloscopePdf,name="colloscopepdf_eleve"),
re_path(r'^action/agenda$', views.agenda,name="agenda_eleve"),
re_path(r'^action/devoirs$', views.devoirs ,name="eleve_devoirs"),
re_path(r'^action/tds$', views.tds ,name="eleve_tds"),
re_path(r'^action/cours$', views.cours ,name="eleve_cours"),
re_path(r'^action/autre$', views.autre ,name="eleve_autre"),
re_path(r'^action/depotcopie/(\d+)$', views.depotCopie ,name="depot_copie"),
]