from django.db import models
from datetime import timedelta

class Semaine(models.Model):
    LISTE_SEMAINES = [(i,i) for i in range(1,37)] 
    numero = models.PositiveSmallIntegerField(unique=True, choices=LISTE_SEMAINES, default=1)
    lundi = models.DateField(unique=True)

    class Meta:
        ordering=['lundi']

    def __str__(self):
        try:
            samedi=self.lundi+timedelta(days=5)
            return "{}:{}/{}-{}/{}".format(self.numero,self.lundi.day,self.lundi.month,samedi.day,samedi.month)
        except Exception:
            return ""
