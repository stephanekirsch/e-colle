
function maj(tableau,num) // mise à jour des id/for du nouveau tableau
{
	var tabinput = tableau.getElementsByTagName("input"); // on récupère les inputs du tableau
	for (var i = tabinput.length - 1; i >= 0; i--) {
		tabinput[i].id=tabinput[i].id.replace(/form-\d+-/ ,"form-"+String(num)+"-");
		tabinput[i].name=tabinput[i].name.replace(/form-\d+-/ ,"form-"+String(num)+"-");
		tabinput[i].value=""; // on efface les données du tableau
	};
	var tablabel = tableau.getElementsByTagName("label"); // on récupère les labels du tableau
	for (var i = tablabel.length - 1; i >= 0; i--) {
		tablabel[i].htmlFor=tablabel[i].htmlFor.replace(/form-\d+-/ ,"form-"+String(num)+"-");
	};
	var tabselect = tableau.getElementsByTagName("select"); // on récupère les selects du tableau
	for (var i = tabselect.length - 1; i >= 0; i--) {
		tabselect[i].id=tabselect[i].id.replace(/form-\d+-/ ,"form-"+String(num)+"-");
		tabselect[i].name=tabselect[i].name.replace(/form-\d+-/ ,"form-"+String(num)+"-");
	};
	var tabul= tableau.getElementsByTagName("ul"); // on récupère les éventuels messages d'erreur et on les supprime
	for (var i = tabul.length - 1; i >= 0; i--) {
		tabul[i].parentNode.removeChild(tabul[i]);
	};
}

var bouton = document.getElementById("ajout");
bouton.onclick=function(){return false;};
var totalForm = document.getElementById("id_form-TOTAL_FORMS");
var nbForm = 1;
var tableau = document.getElementById("ajouttab");
tableau.id="";
var formulaire = document.getElementById("formajout");
var tableaubis=tableau
bouton.addEventListener("click",function(e){
	var ligneinput = tableaubis.firstElementChild.lastElementChild;
	ligneinput.parentNode.removeChild(ligneinput);
	tableaubis = tableau.cloneNode(true);
	maj(tableaubis,nbForm++);
	tableaubis.firstElementChild.appendChild(ligneinput);
	formulaire.appendChild(tableaubis);
	totalForm.value=nbForm;
},false)
