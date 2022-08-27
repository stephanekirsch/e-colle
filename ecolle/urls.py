from django.urls import include, re_path
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from accueil import views

urlpatterns = [
    re_path(r'^$', views.home, name="accueil"),
    re_path(r'^messages$', views.messages, name="messages"),
    re_path(r'^message/(\d+)$', views.message, name="message"),
    re_path(r'^ecrire$', views.ecrire, name="ecrire"),
    re_path(r'^repondre/(\d+)$', views.repondre, name="repondre"),
    re_path(r'^repondreatous/(\d+)$', views.repondreatous, name="repondreatous"),
    re_path(r'^administrateur/', include('administrateur.urls')),
    re_path(r'^eleve/', include('eleve.urls')),
    re_path(r'^app_mobile/', include('app_mobile.urls')),
    re_path(r'^colleur/', include('colleur.urls')),
    re_path(r'^secretariat/', include('secretariat.urls')),
    re_path(r'^logout/$', views.deconnexion, name="deconnexion"),
    re_path(r'^profil/$', views.profil, name="profil"),
    re_path(r'^qrcode/$', views.qrcode, name="qrcode"),
    re_path(r'^qrcodepng/$', views.qrcodepng, name="qrcodepng")
]

urlpatterns += staticfiles_urlpatterns()
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

