# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^check$', views.check, name="connect_app_mobile"),
    url(r'^connect$', views.connect, name="connect_app_mobile"),
    url(r'^agenda$', views.agenda, name="agenda_app_mobile"),
    url(r'^grades$', views.grades, name="grades_app_mobile"),
    url(r'^results$', views.results, name="results_app_mobile"),
    url(r'^colles$', views.colles, name="colles_app_mobile"),
    url(r'^programs$', views.programs, name="programs_app_mobile"),
    url(r'^messages$', views.messages, name="messages_app_mpbile"),
    url(r'^sentmessages$', views.sentmessages,
        name="sent_messages_app_mobile"),
    url(r'^readmessage/(\d+)$', views.readmessage,
        name="read_message_app_mobile"),
    url(r'^deletemessage/(\d+)$', views.deletemessage,
        name="delete_message_app_mobile"),
    url(r'^answer/(\d+)-(\d+)$', views.answer, name="answer_app_mobile"),
]
