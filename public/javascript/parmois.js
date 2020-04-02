var checkbox = document.getElementById("checkbox");
var checkbox2 = document.getElementById("checkbox2");
var tableau=document.getElementById('suppr');
var liensimg = tableau.querySelectorAll("a > img");
for (var i = liensimg.length - 1; i >= 0; i--) {// on désactive tous les liens avec image pour pouvoir capturer les événements
	liensimg[i].parentNode.onclick=function(){return false;}
}
tableau.addEventListener('click',function(e){ 
	var cible=e.target;
	if (cible.nodeName.toLowerCase()=='a' && cible.innerHTML.toLowerCase()=="supprimer")
	{
		cible.onclick=function(){ return confirm('Confirmer la suppression?');} // si on confirme la suppression, on execute le lien.
	} else if (cible.nodeName.toLowerCase()=='img') {
		cible.onclick=function(){ 
			if (!checkbox.checked && !checkbox2.checked){
				cible.parentNode.onclick=function(){return true};
				cible.parentNode.click();
				cible.parentNode.onclick=function(){return false};
			} else {
				var href = cible.parentNode.href;
				var nouveauhref = href;
				var longueur = href.length;
				if (checkbox.checked) {
					var arg = parseInt(href.charAt(longueur-3))+2;
					nouveauhref = href.substring(0,longueur-3) + String(arg) + '/0';
				}
				if (checkbox2.checked)
				{
					nouveauhref = nouveauhref.substring(0,longueur-1) + '1';
				}
				cible.parentNode.href = nouveauhref;
				cible.parentNode.onclick=function(){return true};
				cible.parentNode.click();
				cible.parentNode.href = href;
				cible.parentNode.onclick=function(){return false};
			}
		} 
	}
}
,true);
