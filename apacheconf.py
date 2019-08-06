import os

with open("e-colle.conf","rt",encoding="utf8") as fichier:
    contenu = fichier.read()
    dns = input("nom de domaine de e-colle (par exemple e-colle.fr): ")
    contenu = contenu.replace("e-colle.com",dns)
chemin = os.path.join('/etc','apache2','sites-available','e-colle.conf')
with open(chemin,"wt",encoding="utf8") as fichier:
    fichier.write(contenu)