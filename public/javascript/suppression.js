var tableau=document.getElementById('suppr');
if (tableau) {tableau.addEventListener('click',function(e){ 
	var cible=e.target;
	if (cible.nodeName.toLowerCase()=='a' && (cible.innerHTML.toLowerCase()=="supprimer" || cible.innerHTML=="S") || cible.value.toLowerCase()=="supprimer la sélection")
	{
		cible.onclick=function(){ return confirm('Confirmer la suppression?');} // si on confirme on execute le lien.
	}
}
,true)
}
