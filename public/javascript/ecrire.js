//--------------------------------------------------------------------RÉCUPÉRATION DES CHECKBOX ---------------------------------------------------------

var objUser = document.querySelectorAll("ul[id^=id_classe]"); // on met toutes les listes d'utilisateurs (profs,colleur,groupe) dans listeUser
var listeUser = new Array();
for(var i=-1,l=objUser.length;++i!==l;listeUser[i]=objUser[i]);

var objmatieres = document.querySelectorAll("input[id^=id_matiere]"); // on met tous les checkbox: "Profs"/"Élève"/ "nom de matière" dans listeNiveau1
var listeNiveau1 = new Array();
for(var i=-1,l=objmatieres.length;++i!==l;listeNiveau1[i]=objmatieres[i]);

var objclassematieres = document.querySelectorAll("input[id^=id_classematiere]"); // on met tous les checkbox de colleurs dans listeColleurs
var listeColleurs = new Array();
for(var i=-1,l=objclassematieres.length;++i!==l;listeColleurs[i]=objclassematieres[i]);

var objcolleurs = document.querySelectorAll("input[id^=id_colleurs]");
var listeNiveau2 = new Array();
for(var i=-1,l=objcolleurs.length;++i!==l;listeNiveau2[i]=objcolleurs[i]); // on met tous les checkbox: "Colleurs" dans listeNiveau2

var objdivcolleurs = document.querySelectorAll("div[id^=id_divmatiere]");
var listeColleursMatiere = new Array();
for(var i=-1,l=objdivcolleurs.length;++i!==l;listeColleursMatiere[i]=objdivcolleurs[i]); // on met les div englobant les matieres/colleurs d'une classe dans listeColleursMatiere
var tailles = new Array();
var nbcoches = new Array();

for (var i = 0; i < listeUser.length; i++) {
	tailles[i] = listeUser[i].children.length;
	nbcoches[i]=0;
};


// ---------------------------------------------------------------------- AJOUT DES ÉVÉNEMENTS ET DES BOUTONS --------------------------------------------

for (var i = 0; i < listeNiveau2.length; i++) {
	listeNiveau2[i].addEventListener("click",function(e){majColleur(listeNiveau2.indexOf(e.currentTarget))},true)
	listeColleursMatiere[i].hidden=true;
	var bouton = document.createElement('button');
	bouton.innerHTML="Détails";
	bouton.onclick=function(){return false;}
	bouton.addEventListener('click',function(e){cacheCache(e),true})
	listeNiveau2[i].parentNode.appendChild(bouton);
};

for (var i = listeNiveau1.length - 1; i >= 0; i--) {
	listeNiveau1[i].addEventListener('click',function (e){ coche(listeNiveau1.indexOf(e.currentTarget),true)},true);
	listeUser[i].hidden=true;
	var bouton = document.createElement('button');
	bouton.innerHTML="Détails";
	bouton.onclick=function(){return false;}
	bouton.addEventListener('click',function(e){cacheCache(e),true})
	listeNiveau1[i].parentNode.appendChild(bouton);
	listeUser[i].addEventListener('click',function (e){ if (e.target.nodeName.toLowerCase()=='input') {majCoche(listeUser.indexOf(e.target.parentNode.parentNode.parentNode))}},true)
};

for (var i = 0; i < listeUser.length; i++) { // mise à jour des checkbox de niveau 1
	majCoche(i);
};

// ----------------------------------------------------------------------FONCTIONS----------------------------------------------------------

function cacheCache(e) // pour afficher/ cacher les sous-listes en cliquant sur les boutons détails
{
	liste = e.currentTarget.parentNode.nextElementSibling;
	if (liste.hidden==true)
	{
		liste.hidden=false;
		e.currentTarget.innerHTML="Masquer Détails";
	}
	else
	{
		liste.hidden=true;
		e.currentTarget.innerHTML="Détails";
	}
}

function majColleur(i) // sélectionne ou déselectionne toutes les matières d'une classe quand on clique sur "Colleur"
{
	var div=listeColleursMatiere[i].firstElementChild;
	while (div)
	{
		var input = div.firstElementChild;
		input.checked=listeNiveau2[i].checked;
		input.indeterminate=false;
		coche(listeNiveau1.indexOf(input));
		div=div.nextElementSibling.nextElementSibling;
	}
}

function coche(i,majParent=false) // sélectionne ou désélectionne tous les colleurs d'une classe et d'une matière quand on clique sur la matière (ou par propagation quand on clique sur "Colleur")
{
	var coChe = listeNiveau1[i].checked;
	var check = listeUser[i].firstElementChild;
	if (check) 
	{
		check = check.firstElementChild.firstElementChild;
	}
	while (check)
	{
		check.checked=coChe;
		check = check.parentNode.parentNode.nextElementSibling;
		if (check)
		{
			check=check.firstElementChild.firstElementChild;
		}
	}
	var j = listeColleursMatiere.indexOf(listeUser[i].parentNode)
	if (majParent && j != -1)
	{
		majCheckColleur(j);
	}
}

function majCoche(i) // mise à jour des checkbox de niveau 1
{
	nbcoches[i]=0;
	var check = listeUser[i].firstElementChild;
	if (check)
	{
		check = check.firstElementChild.firstElementChild;
	}
	while (check)
	{
		if (check.checked==true)
		{
			nbcoches[i]++;
		}
		check = check.parentNode.parentNode.nextElementSibling;
		if (check)
		{
			check=check.firstElementChild.firstElementChild;
		}
	}
	var check = listeNiveau1[i];
	if (nbcoches[i]==0)
	{
		check.indeterminate=false;
		check.checked=false;
	}
	else if (nbcoches[i]==tailles[i])
	{
		check.indeterminate=false;
		check.checked=true;
	}
	else
	{
		check.indeterminate=true;
	}
	var j=listeColleursMatiere.indexOf(listeUser[i].parentNode);
	if (j != -1)
	{
		majCheckColleur(j);
	}
}

function majCheckColleur(j)
{
	var tout = true;
	var rien = true;
	var div = listeColleursMatiere[j].firstElementChild;
	while (div)
	{
		var input = div.firstElementChild;
		if (input.indeterminate)
		{
			tout=false;
			rien=false;
			break;
		}
		else if (input.checked) 
		{
			rien = false;
		}
		else
		{
			tout = false;
		}
		div = div.nextElementSibling.nextElementSibling;
	}
	if (tout)
	{
		listeNiveau2[j].indeterminate = false;
		listeNiveau2[j].checked = true;
	}
	else if (rien) 
	{
		listeNiveau2[j].indeterminate = false;
		listeNiveau2[j].checked = false;
	}
	else
	{
		listeNiveau2[j].indeterminate = true;
	}
}



