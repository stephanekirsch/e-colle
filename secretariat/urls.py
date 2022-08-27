#-*- coding: utf-8 -*-
from django.urls import re_path
from . import views

urlpatterns = [
re_path(r'^$', views.connec, name="login_secret"),
re_path(r'^action$', views.action, name="action_secret"),
re_path(r'^action/resultats$', views.resultats, name="resultats_secret"),
re_path(r'^action/resultatcsv/(\d+)/(\d+)/(\d+)/(\d+)$', views.resultatcsv, name="resultatcsv_secret"),
re_path(r'^action/information$', views.information,name="information_secret"),
re_path(r'^action/informationsuppr/(\d+)$', views.informationSuppr,name="informationsuppr_secret"),
re_path(r'^action/informationmodif/(\d+)$', views.informationModif,name="informationmodif_secret"),
re_path(r'^action/notes$', views.notes, name="notes_secret"),
re_path(r'^action/colloscope/([0-1]{1})/(\d+)$', views.colloscope, name="colloscope_secret"),
re_path(r'^action/colloscope/([0-1]{1})/(\d+)/(\d+)/(\d+)$', views.colloscope2, name="colloscope2_secret"),
re_path(r'^action/colloscopepdf/(\d+)/(\d+)/(\d+)$', views.colloscopePdf, name="colloscopepdf_secret"),
re_path(r'^action/colloscopecsv/(\d+)/(\d+)/(\d+)$', views.colloscopeCsv, name="colloscopecsv_secret"),
re_path(r'^action/colloscope/modifier/(\d+)/(\d+)/(\d+)$', views.colloscopeModif,name="colloscopemodif_secret"),
re_path(r'^action/colloscope/importer/(\d+)$', views.colloscopeImport,name="importcolloscope_secret"),
re_path(r'^action/creneau/modifier/(\d+)/(\d+)/(\d+)$', views.creneauModif,name="creneaumodif_secret"),
re_path(r'^action/creneau/supprimer/(\d+)/(\d+)/(\d+)$', views.creneauSuppr,name="creneausuppr_secret"),
re_path(r'^action/creneau/dupliquer/(\d+)/(\d+)/(\d+)$', views.creneauDupli,name="creneaudupli_secret"),
re_path(r'^action/colloscope/ajax/(\d+)/(\d+)/(\d+)/(\d+|semaine)/(\d+|creneau)$', views.ajaxcolloscope,name="ajax_secret"),
re_path(r'^action/colloscope/ajax/eleve/(\d+)/(\d+)/(\d+)/(\d+|semaine)/(\d+|creneau)/(\w{1,3})$', views.ajaxcolloscopeeleve,name="ajax_secret_eleve"),
re_path(r'^action/colloscope/ajax/compat/(\d+)$', views.ajaxcompat,name="ajaxcompat_secret"),
re_path(r'^action/colloscope/ajax/majcolleur/(\d+|matiere)/(\d+)$', views.ajaxmajcolleur,name="ajaxmaj_secret"),
re_path(r'^action/colloscope/ajax/effacer/(\d+|semaine)/(\d+|creneau)$', views.ajaxcolloscopeeffacer,name="ajaxeffacer_secret"),
re_path(r'^action/colloscope/ajax/multi/(-?\d+|matiere)/(\d+|kolleur)/(\d*|groupe)/(\d*|eleve)/(\d+|semaine)/(\d+|creneau)/([1-9]{1}|[1-2]{1}[0-9]{1}|30|duree)/(1|2|3|4|8|frequence)/([1-9]{1}|1[0-9]{1}|20|permu)$', views.ajaxcolloscopemulti,name="ajaxmulti_secret"),
re_path(r'^action/colloscope/ajax/multi/confirm/(-?\d+|matiere)/(\d+|kolleur)/(\d*|groupe)/(\d*|eleve)/(\d+|semaine)/(\d+|creneau)/([1-9]{1}|[1-2]{1}[0-9]{1}|30|duree)/(1|2|3|4|8|frequence)/([1-9]{1}|1[0-9]{1}|20|permu)$', views.ajaxcolloscopemulticonfirm,name="ajaxmulticonfirm_secret"),
re_path(r'^action/groupe/(\d+)$', views.groupe,name="groupe_secret"),
re_path(r'^action/groupe/creer/(\d+)$', views.groupeCreer,name="groupecreer_secret"),
re_path(r'^action/groupe/supprimer/(\d+)$', views.groupeSuppr,name="groupesuppr_secret"),
re_path(r'^action/groupe/modifier/(\d+)$', views.groupeModif,name="groupemodif_secret"),
re_path(r'^action/groupe/swap/(\d+)$', views.groupeSwap,name="groupeSwap_secret"),
re_path(r'^action/groupe/csv/(\d+)$', views.groupecsv,name="groupecsv_secret"),
re_path(r'^action/recapitulatif$', views.recapitulatif, name="recapitulatif"),
re_path(r'^action/compta$', views.compta, name="compta"),
re_path(r'^action/ramassage$', views.ramassage, name="ramassage"),
re_path(r'^action/ramassage/suppr/(\d+)$', views.ramassageSuppr, name="ramassagesuppr"),
re_path(r'^action/ramassage/pdf/(\d+)/(\d+)/(\d+)$', views.ramassagePdf, name="ramassagepdf"),
re_path(r'^action/ramassage/csv/(\d+)/(\d+)/(\d+)$', views.ramassageCSV, name="ramassagecsv"),
re_path(r'^action/ramassage/pdfparclasse/(\d+)/(\d+)/(\d+)$', views.ramassagePdfParClasse, name="ramassagepdfparclasse"),
re_path(r'^action/ramassage/csvparclasse/(\d+)/(\d+)/(\d+)$', views.ramassageCSVParClasse, name="ramassagecsvparclasse"),
re_path(r'^action/ects/credits/(\d+)$', views.ectscredits,name="secret_ects_credits"),
re_path(r'^action/ects/fiche/(\d+)$', views.ficheectspdf,name="secret_ects_fiche"),
re_path(r'^action/ects/attestation/(\d+)$', views.attestationectspdf,name="secret_ects_attestation"),
re_path(r'^action/ects/fiche/classe/(\d+)$', views.ficheectsclassepdf,name="secret_ects_fiche_classe"),
re_path(r'^action/ects/attestation/classe/(\d+)$', views.attestationectsclassepdf,name="secret_ects_attestation_classe")]