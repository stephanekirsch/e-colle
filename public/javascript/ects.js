var form = document.getElementById('form');
var tableau=document.getElementById('ects');
var liens = tableau.getElementsByTagName('a');
//on désactive tous les liens:
for (var i = liens.length - 1; i >= 0; i--) {
	liens[i].onclick=function(){return false;}
}
tableau.addEventListener('click',function(e){ 
	var cible=e.target.parentNode;
	if (cible.nodeName.toLowerCase()=='a')
	{
		// si on clique sur un lien, on soumet le formulaire avec l'url du lien, comme ça on peut récupérer les variables POST du formulaire.
		form.action=cible.href;
		form.submit();
	}
}
,true)
