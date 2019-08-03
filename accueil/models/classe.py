from django.db import models, connection,  transaction
from django.db.models import Q
from .groupe import Groupe
from .eleve import Eleve
from .config import Config
from .autre import dictfetchall
from django.db.models.functions import Lower, Upper, Concat, Substr
from ecolle.settings import BDD


def group_concat(arg):
    """Renvoie une chaîne de caractères correspondant à la syntaxe SQL 
    qui permet d'utiliser une fonction d'agrégation qui concatène des chaînes"""
    if BDD == 'postgresql' or BDD == 'postgresql_psycopg2':
        return "STRING_AGG(DISTINCT {0:}, ',' ORDER BY {0:})".format(arg)
    elif BDD == 'mysql':
        return "GROUP_CONCAT(DISTINCT {0:} ORDER BY {0:})".format(arg)
    elif BDD == 'sqlite3':
        return "GROUP_CONCAT(DISTINCT {})".format(arg)
    else:
        return "" # à compléter par ce qu'il faut dans le cas ou vous utilisez 
                  # un SGBD qui n'est ni mysql, ni postgresql, ni sqlite

class ColleurManager(models.Manager):
    def listeColleurClasse(self, colleur):
        requete = """SELECT DISTINCT colcla.id, colcla.colleur_id, colcla.classe_id FROM accueil_colleur_matieres colmat
                    INNER JOIN accueil_colleur col ON col.id = colmat.colleur_id
                    INNER JOIN accueil_colleur_classes colcla ON col.id = colcla.colleur_id
                    INNER JOIN accueil_prof pr ON pr.classe_id = colcla.classe_id AND pr.matiere_id = colmat.matiere_id
                    WHERE pr.colleur_id = %s OR colcla.colleur_id = %s AND colmat.colleur_id = %s"""
        with connection.cursor() as cursor:
            cursor.execute(requete, [colleur.id, colleur.id, colleur.id])
            return cursor.fetchall()

    def listeColleurMatiere(self, colleur):
        requete = """SELECT DISTINCT colmat.id, colmat.colleur_id, colmat.matiere_id FROM accueil_colleur_matieres colmat
                    INNER JOIN accueil_colleur col ON col.id = colmat.colleur_id
                    INNER JOIN accueil_colleur_classes colcla ON col.id = colcla.colleur_id
                    INNER JOIN accueil_prof pr ON pr.classe_id = colcla.classe_id AND pr.matiere_id = colmat.matiere_id
                    WHERE pr.colleur_id = %s OR colcla.colleur_id = %s AND colmat.colleur_id = %s"""
        with connection.cursor() as cursor:
            cursor.execute(requete, [colleur.id, colleur.id, colleur.id])
            return cursor.fetchall()

    def listeColleurs(self, matiere,classe, pattern = ""):
        # pour éviter de multiples accès à la BDD (même avec optimisation avec prefetch_related)
        # on fait la requête à la main avec fonction d'aggrégation pour concaténer les classes/matières
        where = []
        if classe is not None:
            where.append("cl.id = %s")
        if matiere is not None:
            where.append("m.id = %s")
        if pattern:
            where.append("LOWER(u.first_name) LIKE %s OR LOWER(u.last_name) LIKE %s")
        if where:
            where = "WHERE " + " AND ".join(where)
        else:
            where = ""
        requete = """SELECT u.first_name prenom, u.last_name nom, u.username identifiant, u.email email, u.is_active actif,
                  c.grade grade, c.id id, e.nom etablissement, u.id user_id, {}, {} FROM accueil_colleur c
                  INNER JOIN accueil_user u
                  ON u.colleur_id = c.id
                  LEFT OUTER JOIN accueil_etablissement e
                  ON c.etablissement_id = e.id
                  {}
                  {}
                  LEFT OUTER JOIN accueil_colleur_matieres cm2
                  ON cm2.colleur_id = c.id
                  LEFT OUTER JOIN accueil_matiere m2
                  ON cm2.matiere_id = m2.id
                  LEFT OUTER JOIN accueil_colleur_classes cc2
                  ON cc2.colleur_id = c.id
                  LEFT OUTER JOIN accueil_classe cl2
                  ON cc2.classe_id = cl2.id
                  {}
                  GROUP BY u.id, c.id, e.id
                  ORDER BY u.last_name, u.first_name, c.id
                  """.format(group_concat("m2.nomcomplet") + " matieres", group_concat('cl2.nom') + " classes", "" if matiere is None else """LEFT OUTER JOIN accueil_colleur_matieres cm
                  ON cm.colleur_id = c.id
                  LEFT OUTER JOIN accueil_matiere m
                  ON cm.matiere_id = m.id""","" if classe is None else """LEFT OUTER JOIN accueil_colleur_classes cc
                  ON cc.colleur_id = c.id
                  LEFT OUTER JOIN accueil_classe cl
                  ON cc.classe_id = cl.id""", where)
        with transaction.atomic():
            arguments = [x.id for x in (matiere, classe) if x is not None] + 2*(["%{}%".format(pattern)] if pattern else [])
            with connection.cursor() as cursor:
                cursor.execute(requete, arguments)
                colleurs = dictfetchall(cursor)
        return colleurs


class Colleur(models.Model):
    LISTE_GRADES = [(0,"autre"), (1,"certifié"), (2,"bi-admissible"), (3,"agrégé"), (4,"chaire supérieure")]
    matieres = models.ManyToManyField("Matiere", verbose_name="Matière(s)")
    classes = models.ManyToManyField("Classe", verbose_name="Classe(s)")
    grade = models.PositiveSmallIntegerField(choices=LISTE_GRADES, default=3)
    etablissement = models.ForeignKey("Etablissement", verbose_name="Établissement", null=True,blank=True, on_delete=models.PROTECT)
    objects = ColleurManager()
    
    def allprofs(self):
        return self.colleurprof.prefetch_related('classe')

    def classeGroupes(self):
        classes = set()
        for prof in self.colleurprof.prefetch_related('classe').all():
            if prof.modifgroupe or prof.classe.profprincipal == self:
                classes.add(prof.classe)
        return sorted(classes, key = lambda x:x.nom)

    def modifgroupe(self):
        if Config.objects.get_config().modif_prof_groupe:
            for prof in self.colleurprof.all():
                if prof.modifgroupe or prof.classe.profprincipal == self:
                    return True
        return False

    def ectsclasses(self):
        return Classe.objects.filter(Q(profprincipal=self) | Q(classematiereECTS__profs=self)).distinct().order_by('nom')

    def __str__(self):
        if hasattr(self,'user'):
            return "{} {}".format(self.user.first_name.title(),self.user.last_name.upper())
        return ""

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
