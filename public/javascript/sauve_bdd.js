var td=document.getElementById('sauve_bdd');
td.addEventListener('click', function(e){
	console.log("cliquage")
	var cible = e.target
	if (cible.nodeName.toLowerCase()=='a'){
		cible.onclick = function(){return false}; // on désactive le lien
		if (confirm("Voulez-vous aussi sauvegarder les fichiers média?")) {
			cible.href = cible.href.substring(0,cible.href.length-1) + "1";
		}
		cible.onclick = function() {return true};// on réactive le lien
	}
}, false)


