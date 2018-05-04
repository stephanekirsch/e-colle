#!/bin/bash
CHEMINBACKUP="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )" # chemin absolu vers l'intérieur du répertoire backup
CHEMINECOLLE="$(dirname "$CHEMINBACKUP")" # chemin absolu vers l'intérieur du répertoire e-colle

python3 "$CHEMINECOLLE/manage.py" dumpdata --exclude=auth --exclude=contenttypes --exclude=sessions --format json > ecolle.json

xz -f9 "ecolle.json"
jour=`date "+%w"`
jourmois=`date "+%d"`
mois=`date "+%m"`
nomfichierjour="ecolle_$jour.json.xz"
cp ecolle.json.xz "$CHEMINBACKUP/jour/$nomfichierjour"
if [[ $jour = "6" && $jourmois < 29 ]]
then
	let "semmois= 10#$jourmois /7"
	nomfichiersem="ecolle_$semmois"_"$mois.json.xz"
	rm -f "$CHEMINBACKUP/semaine/ecolle_$semmois"
	cp ecolle.json.xz "$CHEMINBACKUP/semaine/$nomfichiersem"
fi
if [[ $jourmois = "01" ]]
then
	nomfichiermois="ecolle_$mois.json.xz"
	cp ecolle.json.xz "$CHEMINBACKUP/mois/$nomfichiermois"
fi
rm -f ecolle.json.xz
