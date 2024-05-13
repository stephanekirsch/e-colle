var tableau=document.getElementById('suppr');
if (tableau) {tableau.addEventListener('click',function(e){ 
	var cible=e.target;
	if (cible.nodeName.toLowerCase()=='a' && (cible.innerHTML.toLowerCase()=="se désinscrire" || cible.innerHTML=="S"))
	{
		cible.onclick=function(){ return confirm('Confirmer la désinscription?');} // si on confirme on execute le lien.
	}
}
,true)
}
