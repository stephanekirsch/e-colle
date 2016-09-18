var selectliste = document.getElementsByTagName("select");
var nbprofs = selectliste.length;
function videSelect() // nettoyage du select du prof principal
{
	for (var i = selectliste[nbprofs-1].length - 1; i > 0; i--)
	{
		selectliste[nbprofs-1].removeChild(selectliste[nbprofs-1][i]);
	}

}
var selected;
function majProfprincipal()
{
	selected = selectliste[nbprofs-1][selectliste[nbprofs-1].selectedIndex].value;
	videSelect();
	colleurvalues = new Array();
	for (var i = 0; i < selectliste.length-1 ; i++)
	{
		var option = selectliste[i][selectliste[i].selectedIndex].cloneNode(true);
		if (option.value != "" && colleurvalues.indexOf(option.value) == -1) // si le professeur n'apparait pas encore dans le select des professeurs principaux, on l'ajoute
		{
			selectliste[nbprofs-1].appendChild(option);
			colleurvalues.push(option.value);
		}	
	}
	indexselectionne = colleurvalues.indexOf(selected);
	if (indexselectionne == -1)
	{
		selectliste[nbprofs-1].selectedIndex=0;
	}
	else
	{
		selectliste[nbprofs-1].selectedIndex = indexselectionne+1;
	}
}
majProfprincipal();

for (var i = 0; i < nbprofs-1; i++)
{
	selectliste[i].addEventListener("change",majProfprincipal,true);
}