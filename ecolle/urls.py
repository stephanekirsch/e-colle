from django.conf.urls import include, url
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from accueil import views

urlpatterns = [
    url(r'^$', views.home, name="accueil"),
    url(r'^messages$', views.messages, name="messages"),
    url(r'^messagesenvoyes$', views.messagesenvoyes, name="messagesenvoyes"),
    url(r'^message/(\d+)$', views.message, name="message"),
    url(r'^messageenvoye/(\d+)$', views.messageenvoye, name="messageenvoye"),
    url(r'^ecrire$', views.ecrire, name="ecrire"),
    url(r'^repondre/(\d+)$', views.repondre, name="repondre"),
    url(r'^administrateur/', include('administrateur.urls')),
    url(r'^eleve/', include('eleve.urls')),
    url(r'^colleur/', include('colleur.urls')),
    url(r'^secretariat/', include('secretariat.urls')),
    url(r'^logout/$', views.deconnexion, name="deconnexion"),
    url(r'^profil/$', views.profil, name="profil")
]

urlpatterns += staticfiles_urlpatterns()
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
