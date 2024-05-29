// on dégomme toutes les listes déroulantes
var deroul=document.getElementById('niveau2');
var deroul2;
var creneaux=document.getElementById('creneaux')
creneaux.onclick=function(){return false};
deroul.parentNode.removeChild(deroul);
var grise=document.getElementById('grise');
var colleurs=document.getElementById('id_colleur');
var matcolleur=document.getElementById('id_matiere');
var opt=document.createElement('option');
var semestre2=parseInt(document.getElementById('semestre2').value);
var semestres;
var semaine = -1;
if (semestre2 == -1) 
{
	semestres = false;
} else {
	semestres = true;
	deroul2 = document.getElementById('niveau2bis');
	deroul2.parentNode.removeChild(deroul2);
}
opt.innerHTML="Effacer";
opt.value="-1"
matcolleur.appendChild(opt); 
var annul=document.getElementById('annul');
annul.onclick=function(){return false};
var compat=document.getElementById('compat');
compat.onclick=function(){return false};
var trgsc = document.getElementById('id_GSC');
var trcolleur = document.getElementById('id_colleur').parentNode.parentNode;
var treleve = document.getElementById('id_eleve').parentNode.parentNode;
var trgroupe = document.getElementById('id_groupe').parentNode.parentNode;
var trpermu = document.getElementById('id_permutation').parentNode.parentNode;
var dictgroupes = eval('('+document.getElementById('dictgroupes').value+')');
var dictgroupes2;
if (semestres) {
	dictgroupes2 = eval('('+document.getElementById('dictgroupes2').value+')');
}
var selectgroupe = trgroupe.firstElementChild.nextElementSibling.firstElementChild.cloneNode(true);
var dictselectgroupe = new Object();
for (var i in dictgroupes) {
	dictselectgroupe[i] = selectgroupe.cloneNode(true);
	for (var j = dictgroupes[i].length - 1; j >= 0; j--) {
		if (!dictgroupes[i][j])
		{
			dictselectgroupe[i].removeChild(dictselectgroupe[i][j]);
		}
	}
}
if (semestres) {
	var dictselectgroupe2 = new Object();
	for (var i in dictgroupes2) {
		dictselectgroupe2[i] = selectgroupe.cloneNode(true);
		for (var j = dictgroupes2[i].length - 1; j >= 0; j--) {
			if (!dictgroupes2[i][j])
			{
				dictselectgroupe2[i].removeChild(dictselectgroupe2[i][j]);
			}
		}
	}
}
var dicteleves = eval('('+document.getElementById('dicteleves').value+')');
var selecteleve = treleve.firstElementChild.nextElementSibling.firstElementChild.cloneNode(true);
var dictselecteleve = new Object();
for (var i in dicteleves) {
	dictselecteleve[i] = selecteleve.cloneNode(true);
	for (var j = dicteleves[i].length - 1; j >= 0; j--) {
		if (!dicteleves[i][j])
		{
			dictselecteleve[i].removeChild(dictselecteleve[i][j]);
		}
	}
}
var matieres = new Object();
var temps = new Object();
function videColleur()
{
	var option = colleurs.firstElementChild;
	while (option!=undefined)
	{
		colleurs.removeChild(option);
		option = colleurs.firstElementChild;
	}
}

function majColleur()
{
	matiere=matcolleur.value;
	if (matiere != "-1" && matieres[matiere] == undefined)
	{
		var lienajax3=document.getElementById('ajaxcolleur').value.replace('matiere',matiere);
		xhr3=new XMLHttpRequest;
		xhr3.onreadystatechange = function() {
			if (xhr3.readyState == 4) {
				if (xhr3.status==200) 
				{
					var reponsejson=eval('('+xhr3.responseText+')');
					temps[matiere]=reponsejson.splice(0,1)[0];
					matieres[matiere]=reponsejson;
					for (var i = 0; i < reponsejson.length; i++)
					{
						var opt=document.createElement('option');
						opt.innerHTML=reponsejson[i]['nom'];
						opt.value=reponsejson[i]['id'];
						colleurs.appendChild(opt);
					}
					majGroupes();
				}
				else
				{
					alert('erreur du serveur');
				}
			} 
		}		
		xhr3.open('GET' , lienajax3,true);
		xhr3.send(null);
	}
	else
	{
		if (matiere != "-1"){
			for (var i = 0; i < matieres[matiere].length; i++)
			{
				var opt=document.createElement('option');
				opt.innerHTML=matieres[matiere][i]['nom'];
				opt.value=matieres[matiere][i]['id'];
				colleurs.appendChild(opt);
			}
		}
		majGroupes();
	}
}
function majGroupes()
{
	radio = document.querySelector('input[name="GSC"]:checked');
	if (matiere == "-1"){
		trcolleur.style.display="none";
		treleve.style.display="none";
		trgroupe.style.display="none";
		trpermu.style.display="none";
	}
	else if (radio != null) {
		val = radio.value
		if (val == '0')
		{
			trcolleur.style.display="table-row";
			treleve.style.display="none";
			trgroupe.style.display="table-row";
			trpermu.style.display="table-row";
			if (semestres && semestre2 <= semaine) {
				trgroupe.firstElementChild.nextElementSibling.replaceChild(dictselectgroupe2[matiere],trgroupe.firstElementChild.nextElementSibling.firstElementChild);
			} else {
				trgroupe.firstElementChild.nextElementSibling.replaceChild(dictselectgroupe[matiere],trgroupe.firstElementChild.nextElementSibling.firstElementChild);
			}
		}
		else if (val == '2')
		{
			trcolleur.style.display="table-row";
			trgroupe.style.display="none";
			treleve.style.display="none";
			trpermu.style.display="none";
		}
		else
		{
			trcolleur.style.display="table-row";
			trgroupe.style.display="none";
			treleve.style.display="table-row";
			trpermu.style.display="table-row";
			treleve.firstElementChild.nextElementSibling.replaceChild(dictselecteleve[matiere],treleve.firstElementChild.nextElementSibling.firstElementChild);
		}
	}
	
}
majColleur();
matcolleur.addEventListener('change',function(){ videColleur();majColleur()},true);
majGroupes()
trgsc.addEventListener('change', majGroupes
,true);
compat.addEventListener('click',function(){
var lienajax4 = compat.href;
xhr4 = new XMLHttpRequest;
xhr4.onreadystatechange = function() {
	if (xhr4.readyState == 4) {
		if (xhr4.status==200) 
		{
			reponse=xhr4.responseText;
			alert(reponse);
		}
		else
		{
			alert('erreur du serveur');
		} 
	} 
}
xhr4.open('GET' , lienajax4,true);
xhr4.send(null);
},true)

annul.addEventListener('click',function(e){
	grise.parentNode.removeChild(grise);
}
,true)
grise.style.display="block";
grise.parentNode.removeChild(grise);
var corps=document.getElementById('body');
// on recup le tableau qu'on met dans la variable globale 'colles'
var colles = document.getElementById('colloscope');
var semcren;
// on ajoute un événement 'click' au tableau 'colles'
colles.addEventListener('click', function(e) { 
	var cible=e.target;
// si on a cliqué sur un case du tableau du colloscope, on recolle la liste déroulante correspondante on lui collant un 'mouseout' qui la supprime dès qu'on ne la survole plus, et qui supprime l'événement mouseout associé
if (cible.id=='creneaux')
{
	cible.onclick=function(){ return false };
	corps.insertBefore(grise,corps.firstElementChild);
	semcren=cible.parentNode.parentNode.parentNode.id.split('_');
	semaine = parseInt(semcren[0]);
	majGroupes();
}

if (cible.parentNode.parentNode.nodeName.toLowerCase()=='td')
{
// on met les bons liens à la liste déroulante
semcren=cible.parentNode.lastElementChild.id.split("_");
semaine = parseInt(semcren[0]);
if (semestres && semestre2 <= semaine) {
	cible.parentNode.lastElementChild.appendChild(deroul2);
	deroul2.onmouseout=function(event){
	if (event.relatedTarget.parentNode.id!='niveau2bis'&& event.relatedTarget.parentNode.parentNode.id!='niveau2bis'    && event.relatedTarget.parentNode.className!='niveau3' && event.relatedTarget.parentNode.parentNode.className!='niveau4'  && event.relatedTarget.parentNode.className!='niveau4' ) 
	{
		deroul2.parentNode.removeChild(deroul2); deroul2.onmouseout=null;
	}
};
} else {
cible.parentNode.lastElementChild.appendChild(deroul);
deroul.onmouseout=function(event){
	if (event.relatedTarget.parentNode.id!='niveau2'&& event.relatedTarget.parentNode.parentNode.id!='niveau2'    && event.relatedTarget.parentNode.className!='niveau3' && event.relatedTarget.parentNode.parentNode.className!='niveau4'  && event.relatedTarget.parentNode.className!='niveau4' ) 
	{
		deroul.parentNode.removeChild(deroul); deroul.onmouseout=null;
	}
};
}
}
// si on a cliqué sur un lien d'une liste déroulante on désactive le lien et on traite la requête en AJAX pour ne pas avoir à recharger la page.
if (cible.nodeName.toLowerCase()=='a' && cible.parentNode.nodeName.toLowerCase()!='td' && cible.id!='creneaux') 
{ 
	var groupe;
	cible.onclick=function(){ return false };
	lienajax=e.target.href;
	lienajax=lienajax.replace('creneau',semcren[1]);
	lienajax=lienajax.replace('semaine',semcren[0]);
	var caseparent = cible.parentNode.parentNode.parentNode.parentNode;
	var casedepart;
	var contenu=cible.innerHTML.toLowerCase();
	if (contenu=='effacer'){
		casedepart=caseparent.firstElementChild;
		couleur='';
	} else {
		casedepart=caseparent.parentNode.parentNode.parentNode.parentNode.firstElementChild;
		couleur=cible.parentNode.parentNode.parentNode.style.backgroundColor;
	}
	xhr=new XMLHttpRequest;
	xhr.onreadystatechange = function() {
		if (xhr.readyState == 4) {
			if (xhr.status==200) 
			{
				var reponse=xhr.responseText;
				if (reponse=="efface")
				{
					casedepart.innerHTML=":";
					casedepart.style.backgroundColor=couleur;
				}
				else if (reponse=="jour férié")
				{
					alert("Vous ne pouvez pas placer de colle un jour férié!");
				}
				else
				{
					casedepart.style.backgroundColor=couleur;
					casedepart.innerHTML= reponse;
				}
			}
			else
			{
				alert('erreur du serveur');
			} 
		} 
	}	
	xhr.open('GET' , lienajax,true);
	xhr.send(null);
}},true);
grise.firstElementChild.addEventListener('submit',function(e)
{
	radio = document.querySelector('input[name="GSC"]:checked');
	if (radio == null) {
		val = '2';
	} else {
		val = radio.value;
	}
	e.preventDefault();
	var lienajax = grise.firstElementChild.action;
	lienajax=lienajax.replace('creneau',semcren[1]);
	lienajax=lienajax.replace('semaine',semcren[0]);
	var mat = document.getElementById('id_matiere').value;
	var kolleur = document.getElementById('id_colleur').value
	if (mat == "-1") {
		kolleur = "0";
	}
	lienajax=lienajax.replace('matiere', mat);
	lienajax=lienajax.replace('kolleur', kolleur);
	var groupe = document.getElementById('id_groupe').value;
	if (!(val == '0' & groupe != "")){
		groupe = '0'
	}
	lienajax=lienajax.replace('groupe', groupe);
	var eleve = document.getElementById('id_eleve').value;
	if (!(val == '1' & eleve != "")){
		eleve = '0';
	}
	lienajax=lienajax.replace('eleve', eleve);
	lienajax=lienajax.replace('duree',document.getElementById('id_duree').value);
	lienajax=lienajax.replace('frequence',document.getElementById('id_frequence').value);
	lienajax=lienajax.replace('permu',document.getElementById('id_permutation').value);
	console.log(lienajax)
	xhr=new XMLHttpRequest;
	xhr.onreadystatechange = function() {
		if (xhr.readyState == 4) {
			if (xhr.status==200) 
			{
				var reponse = xhr.responseText;
				if (isNaN(parseInt(reponse.split("_")[0])))
				{
					grise.parentNode.removeChild(grise);
					var reponsejson=eval('('+xhr.responseText+')');
					var creneau = reponsejson.creneau;
					if ("couleur" in reponsejson) {
					var couleur = reponsejson.couleur;
					var colleur = reponsejson.colleur;
					for (var i = 0; i < semgroupe.length; i++)
					{
						var colle=document.getElementById(semgroupe[i].semaine+'_'+creneau).parentNode.firstElementChild;
						colle.innerHTML=colleur+":"+semgroupe[i].groupe;
						colle.style.backgroundColor=couleur;
					} 
				} else {
					for (var i = 0; i < semgroupe.length; i++)
					{
						var colle=document.getElementById(semgroupe[i].semaine+'_'+creneau).parentNode.firstElementChild;
						colle.innerHTML=":"
						colle.style.backgroundColor="";
					} 
				}
				}
				else
				{
					nombres = reponse.split("_");
					alerte="";
					if (nombres[0]!="0")
					{
						alerte+="vous etes sur le point d'écraser "+nombres[0]+" créneau(x) existant(s)\n";
					}
					if (nombres[1]!="0")
					{
						alerte+="\n"+nombres[1]+" créneau(x) tombe(nt) sur un jour férié\n";
					}
					if (nombres[2]!="")
					{
						alerte+=nombres[2];
					}
					alerte+="\nVoulez-vous poursuivre?";
					if (reponse == "0_0_" || confirm(alerte))
					{
						lienajax2=lienajax.replace('multi','multi/confirm');
						xhr2=new XMLHttpRequest;
						xhr2.onreadystatechange = function() {
							if (xhr2.readyState == 4) {
								grise.parentNode.removeChild(grise);
								if (xhr2.status==200) 
								{
									var reponsejson=eval('('+xhr2.responseText+')');
									var creneau = reponsejson.creneau;
									var semgroupe = reponsejson.semgroupe;
									if ("couleur" in reponsejson) {
										var couleur = reponsejson.couleur;
										var colleur = reponsejson.colleur;
										for (var i = 0; i < semgroupe.length; i++)
										{
											var colle=document.getElementById(semgroupe[i].semaine+'_'+creneau).parentNode.firstElementChild;
											colle.innerHTML=colleur+":"+semgroupe[i].groupe;
											colle.style.backgroundColor=couleur;
										} 
									} else {
										for (var i = 0; i < semgroupe.length; i++)
										{
											var colle=document.getElementById(semgroupe[i].semaine+'_'+creneau).parentNode.firstElementChild;
											colle.innerHTML=":"
											colle.style.backgroundColor="";
										} 
									}
								}
								else
								{
									alert('erreur du serveur');
								}
							}}
							xhr2.open('GET' , lienajax2,true);
							xhr2.send(null);
						}
					}
				}
				else
				{
					alert('erreur du serveur');
				} 
			}}
			xhr.open('GET' , lienajax,true);
			xhr.send(null);
		},
true);
