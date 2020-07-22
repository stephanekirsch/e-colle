#-*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
url(r'^$', views.connec,name="login_admin"),
url(r'^action$', views.action,name="action_admin"),
url(r'^action/config$', views.config,name="config"),
url(r'^action/configconfirm$', views.configconfirm,name="configconfirm"),
url(r'^action/classe$', views.classe,name="gestion_classe"),
url(r'^action/classe/modifier/(\d+)$', views.classemodif,name="modif_classe"),
url(r'^action/classe/supprimer/(\d+)$', views.classesuppr,name="suppr_classe"),
url(r'^action/matiere$', views.matiere,name="gestion_matiere"),
url(r'^action/matiere/modifier/(\d+)$', views.matieremodif,name="modif_matiere"),
url(r'^action/matiere/supprimer/(\d+)$', views.matieresuppr,name="suppr_matiere"),
url(r'^action/etab$', views.etab,name="gestion_etab"),
url(r'^action/etab/modifier/(\d+)$', views.etabmodif,name="modif_etab"),
url(r'^action/etab/supprimer/(\d+)$', views.etabsuppr,name="suppr_etab"),
url(r'^action/semaine$', views.semaine,name="gestion_semaine"),
url(r'^action/semaine/modifier/(\d+)$', views.semainemodif,name="modif_semaine"),
url(r'^action/semaine/supprimer/(\d+)$', views.semainesuppr,name="suppr_semaine"),
url(r'^action/semaine/generer$', views.genere_semaines ,name="genere_semaines"),
url(r'^action/eleve$', views.eleve,name="gestion_eleve"),
url(r'^action/eleve/tri/([0-1]{1})$', views.eleveTri,name="gestion_eleve_tri"),
url(r'^action/eleve/modifier/(\d+(?:-\d+)*)$', views.elevemodif,name="modif_eleve"),
url(r'^action/eleve/supprimer/(\d+)$', views.elevesuppr,name="suppr_eleve"),
url(r'^action/eleve/ajouter$', views.eleveajout,name="ajout_eleve"),
url(r'^action/eleve/csv$', views.elevecsv,name="csv_eleve"),
url(r'^action/colleur$', views.colleur,name="gestion_colleur"),
url(r'^action/colleur/modifier/(\d+(?:-\d+)*)$', views.colleurmodif,name="modif_colleur"),
url(r'^action/colleur/supprimer/(\d+)$', views.colleursuppr,name="suppr_colleur"),
url(r'^action/colleur/ajouter$', views.colleurajout,name="ajout_colleur"),
url(r'^action/prof$', views.prof,name="gestion_prof"),
url(r'^action/prof/modifier/(\d+)$', views.profmodif,name="modif_prof"),
url(r'^action/ferie$', views.ferie,name="gestion_ferie"),
url(r'^action/ferie/modifier/(\d+)$', views.feriemodif,name="modif_ferie"),
url(r'^action/ferie/supprimer/(\d+)$', views.feriesuppr,name="suppr_ferie"),
url(r'^action/rgpd/eleve/(\d+)$', views.rgpd_eleve,name="rgpd_eleve"),
url(r'^action/rgpd/eleve/pdf/(\d+)$', views.rgpd_eleve_pdf,name="rgpd_eleve_pdf"),
url(r'^action/rgpd/eleve/efface/(\d+)$', views.eleve_force_efface,name="eleve_force_efface"),
url(r'^action/rgpd/colleur/(\d+)$', views.rgpd_colleur,name="rgpd_colleur"),
url(r'^action/rgpd/colleur/pdf/(\d+)$', views.rgpd_colleur_pdf,name="rgpd_colleur_pdf"),
url(r'^action/rgpd/colleur/efface/(\d+)$', views.colleur_force_efface,name="colleur_force_efface"),
url(r'^action/nouvelle_annee$', views.nouvelle_annee, name="gestion_nouvelle_annee"),
url(r'^action/nouvelle_annee_confirm$', views.nouvelle_annee_confirm, name="gestion_nouvelle_annee_confirm"),
url(r'^action/sauvebdd$', views.sauvebdd, name="gestion_sauvebdd"),
url(r'^action/sauvegarde_bdd/([01]{1})$', views.sauvegarde_bdd, name="sauvegarde_bdd"),
url(r'^action/suppr_sauvegarde/(\d{4}-\d{2}-\d{2})$', views.suppr_sauvegarde, name="suppr_sauvegarde"),
url(r'^action/restaure_sauvegarde/(\d{4}-\d{2}-\d{2})$', views.restaure_sauvegarde, name="restaure_sauvegarde"),
url(r'^action/restaure_sauvegarde_confirm/(\d{4}-\d{2}-\d{2})/([123]{1})$', views.restaure_sauvegarde_confirm, name="restaure_sauvegarde_confirm"),
]