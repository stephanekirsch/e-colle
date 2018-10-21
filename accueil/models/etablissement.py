from django.db import models

class Etablissement(models.Model):
    nom = models.CharField(max_length = 50, unique=True)

    def __str__(self):
        return self.nom
