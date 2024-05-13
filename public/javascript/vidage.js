var tableau=document.getElementById('suppr');
if (tableau) {tableau.addEventListener('click',function(e){ 
	var cible=e.target;
	if (cible.nodeName.toLowerCase()=='a' && (cible.innerHTML.toLowerCase()=="vider" || cible.innerHTML=="V") || cible.value.toLowerCase()=="vider la sélection")
	{
		cible.onclick=function(){ return confirm('Confirmer le vidage?');} // si on confirme on execute le lien.
	}
}
,true)
}
