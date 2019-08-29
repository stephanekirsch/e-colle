import sys
import platform
import subprocess
from getpass import getpass

liste_echecs = []
liste_echecs_config = []

install_command = "apt"

def aptinstall(package):
    return subprocess.run(
        ["sudo",install_command, "install", package])

def pipinstall(package):
    return subprocess.run(
        ["sudo","-H","pip3", "install", package])

def configpostgresl():
    from pexpect import spawn, TIMEOUT
    from ecolle.config import DB_PASSWORD, DB_NAME, DB_USER, DB_PORT, DB_HOST
    if DB_PASSWORD =="":
        return
    print("-"*20)
    print("configuration de la base de données")
    p=spawn("sudo -i -u postgres", encoding="utf8")
    passwd = getpass("[sudo] mot de passe: ")
    p.sendline(passwd)
    p.sendline("createuser -PE {}".format(DB_USER))
    p.expect("Enter password for new role: ")
    p.sendline("{}".format(DB_PASSWORD))
    p.expect("Enter it again: ")
    p.sendline("{}".format(DB_PASSWORD))
    i = p.expect(['createuser: creation of new role failed: ERROR:  role "e-colle" already exists',TIMEOUT],timeout=2)
    if i==0:
        print("l'utilisateur e-colle existe déjà")
        maj = input("Voulez-vous mettre à jour son mot de passe? O/N (N): ")
        if maj not in "nN":
            p.sendline("dropuser e-colle")
            p.sendline("createuser -PE e-colle")
            p.expect("Enter password for new role: ")
            p.sendline("{}".format(DB_PASSWORD))
            p.expect("Enter it again: ")
            p.sendline("{}".format(DB_PASSWORD))
            print("mot de passe mis à jour")
    p.sendline("createdb -O {} {} -h {} -E UTF8 {}".format(DB_USER, "" if not DB_PORT else ("-p " + DB_PORT), DB_HOST, DB_NAME))
    i = p.expect(['createdb: database creation failed: ERROR:  database "e-colle" already exists',TIMEOUT],timeout=2)
    if i==0:
        print("la base de données e-colle existe déjà")
        maj = input("Voulez-vous l'effacer et la recréer? O/N (N): ")
        if maj not in "nN":
            p.sendline("dropdb e-colle")
            p.sendline("createdb -O {} {} -h {} -E UTF8 {}".format(DB_USER, "" if not DB_PORT else ("-p " + DB_PORT), DB_HOST, DB_NAME))
            print("base de données recréée")
    p.sendline("exit")
    p.close

def configmysql():
    from pexpect import spawn, TIMEOUT
    from ecolle.config import DB_PASSWORD, DB_NAME, DB_USER, DB_PORT, DB_HOST
    if DB_PASSWORD =="":
        return
    print("-"*20)
    print("configuration de la base de données")
    p=spawn("sudo mysql", encoding="utf8")
    passwd = getpass("[sudo] mot de passe: ")
    p.sendline(passwd)
    p.sendline("CREATE USER '{}' IDENTIFIED BY '{}';".format(DB_USER, DB_PASSWORD))
    i = p.expect(['ERROR',TIMEOUT],timeout=2)
    if i==0:
        print("l'utilisateur e-colle existe déjà")
        maj = input("Voulez-vous mettre à jour son mot de passe? O/N (N): ")
        if maj not in "nN":
            p.sendline("DROP USER `{}`;".format(DB_USER))
            p.sendline("CREATE USER '{}' IDENTIFIED BY '{}';".format(DB_USER, DB_PASSWORD))
            print("mot de passe mis à jour")
    p.sendline("CREATE DATABASE `{}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;".format(DB_NAME))
    i = p.expect(["ERROR",TIMEOUT],timeout=2)
    if i==0:
        print("la base de données e-colle existe déjà")
        maj = input("Voulez-vous l'effacer et la recréer? O/N (N): ")
        if maj not in "nN":
            p.sendline("DROP DATABASE `{}`;".format(DB_NAME))
            p.sendline("CREATE DATABASE `{}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;".format(DB_NAME))
            print("base de données recréée")
    p.sendline("GRANT ALL PRIVILEGES ON `{}`.* TO `{}` WITH GRANT OPTION;".format(DB_NAME, DB_USER))
    i = p.expect(["ERROR",TIMEOUT],timeout=2)
    if i==0:
        print("erreur dans la modification des privilèges")
    p.sendline("exit")
    p.close()

def configsqlite():
    from pexpect import spawn
    print("-"*20)
    print("configuration de la base de données")
    p=spawn("sqlite3 e-colle.db",encoding="utf8")
    print("base de données créée")
    p.sendline(".quit")

def installapache():
    print("-"*20)
    print("installation de apache2")
    completedProcess = aptinstall("apache2")
    if completedProcess.returncode:
        print("échec de l'installation d'apache2")
        liste_echecs.append("apache2")
    print("-"*20)
    print("installation de libapache2-mod-wsgi-py3")
    completedProcess = aptinstall("libapache2-mod-wsgi-py3")
    if completedProcess.returncode:
        print("échec de l'installation de libapache2-mod-wsgi-py3")
        liste_echecs.append("libapache2-mod-wsgi-py3")
    if "apache2" not in liste_echecs and "libapache2-mod-wsgi-py3" not in liste_echecs:
        configapache()

def configapache():
    code1 = subprocess.run(["sudo","a2enmod","wsgi"]).returncode # activation du mod wsgi
    # lecture de e-colle.conf
    subprocess.run(["sudo","python3","apacheconf.py"])
    code2 = subprocess.run(["sudo","a2ensite","e-colle.conf"]).returncode # activation du site
    if not(code1 or code2):
        droits()
    subprocess.run(["sudo","service","apache2","reload"])

def droits():
    print("gestion des droits d'apache")
    p = subprocess.Popen("whoami",shell=True,stdout=subprocess.PIPE)
    user = str(p.communicate()[0], encoding="utf8").strip()
    subprocess.run(["sudo","groupadd","web"]) # création du group web
    subprocess.run(["sudo","adduser",user,"web"]) # ajout de l'utilisateur courant au groupe web
    subprocess.run(["sudo","adduser","www-data","web"]) # ajout de l'utilisateur www-data (apache) au groupe web
    subprocess.run(["sudo","chown","-R","{}:web".format(user),"../e-colle"]) # tout le répertoire e-colle est associé au group web
    print("changement des droits effectué")


def main():
    global install_command
    if platform.system().lower() != 'linux':
        print("cette commande ne fonctionne que sous linux")
        return
    if sys.version[:3] < '3.5':
        print("Il vous faut une version de de Python >= 3.5")
        return
    p = subprocess.Popen("command -v apt",shell=True,stdout=subprocess.PIPE)
    result = p.communicate()[0]
    if result != bytes(0):
        install_command = "apt"
    else:
        p = subprocess.Popen("command -v yum",shell=True,stdout=subprocess.PIPE)
        result = p.communicate()[0]
        if result != bytes(0):
            install_command = "yum"
        else:
            print("impossible d'exécuter le script sous ce système d'exploitation")
            return
    print("installation des logiciels / biliothèques python nécessaires")
    print("-"*20)
    print("installation de python3-pip")
    completedProcess = aptinstall("python3-pip")
    if completedProcess.returncode:
        print("échec de l'installation de pip")
        liste_echecs.append("python3-pip")
    else:
        print("installation des bibliothèques python requises")
        for bibli in ["django","pexpect","reportlab","unidecode","pillow"]:
            print("-"*20)
            completedProcess = pipinstall(bibli)
            if completedProcess.returncode:
                print("échec de l'installation de " + bibli)
                liste_echecs.append(bibli)
    print("-"*20)
    init = input("Avez-vous initialisé les données du fichier de configuration\n\
        à l'aide de la commande 'python3 manage.py initdata' ?\n\
        Si ce n'est pas le cas, voulez-vous le faire maintenant?\n\
        (très fortement conseillé) o/n: ")
    while init == "" or init not in "oOnN":
        init = input("réponse incorrecte, voulez-vous exécuter l'initialisation\n\
            du fichier de configuration? o/n: ")
    if init in "oO":
        print("initialisation du fichier de configuration")
        completedProcess = subprocess.run(["python3","manage.py","initdata"])
        if completedProcess.returncode:
            print("l'initialisation des données de donfiguration a échoué, il faudra le faire à la main")
        else:
            print("l'initialisation des données de configuration a été effectuée avec succès")
    from ecolle.config import DB_ENGINE, IMAGEMAGICK, DB_PASSWORD
    if IMAGEMAGICK:
        print("-"*20)
        print("installation de ImageMagick")
        completedProcess = aptinstall("imagemagick")
        if completedProcess.returncode:
            print("échec de l'installation d'imagemagick")
            liste_echecs.append("imagemagick")
        else: # configuration (on autorise la conversion des pdfs)
            print("modification de la configuration pour autoriser les conversion des pdfs")
            subprocess.run(["sudo","python3","imagemagick.py"])
    print("-"*20)
    if DB_ENGINE == "postgresql":
        print("installation de postgresql")
        completedProcess = aptinstall("postgresql")
        if completedProcess.returncode:
            print("échec de l'installation de postgresql")
            liste_echecs.append("postgresql")
        print("-"*20)
        print("installation de psycopg2")
        completedProcess = pipinstall("psycopg2")
        if completedProcess.returncode:
            print("échec de l'installation de psycopg2")
            liste_echecs.append("psycopg2")
        elif "pexpect" not in liste_echecs:
            configpostgresl()
    elif DB_ENGINE == "mysql":
        print("installation de mysql")
        completedProcess = aptinstall("mysql-server")
        if completedProcess.returncode:
            print("échec de l'installation de mysql")
            liste_echecs.append("mysql")
        print("-"*20)
        print("installation de mysqlclient")
        completedProcess = aptinstall("libmysqlclient-dev")
        completedProcess = pipinstall("mysqlclient")
        if completedProcess.returncode:
            print("échec de l'installation de mysqlclient")
            liste_echecs.append("mysqlclient")
        elif "pexpect" not in liste_echecs:
            configmysql()
    elif DB_ENGINE == "sqlite3":
        print("installation de sqlite3")
        completedProcess = aptinstall("sqlite3")
        if completedProcess.returncode:
            print("échec de l'installation de sqlite3")
            liste_echecs.append("sqlite3")
        else:
            print("-"*20)
            configsqlite()
    if DB_ENGINE != "sqlite3" and DB_PASSWORD =="":
        print("il faut définir un mot de passe pour la base de données\n\
            initialisation de la base de données impossible")
    else:
        print("début initialisation de la base de données")
        subprocess.run(["python3","manage.py","migrate"])
        print("fin initialisation de la base de données") 
    apache = input("Voulez-vous installer apache comme logiciel pour faire serveur? O/N (N): ")
    if apache != "" and apache in "oO":
        installapache()

    ssl = input("Voulez-vous configurer votre site en ssl avec let's encrypt? o/n (N): ")
    if ssl !="" and ssl in "oO":
        if install_command == "apt":
            subprocess.run(["sudo","add-apt-repository","ppa:certbot/certbot"]) # ajout du ppa de certbot
            subprocess.run(["sudo","apt","update"]) # mise à jour des dépôts pour inclure certbot
            print("installation de certbot")
            subprocess.run(["sudo","apt","install","certbot","python-certbot-apache"]) #installation de certbot
            print("lancement de certbot")
            subprocess.run(["sudo","certbot","--apache"])
        elif install_command == "yum":
            print("installation de certbot")
            subprocess.run(["sudo","dnf","install","certbot","certbot-apache"]) #installation de certbot
            print("lancement de certbot")
            subprocess.run(["sudo","certbot","--apache"])

if __name__== '__main__':
    main()
        
            









