from django.db import models
from django.utils import timezone
from datetime import timedelta, datetime, time
from ecolle.settings import HEURE_DEBUT, HEURE_FIN, INTERVALLE

class Planche(models.Model):
    colleur = models.ForeignKey("Colleur",verbose_name="Colleur",related_name="planchecolleur",on_delete=models.PROTECT)
    classes = models.ManyToManyField("Classe",verbose_name="Classe(s)",blank=False)
    matiere = models.ForeignKey("Matiere",related_name="planchematiere",on_delete=models.PROTECT)
    semaine = models.ForeignKey("semaine",related_name="planchesemaine",on_delete=models.PROTECT)
    eleve = models.ForeignKey("Eleve",related_name="plancheeleve",null=True,blank=True,on_delete=models.SET_NULL)
    commentaire = models.CharField(max_length=100,null=True,blank=True)
    LISTE_HEURE=[(i,"{}h{:02d}".format(i//60,(i%60))) for i in range(HEURE_DEBUT,HEURE_FIN,INTERVALLE)] 
        # une heure est représentée par le nombre de minutes depuis
        # minuit
    JOURS = ["lundi","mardi","mercredi","jeudi","vendredi","samedi"]
    LISTE_JOUR=enumerate(JOURS)
    jour = models.PositiveSmallIntegerField(choices=LISTE_JOUR,default=0)
    heure = models.PositiveSmallIntegerField(choices=LISTE_HEURE,default=480)
    salle = models.CharField(max_length=20,null=True,blank=True)

    class Meta:
        ordering = ['matiere__nom', 'colleur__user__last_name', 'colleur__user__first_name','semaine__numero','jour','heure']

    def get_date(self):
        return (self.semaine.lundi + timedelta(days=self.jour,minutes=self.heure)).strftime("%d/%m/%Y")

    def get_utc_timestamp(self):
        return int(datetime.combine(self.semaine.lundi + timedelta(days=self.jour),
                time(self.heure // 60, self.heure % 60)).replace(tzinfo=timezone.utc).timestamp())

    def __str__(self):
        return "{} {}, S{},{} {}h{:02d}".format(self.colleur.user.first_name.title(),self.colleur.user.last_name.upper(),self.semaine.numero,self.JOURS[self.jour],int(self.heure)//60,int(self.heure)%60)

