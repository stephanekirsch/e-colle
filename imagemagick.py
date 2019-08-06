import os

contenu = False
succes = False

reps = [f for f in os.listdir("/etc") if not os.path.isfile(f) and f.startswith("ImageMagick")]
if reps:
	with open(os.path.join('/etc',reps[0],'policy.xml'),"rt",encoding="utf8") as fichier:
		contenu = fichier.read()
		contenu = contenu.replace('<policy domain="coder" rights="none" pattern="PDF" />','<policy domain="coder" rights="read|write" pattern="PDF" />')
	if contenu:
		with open(os.path.join('/etc',reps[0],'policy.xml'),"wt",encoding="utf8") as fichier:
			fichier.write(contenu)
			succes = True
if succes:
	print("configuration effectuée avec succès")
else:
	print("configuration échouée, à faire à la main")
