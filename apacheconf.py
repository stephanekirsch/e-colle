import os
import subprocess

chemin = os.path.join('/etc','apache2','sites-available','e-colle.conf')
with open("e-colle.conf","rt",encoding="utf8") as fichier, open(chemin,"wt",encoding="utf8") as fichier2:
    contenu = fichier.read()
    dns = input("nom de domaine de e-colle (par exemple e-colle.fr): ")
    contenu = contenu.replace("e-colle.com",dns)
    fichier2.write(contenu)
cheminhtml = os.path.join('/var','www','html','e-colle')
cheminlocal = os.path.dirname(os.path.abspath(__file__))
subprocess.run(["sudo","ln","-s",cheminlocal,cheminhtml])
