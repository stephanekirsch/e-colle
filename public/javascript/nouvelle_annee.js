var tableau=document.getElementById('nouvelle_annee');
if (tableau) {tableau.addEventListener('click',function(e){ 
	var cible=e.target;
	if (cible.nodeName.toLowerCase()=='a')
	{
		cible.onclick=function(){ return confirm('Êtes-vous sûr de vouloir effectuer cette opération? Les suppressions sont irréversibles. Il est fortement conseillé d\'effectuer au préalable une sauvegarde de la base de données.');} // si on confirme on execute le lien.
	}
}
,true)
}
