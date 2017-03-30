# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^check$', views.check, name="connect_app_eleve"),
    url(r'^connect$', views.connect, name="connect_app_eleve"),
    url(r'^agenda$', views.agenda, name="agenda_app_eleve"),
    url(r'^grades$', views.grades, name="grades_app_eleve"),
    url(r'^results$', views.results, name="results_app_eleve"),
    url(r'^programs$', views.programs, name="programs_app_eleve"),
]
