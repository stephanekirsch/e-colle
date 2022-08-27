#-*- coding: utf-8 -*-
from django.urls import re_path
from . import views

urlpatterns = [
re_path(r'^$', views.connec,name="login_admin"),
re_path(r'^action$', views.action,name="action_admin"),
re_path(r'^action/config$', views.config,name="config"),
re_path(r'^action/configconfirm$', views.configconfirm,name="configconfirm"),
re_path(r'^action/information$', views.information,name="information_admin"),
re_path(r'^action/informationsuppr/(\d+)$', views.informationSuppr,name="informationsuppr_admin"),
re_path(r'^action/informationmodif/(\d+)$', views.informationModif,name="informationmodif_admin"),
re_path(r'^action/classe$', views.classe,name="gestion_classe"),
re_path(r'^action/classe/modifier/(\d+)$', views.classemodif,name="modif_classe"),
re_path(r'^action/classe/supprimer/(\d+)$', views.classesuppr,name="suppr_classe"),
re_path(r'^action/matiere$', views.matiere,name="gestion_matiere"),
re_path(r'^action/matiere/modifier/(\d+)$', views.matieremodif,name="modif_matiere"),
re_path(r'^action/matiere/supprimer/(\d+)$', views.matieresuppr,name="suppr_matiere"),
re_path(r'^action/etab$', views.etab,name="gestion_etab"),
re_path(r'^action/etab/modifier/(\d+)$', views.etabmodif,name="modif_etab"),
re_path(r'^action/etab/supprimer/(\d+)$', views.etabsuppr,name="suppr_etab"),
re_path(r'^action/semaine$', views.semaine,name="gestion_semaine"),
re_path(r'^action/semaine/modifier/(\d+)$', views.semainemodif,name="modif_semaine"),
re_path(r'^action/semaine/supprimer/(\d+)$', views.semainesuppr,name="suppr_semaine"),
re_path(r'^action/semaine/generer$', views.genere_semaines ,name="genere_semaines"),
re_path(r'^action/eleve$', views.eleve,name="gestion_eleve"),
re_path(r'^action/eleve/tri/([0-1]{1})$', views.eleveTri,name="gestion_eleve_tri"),
re_path(r'^action/eleve/modifier/(\d+(?:-\d+)*)$', views.elevemodif,name="modif_eleve"),
re_path(r'^action/eleve/supprimer/(\d+)$', views.elevesuppr,name="suppr_eleve"),
re_path(r'^action/eleve/ajouter$', views.eleveajout,name="ajout_eleve"),
re_path(r'^action/eleve/csv$', views.elevecsv,name="csv_eleve"),
re_path(r'^action/colleur$', views.colleur,name="gestion_colleur"),
re_path(r'^action/colleur/csv$', views.colleurcsv,name="csv_colleur"),
re_path(r'^action/colleur/modifier/(\d+(?:-\d+)*)$', views.colleurmodif,name="modif_colleur"),
re_path(r'^action/colleur/supprimer/(\d+)$', views.colleursuppr,name="suppr_colleur"),
re_path(r'^action/colleur/ajouter$', views.colleurajout,name="ajout_colleur"),
re_path(r'^action/prof$', views.prof,name="gestion_prof"),
re_path(r'^action/prof/modifier/(\d+)$', views.profmodif,name="modif_prof"),
re_path(r'^action/ferie$', views.ferie,name="gestion_ferie"),
re_path(r'^action/ferie/modifier/(\d+)$', views.feriemodif,name="modif_ferie"),
re_path(r'^action/ferie/supprimer/(\d+)$', views.feriesuppr,name="suppr_ferie"),
re_path(r'^action/rgpd/eleve/(\d+)$', views.rgpd_eleve,name="rgpd_eleve"),
re_path(r'^action/rgpd/eleve/pdf/(\d+)$', views.rgpd_eleve_pdf,name="rgpd_eleve_pdf"),
re_path(r'^action/rgpd/eleve/efface/(\d+)$', views.eleve_force_efface,name="eleve_force_efface"),
re_path(r'^action/rgpd/colleur/(\d+)$', views.rgpd_colleur,name="rgpd_colleur"),
re_path(r'^action/rgpd/colleur/pdf/(\d+)$', views.rgpd_colleur_pdf,name="rgpd_colleur_pdf"),
re_path(r'^action/rgpd/colleur/efface/(\d+)$', views.colleur_force_efface,name="colleur_force_efface"),
re_path(r'^action/nouvelle_annee$', views.nouvelle_annee, name="gestion_nouvelle_annee"),
re_path(r'^action/nouvelle_annee_confirm$', views.nouvelle_annee_confirm, name="gestion_nouvelle_annee_confirm"),
re_path(r'^action/sauvebdd$', views.sauvebdd, name="gestion_sauvebdd"),
re_path(r'^action/sauvegarde_bdd/([01]{1})$', views.sauvegarde_bdd, name="sauvegarde_bdd"),
re_path(r'^action/suppr_sauvegarde/(\d{4}-\d{2}-\d{2})$', views.suppr_sauvegarde, name="suppr_sauvegarde"),
re_path(r'^action/restaure_sauvegarde/(\d{4}-\d{2}-\d{2})$', views.restaure_sauvegarde, name="restaure_sauvegarde"),
re_path(r'^action/restaure_sauvegarde_confirm/(\d{4}-\d{2}-\d{2})/([123]{1})$', views.restaure_sauvegarde_confirm, name="restaure_sauvegarde_confirm"),
]