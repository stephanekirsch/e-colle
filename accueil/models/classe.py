from django.db import models
from .groupe import Groupe
from .eleve import Eleve
from .colleur import Colleur
from django.db.models.functions import Lower, Upper, Concat, Substr

class Classe(models.Model):
    ANNEE_PREPA = (
        (1,"1ère année"),
        (2,"2ème année")
    )
    nom = models.CharField(max_length=30, unique=True)
    annee = models.PositiveSmallIntegerField(choices=ANNEE_PREPA,default=1)
    matieres = models.ManyToManyField(
        "Matiere",
        verbose_name="matières",
        related_name="matieresclasse", 
        blank = True
    )
    profprincipal = models.ForeignKey(
        'Colleur',
        null=True,
        related_name="classeprofprincipal",
        on_delete=models.SET_NULL)
    class Meta:
        ordering=['annee', 'nom']

    def matierespk(self):
        if hasattr(self, 'listeMatieres'): 
            # si l'attribut existe déjà, on le renvoie
            return self.listeMatieres
        # pour éviter de faire la requête plusieurs fois, on garde le 
        # résultat en cache dans un attribut
        self.listeMatieres = self.matieres.values_list('pk', flat=True) 
        return self.listeMatieres

    def __str__(self):
        return self.nom

    def loginsEleves(self):
        """Renvoie la liste des logins des élèves de la classe ordonnés 
        par ordre alphabétique"""
        eleves = self.classeeleve.order_by(
            'user__last_name',
            'user__first_name'
        ).annotate(
            login=Lower(Concat(Substr('user__first_name',1,1),Substr('user__last_name',1,1)))
        ).order_by(
            'login',
            'user__last_name',
            'user__first_name'
        ).select_related('user')
        listeLogins = []
        lastlogin = False
        indice = 1
        for eleve in eleves:
            login = eleve.login
            if login == lastlogin:
                if indice == 1:
                    listeLogins[-1] += "1"
                indice += 1
                listeLogins.append("{}{:x}".format(login, indice))
            else:
                indice = 1
                listeLogins.append(login)
            lastlogin=login
        elevesLogin = list(zip(eleves, listeLogins))
        elevesLogin.sort(key = lambda x:(x[0].user.last_name, x[0].user.first_name))
        return elevesLogin

    def loginMatiereEleves(self):
        matiereeleves = []
        listeEleves = self.loginsEleves()
        for matiere in self.matieres.filter(colleur__classes=self).distinct():
            if matiere.temps != 30:
                matiereeleves.append(None)
            elif not matiere.lv:
                matiereeleves.append(listeEleves)
            elif matiere.lv == 1:
                listeTemp = listeEleves.copy()
                for i in range(len(listeTemp)-1, -1, -1):
                    if listeTemp[i][0].lv1 != matiere:
                        listeTemp.pop(i)
                matiereeleves.append(listeTemp)
            elif matiere.lv == 2:
                listeTemp = listeEleves.copy()
                for i in range(len(listeTemp)-1, -1, -1):
                    if listeTemp[i][0].lv2 != matiere:
                        listeTemp.pop(i)
                matiereeleves.append(listeTemp)
        return matiereeleves

    def dictEleves(self):
        """Renvoie un dictionnaire dont les clés sont les id des élèves 
        de la classe, et les valeurs le login correspondant"""
        dictEleves = {}
        for eleve,login in self.loginsEleves():
            dictEleves[eleve.pk] = login
        return dictEleves

    def loginsColleurs(self, semin=None, semax=None, colleur=None):
        """Renvoie la liste des logins des colleurs de la classe, qui 
        ont des colles entre les semaines semin et semax, ordonnés par 
        ordre alphabétique"""
        if colleur is not None:
            colleurs = Colleur.objects.filter(
                user__is_active=True, 
                classes__in=colleur.classes.all()
            ).distinct().annotate(
                login=Upper(Concat(Substr('user__first_name',1,1), Substr('user__last_name',1,1)))
            ).order_by(
                'login',
                'user__last_name',
                'user__first_name'
            )
        elif semin is None or semax is None:
            colleurs = self.colleur_set.filter(
                user__is_active=True
            ).annotate(
                login=Upper(Concat(Substr('user__first_name',1,1), Substr('user__last_name',1,1)))
            ).order_by('login','user__last_name','user__first_name')
        else:
            colleurs = self.colleur_set.filter(
                colle__semaine__lundi__range=(
                    semin.lundi,semax.lundi
                )
            ).distinct().annotate(
                login=Upper(Concat(Substr('user__first_name',1,1), Substr('user__last_name',1,1)))
            ).order_by('login', 'user__last_name','user__first_name')
        listeLogins = []
        lastlogin = False
        indice = 1
        for colleur in colleurs:
            login = colleur.login
            if login == lastlogin:
                if indice == 1:
                    listeLogins[-1] += "1"
                indice += 1
                listeLogins.append("{}{:x}".format(login, indice))
            else:
                indice = 1
                listeLogins.append(login)
            lastlogin = login
        return list(zip(colleurs, listeLogins))

    def dictColleurs(self, semin=None, semax=None):
        """Renvoie un dictionnaire dont les clés sont les id des 
        colleurs de la classe, et les valeurs le login correspondant"""
        dictColleurs={}
        for colleur, login in self.loginsColleurs(semin, semax):
            dictColleurs[colleur.pk] = login
        return dictColleurs

    def dictGroupes(self, noms=True):
        dictgroupes = dict()
        if noms is True:
            groupes = Groupe.objects.filter(classe=self)\
                      .prefetch_related('groupeeleve','groupeeleve__user')
            listegroupes = {groupe.pk: (groupe.nom,"; ".join(["{} {}".format(eleve.user.first_name.title(), eleve.user.last_name.upper()) for eleve in groupe.groupeeleve.all()])) for groupe in groupes}
            for matiere in self.matieres.filter(temps=20):
                if matiere.lv == 0:
                    dictgroupes[matiere.pk] = listegroupes
                elif matiere.lv == 1:
                    dictgroupes[matiere.pk] = {groupe.pk: (groupe.nom,"; ".join(["{} {}".format(eleve.user.first_name.title(),eleve.user.last_name.upper()) for eleve in groupe.groupeeleve.all() if eleve.lv1==matiere])) for groupe in groupes}
                elif matiere.lv == 2:
                    dictgroupes[matiere.pk] = {groupe.pk: (groupe.nom,"; ".join(["{} {}".format(eleve.user.first_name.title(),eleve.user.last_name.upper()) for eleve in groupe.groupeeleve.all() if eleve.lv2==matiere])) for groupe in groupes}
        else:
            groupes = Groupe.objects.filter(classe=self)
            listegroupes = [True]*groupes.count()
            for matiere in self.matieres.filter(temps=20):
                if matiere.lv == 0:
                    dictgroupes[matiere.pk] = listegroupes
                elif matiere.lv == 1:
                    dictgroupes[matiere.pk] = [any(eleve.lv1==matiere for eleve in groupe.groupeeleve.all()) for groupe in groupes]
                elif matiere.lv == 2:
                    dictgroupes[matiere.pk] = [any(eleve.lv2==matiere for eleve in groupe.groupeeleve.all()) for groupe in groupes]
        return dictgroupes

    def dictElevespk(self):
        dictEleves = dict()
        listeEleves = [True]*Eleve.objects.filter(classe=self).count()
        for matiere in self.matieres.filter(temps=30):
            if matiere.lv == 0:
                dictEleves[matiere.pk] = listeEleves
            elif matiere.lv == 1:
                dictEleves[matiere.pk] = [eleve.lv1 == matiere for eleve in Eleve.objects.filter(classe=self)]
            elif matiere.lv == 2:
                dictEleves[matiere.pk] = [eleve.lv2 == matiere for eleve in Eleve.objects.filter(classe=self)]
        return dictEleves
