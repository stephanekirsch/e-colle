# -*- coding: utf-8 -*-

from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^check$', views.check, name="check_app_mobile"),
    re_path(r'^connect$', views.connect, name="connect_app_mobile"),
    re_path(r'^agendaprograms$', views.agendaprograms, name="agenda_app_mobile"),
    re_path(r'^grades$', views.grades, name="grades_app_mobile"),
    re_path(r'^results$', views.results, name="results_app_mobile"),
    re_path(r'^colles$', views.colles, name="colles_app_mobile"),
    re_path(r'^messages$', views.messages, name="messages_app_mobile"),
    re_path(r'^readmessage/(\d+)$', views.readmessage,
        name="read_message_app_mobile"),
    re_path(r'^deletemessage/(\d+)$', views.deletemessage,
        name="delete_message_app_mobile"),
    re_path(r'^answer/(\d+)-(\d+)$', views.answer, name="answer_app_mobile"),
    re_path(r'^colleurdata$', views.colleurDonnees, name="colleur_donneesapp_mobile"),
    re_path(r'^deletegrade/(\d+)$', views.deletegrade, name="delete_grade_app_mobile"),
    re_path(r'^addsinglegrade$', views.addsinglegrade, name="add_single_grade_app_mobile"),
    re_path(r'^addgroupgrades$', views.addgroupgrades, name="add_group_grades_app_mobile"),
    re_path(r'^adddraftgrades$', views.adddraftgrades, name="add_draft_grades_app_mobile"),
    re_path(r'^addmessage$', views.addmessage, name="add_message_app_mobile"),
    re_path(r'^documents$', views.documents, name="documents_app_mobile"),
    re_path(r'^documentsprof$', views.documents_prof, name="documentsprof_app_mobile"),
    re_path(r'^inscriptionplanche$', views.inscriptionPlanche, name="inscriptionplanche_app_mobile"),
    re_path(r'^deinscriptionplanche/(\d+)$', views.desinscriptionPlanche, name="deinscriptionplanche_app_mobile"),
]
