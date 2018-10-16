from django.contrib.auth.models import AbstractUser
from django.db import models

from ecolle.settings import DEFAULT_CSS

class User(AbstractUser):
    eleve = models.OneToOneField("Eleve", null=True, on_delete=models.CASCADE)
    colleur = models.OneToOneField("Colleur", null=True, on_delete=models.CASCADE)

    css = models.CharField(
        verbose_name="Style préféré",
        default=DEFAULT_CSS,
        null=True,
        blank=True,
        max_length=50
    )

    def totalmessages(self):
        return Destinataire.objects.filter(user=self).count()

    def messagesnonlus(self):
        return Destinataire.objects.filter(user=self,lu=False).count()

    def __str__(self):
        return "{} {}".format(self.first_name.title(),self.last_name.upper())
