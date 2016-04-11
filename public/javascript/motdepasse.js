function alea()
{
    var texte = "";
    var possible = "ABCDEFGHJKLMNOPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz0123456789";

    for( var i=0; i < 10; i++ )
        texte += possible.charAt(Math.floor(Math.random() * possible.length));

    return texte;
}

var csv = false;
var listemdp = document.querySelectorAll("input[id$=motdepasse]");
var listenom = document.querySelectorAll("input[id$=-nom]");
var listeprenom = document.querySelectorAll("input[id$=prenom]");
var listeclasse = document.querySelectorAll("select[id$=classe]");
var listematiere = document.querySelectorAll("select[id$=matiere]");
var matiere = false;
if (listematiere[0]) {
	matiere = true;
}
var titre = document.getElementById('titre');
var td = document.createElement("td");
var lien = document.createElement("a");
lien.innerHTML = "génération aléatoire des mots de passe";
td.appendChild(lien);
lien.href="#";
titre.parentNode.appendChild(td);

function createlien(){
	var td2 = document.createElement("td");
	var lien2 = document.createElement("a");
	lien2.innerHTML = "fichier csv (nom/prenom/mot de passe)";
	td2.appendChild(lien2);
	lien2.href="#";
	titre.parentNode.appendChild(td2);
	lien2.addEventListener('click',function(){
		createcsv();
	},true)
}

function changeMdp(){
	listemdp = document.querySelectorAll("input[id$=motdepasse]");
	for (var i = listemdp.length - 1; i >= 0; i--) {
		listemdp[i].value = alea();
	};
	if (!csv)
	{
		csv = true;
		createlien();
	}
}

lien.addEventListener('click',function(){
	changeMdp();
},false)

function createcsv(){
	var listemdp = document.querySelectorAll("input[id$=motdepasse]");
	var listenom = document.querySelectorAll("input[id$=-nom]");
	var listeprenom = document.querySelectorAll("input[id$=prenom]");
	var listeclasse = document.querySelectorAll("select[id$=classe]");
	var listematiere = document.querySelectorAll("select[id$=matiere]");
	var a = window.document.createElement('a');
	var innerBlob = "nom,prenom";
	if (matiere){
		innerBlob+=",matieres,classes";
	} else {
		innerBlob+=",classe"
	}
	innerBlob+=',mot de passe\n';
	if (matiere){
		for (var i = 0 ; i < listenom.length; i++) {
			innerBlob += listenom[i].value.toUpperCase()+','+listeprenom[i].value.toLowerCase()+',';
			var classes = ""
			for (var j = 0; j<listeclasse[i].options.length; j++) {
				if (listeclasse[i].options[j].selected){
					classes += listeclasse[i].options[j].innerHTML;
					classes += "-";
				}
			};
			classes = classes.slice(0,-1);// on retire le dernier "-"
			var matieres = ""
			for (var j = 0; j<listematiere[i].options.length; j++) {
				if (listematiere[i].options[j].selected){
					matieres += listematiere[i].options[j].innerHTML;
					matieres += "-";
				}
			};
			matieres = matieres.slice(0,-1);// on retire le dernier "-"
			innerBlob+= matieres + ',' + classes + ',' + listemdp[i].value+'\n';
		};
	} else {
		for (var i = 0 ; i < listenom.length; i++) {
		innerBlob += listenom[i].value.toUpperCase()+','+listeprenom[i].value.toLowerCase()+','+listeclasse[i][parseInt(listeclasse[i].selectedIndex)].innerHTML+','+listemdp[i].value+'\n';
		};
	}
	a.href = window.URL.createObjectURL(new Blob([innerBlob], {type: 'text/csv'}));
	a.download = 'test.csv';

	// Append anchor to body.
	document.body.appendChild(a);
	a.click();

	// Remove anchor from body
	document.body.removeChild(a);	
}

