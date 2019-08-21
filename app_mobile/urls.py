# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^check$', views.check, name="check_app_mobile"),
    url(r'^connect$', views.connect, name="connect_app_mobile"),
    url(r'^agendaprograms$', views.agendaprograms, name="agenda_app_mobile"),
    url(r'^grades$', views.grades, name="grades_app_mobile"),
    url(r'^results$', views.results, name="results_app_mobile"),
    url(r'^colles$', views.colles, name="colles_app_mobile"),
    url(r'^messages$', views.messages, name="messages_app_mobile"),
    url(r'^readmessage/(\d+)$', views.readmessage,
        name="read_message_app_mobile"),
    url(r'^deletemessage/(\d+)$', views.deletemessage,
        name="delete_message_app_mobile"),
    url(r'^answer/(\d+)-(\d+)$', views.answer, name="answer_app_mobile"),
    url(r'^colleurdata$', views.colleurDonnees, name="colleur_donneesapp_mobile"),
    url(r'^deletegrade/(\d+)$', views.deletegrade, name="delete_grade_app_mobile"),
    url(r'^addsinglegrade$', views.addsinglegrade, name="add_single_grade_app_mobile"),
    url(r'^addgroupgrades$', views.addgroupgrades, name="add_group_grades_app_mobile"),
    url(r'^adddraftgrades$', views.adddraftgrades, name="add_draft_grades_app_mobile"),
    url(r'^addmessage$', views.addmessage, name="add_message_app_mobile")
]
