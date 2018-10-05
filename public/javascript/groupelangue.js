var selectTableau = document.getElementById("id_eleve0").parentNode;
// selectTableau[0] = document.getElementById("id_eleve0");
// selectTableau[1] = document.getElementById("id_eleve1");
// selectTableau[2] = document.getElementById("id_eleve2");
var lv1select = document.getElementById("id_lv1");
var lv2select = document.getElementById("id_lv2");

var selectFull = selectTableau.lastElementChild.cloneNode(true); // la liste pleine des élèves
var selectCourant; // la liste "courante" des élèves (fonction de la/les langue(s) sélectionnée(s))
var eleves = eval('('+document.getElementById("hide").value+')'); // la liste de tous les élèves (via leur id) de la classe ainsi que de leur(s) éventuelle(s) langues


function majLangues() // mise à jour du selectCourant en fonction des langues sélectionnées
{
	var lv1 = lv1select==null?null:parseInt(lv1select.value);
	var lv2 = lv2select==null?null:parseInt(lv2select.value);
	selectCourant = selectFull.cloneNode(true);
	for (var i = selectFull.length - 1; i > 0; i--)
	{
		if ((lv1 && eleves[i-1][1] != lv1) || (lv2 && eleves[i-1][2] != lv2))
		{
			selectCourant.removeChild(selectCourant[i]);
		}
	}
	majSelectLangues();
}


function majSelectLangues() // met à jour les listes déroulantes des selects
{
	var current = selectTableau;
	for (var i = 0; i < 3; i++) {
		selectCourant.id="id_eleve"+String(i);
		selectCourant.name="eleve"+String(i);
		var eleve_id = current.lastElementChild.value;
		current.replaceChild(selectCourant.cloneNode(true),current.lastElementChild);
		if (eleve_id == "") {
			current.lastElementChild.selectedIndex = 0;
		} else {
			for (var j = current.lastElementChild.length - 1; j > 0; j--) {
				if (current.lastElementChild[j].value == parseInt(eleve_id))
				{
					current.lastElementChild.selectedIndex = j;
				}
			}
		}
		current = current.parentNode.nextElementSibling.firstElementChild.nextElementSibling;
	}
}

majLangues();

if (lv1select != null)
{
	lv1select.addEventListener('change',function(){
		majLangues();
	},true)
}
