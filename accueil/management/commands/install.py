from django.core.management.base import BaseCommand
import os
import sys
import platform
import subprocess
from time import sleep
from random import choice
from ecolle.config import DB_PASSWORD, DB_NAME

class Command(BaseCommand):
    help = """installe les logiciels nécessaires sous GNU/Linux"""

    def aptinstall(self, package):
    	return subprocess.run(
            ["sudo","apt", "install", package])

    def handle(self, *args, **options):
    	liste_echecs = []
    	liste_echecs_config = []
    	if platform.system().lower() != 'linux':
    		self.stdout.write("cette commande ne fonctionne que sous linux")
    		return
    	if sys.version[:3] < '3.5':
    		self.stdout.write("Il vous faut une version de de Python >= 3.5")
    		return
    	self.stdout.write("installation des logiciels / biliothèques python nécessaires")
    	self.stdout.write("-"*20)
    	self.stdout.write("installation de python3-pip")
    	completedProcess = self.aptinstall("python3-pip")
    	if completedProcess.returncode:
    		self.stdout.write("échec de l'installation de pip")
    		liste_echecs.append("python3-pip")
    	self.stdout.write("-"*20)
    	self.stdout.write("installation de apache2")
    	completedProcess = self.aptinstall("apache2")
    	if completedProcess.returncode:
    		self.stdout.write("échec de l'installation d'apache2")
    		liste_echecs.append("apache2")
    	self.stdout.write("-"*20)
    	self.stdout.write("installation de libapache2-mod-wsgi-py3")
    	completedProcess = self.aptinstall("libapache2-mod-wsgi-py3")
    	if completedProcess.returncode:
    		self.stdout.write("échec de l'installation de libapache2-mod-wsgi-py3")
    		liste_echecs.append("libapache2-mod-wsgi-py3")
    	self.stdout.write("-"*20)
    	if DB_NAME == "postgresql":
    		self.stdout.write("installation de postgresql")
    		completedProcess = self.aptinstall("postgresql")
    		if completedProcess.returncode:
	    		self.stdout.write("échec de l'installation de postgresql")
	    		liste_echecs.append("postgresql")
	    	self.stdout.write("installation de psycopg2")
    		completedProcess = self.aptinstall("python3-psycopg2")
    		if completedProcess.returncode:
	    		self.stdout.write("échec de l'installation de psycopg2")
	    		liste_echecs.append("psycopg2")
	    	else:
	    		self.stdout.write("configuration de la base de données")
	    		

	    		
	    			






        


