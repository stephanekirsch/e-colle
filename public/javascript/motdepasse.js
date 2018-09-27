function alea()
{
    var texte = "";
    var possible = "ABCDEFGHJKLMNOPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz0123456789";

    for( var i=0; i < 10; i++ )
        texte += possible.charAt(Math.floor(Math.random() * possible.length));

    return texte;
}

var csv = false;
var listemdp = document.querySelectorAll("input[id$=password]");
var listenom = document.querySelectorAll("input[id$=last_name]");
var listeprenom = document.querySelectorAll("input[id$=first_name]");
var listeidentifiant = document.querySelectorAll("input[id$=username]");
var listeclasse = document.querySelectorAll("select[id$=classe]");
var listematiere = document.querySelectorAll("select[id$=matiere]");
var matiere = false;
if (listematiere[0]) {
	matiere = true;
}
var titre = document.getElementById('titre');
var td = document.createElement("td");
var lien = document.createElement("a");
lien.innerHTML = "générer mots de passe";
td.appendChild(lien);
lien.href="#";
titre.parentNode.appendChild(td);
var td2 = document.createElement("td");
var lien2 = document.createElement("a");
lien2.innerHTML = "générer identifiants";
td2.appendChild(lien2);
lien2.href="#";
titre.parentNode.appendChild(td2);


function createlien(){
	var td2 = document.createElement("td");
	var lien2 = document.createElement("a");
	lien2.innerHTML = "fichier csv";
	td2.appendChild(lien2);
	lien2.href="#";
	titre.parentNode.appendChild(td2);
	lien2.addEventListener('click',function(){
		createcsv();
	},true)
}

function changeMdp(){
	listemdp = document.querySelectorAll("input[id$=password]");
	for (var i = listemdp.length - 1; i >= 0; i--) {
		listemdp[i].value = alea();
	};
	if (!csv)
	{
		csv = true;
		createlien();
	}
}

function createUsername(){
	// on recrée les listes qui ont pu gagner des éléments
	listenom = document.querySelectorAll("input[id$=last_name]");
	listeprenom = document.querySelectorAll("input[id$=first_name]");
	listeidentifiant = document.querySelectorAll("input[id$=username]");
	for (var i = 0; i < listeidentifiant.length; i++) {
		listeidentifiant[i].value = (listeprenom[i].value.toLowerCase()+"."+listenom[i].value.toLowerCase()).replace(/ /g,"-").replace(/'/g,"");
	}
}

lien.addEventListener('click',function(){
	changeMdp();
},false)

lien2.addEventListener('click',function(){
	createUsername();
},false)

function createcsv(){
	var listemdp = document.querySelectorAll("input[id$=password]");
	var listenom = document.querySelectorAll("input[id$=last_name]");
	var listeprenom = document.querySelectorAll("input[id$=first_name]");
	var listeidentifiant = document.querySelectorAll("input[id$=username]");
	var listeclasse = document.querySelectorAll("select[id$=classe]");
	var listematiere = document.querySelectorAll("select[id$=matiere]");
	var a = window.document.createElement('a');
	var innerBlob = "nom,prenom,identifiant";
	if (matiere){
		innerBlob+=",matieres,classes";
	} else {
		innerBlob+=",classe"
	}
	innerBlob+=',mot de passe\n';
	if (matiere){
		for (var i = 0 ; i < listenom.length; i++) {
			innerBlob += listenom[i].value.toUpperCase()+','+listeprenom[i].value.toLowerCase()+','+listeidentifiant[i].value+',';
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
		innerBlob += listenom[i].value.toUpperCase()+','+listeprenom[i].value.toLowerCase()+','+listeidentifiant[i].value+','+listeclasse[i][parseInt(listeclasse[i].selectedIndex)].innerHTML+','+listemdp[i].value+'\n';
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

