from django.db import models
import locale
from datetime import date, timedelta, time

class Semaine(models.Model):
    locale.setlocale(locale.LC_ALL,'')
    LISTE_SEMAINES = [(i,i) for i in range(1,36)] 
    base = date.today()
    base = base-timedelta(days=base.weekday())
    # utilisation d'une fonction lambda car en python 3 les compréhensions on leur propre espace de nom, et les variables d'une classe englobante y sont invisibles
    liste1 = (lambda y:[y+timedelta(days=7*x) for x in range(-40,60)])(base)
    liste2 = [d.strftime('%d %B %Y') for d in liste1]
    LISTE_LUNDIS = zip(liste1,liste2)
    numero = models.PositiveSmallIntegerField(unique=True, choices=LISTE_SEMAINES, default=1)
    lundi = models.DateField(unique=True, choices=LISTE_LUNDIS, default=base)

    class Meta:
        ordering=['lundi']

    def __str__(self):
        samedi=self.lundi+timedelta(days=5)
        return "{}:{}/{}-{}/{}".format(self.numero,self.lundi.day,self.lundi.month,samedi.day,samedi.month)
