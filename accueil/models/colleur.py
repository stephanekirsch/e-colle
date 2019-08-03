from django.db import models
from django.db import transaction,connection
from django.db.models import Q

from .config import Config


def dictfetchall(cursor):
    """Renvoie les lignes du curseur sous forme de dictionnaire"""
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

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
