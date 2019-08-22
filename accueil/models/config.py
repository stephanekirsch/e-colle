from django.db import models

class ConfigManager(models.Manager):
    def get_config(self):
        try:
            config = self.all()[0]
        except Exception:
            config = Config(nom_etablissement="",
                            modif_secret_col=False,
                            modif_secret_groupe=False,
                            modif_prof_col=True,
                            modif_prof_groupe=True,
                            default_modif_col=False,
                            default_modif_groupe=False,
                            message_eleves=False,
                            mathjax=True,
                            ects=False,
                            nom_adresse_etablissement="",
                            academie="",
                            ville="",
                            app_mobile=False
                           )
        return config


class Config(models.Model):
    nom_etablissement = models.CharField(
        verbose_name="Nom de l'établissement",
        max_length=30,
        blank=True
    )
    modif_secret_col = models.BooleanField(
        verbose_name="Modification du colloscope par le secrétariat",
        default=False
    )
    modif_secret_groupe = models.BooleanField(
            verbose_name="Modification des groupes par le secrétariat",
            default=False
    )
    modif_prof_col = models.BooleanField(
            verbose_name="Modification du colloscope par les enseignants",
            default=True
    )
    default_modif_col = models.BooleanField(
            verbose_name="Modification du colloscope par défaut pour tous les enseignants",
            default=False
    )
    modif_prof_groupe = models.BooleanField(
            verbose_name="Modification des groupes par les enseignants",
            default=True
    )
    default_modif_groupe = models.BooleanField(
            verbose_name="Modification des groupes par défaut pour tous les enseignants",
            default=False
    )
    message_eleves = models.BooleanField(
            verbose_name="Autoriser les étudiants à écrire aux colleurs (pas seulement répondre)",
            default=False
    )
    mathjax = models.BooleanField(
            verbose_name="Mise en forme des formules mathématiques avec Lateχ",
            default=True
    )
    ects = models.BooleanField(
            verbose_name="Gestion des fiches de crédits ECTS",
            default=False
    )
    nom_adresse_etablissement = models.TextField(
            verbose_name="Nom complet de l'établissement + adresse",
            blank=True
    )
    ville = models.CharField(
            verbose_name = "Ville de l'établissement", 
            max_length=40,
            blank=True
    )
    academie = models.CharField(
            verbose_name = "Académie de l'établissement", 
            max_length=40,
            blank=True
    )
    app_mobile = models.BooleanField(
            verbose_name="Application mobile",
            default=False
    )
    objects = ConfigManager()
