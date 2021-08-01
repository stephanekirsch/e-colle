var select10 = document.getElementById("id_eleve0");
var select11 = document.getElementById("id_eleve1");
var select12 = document.getElementById("id_eleve2");
var select1 = [select10, select11, select12];
var select20 = document.getElementById("id_eleve20");
var select21 = document.getElementById("id_eleve21");
var select22 = document.getElementById("id_eleve22");
var select2 = [select20, select21, select22];
var lv1select = document.getElementById("id_lv11");
var lv2select = document.getElementById("id_lv21");
var lv1select2 = document.getElementById("id_lv12");
var lv2select2 = document.getElementById("id_lv22");
var optionmatiereselect = document.getElementById("id_option");
var idem = document.getElementById("id_idem");
var selectFull = select10.cloneNode(true); // la liste pleine des élèves
var selectFull2 = select20.cloneNode(true); // la liste pleine des élèves
var selectCourant; // la liste "courante" des élèves (fonction de la/les langue(s) sélectionnée(s))
var eleves = eval('('+document.getElementById("hide").value+')'); // la liste de tous les élèves (via leur id) de la classe ainsi que de leur(s) éventuelle(s) langues


idem.addEventListener('change',function(){
	if (this.checked) {
		recopie();
	}
	},true)

function recopie() {
	for (var i = 0; i < 3; i++){
		var eleve_id = select1[i][select1[i].selectedIndex].value;
		for (var j = 0; j < select2[i].length; j++) {
			if (select2[i][j].value == eleve_id) {
				select2[i].selectedIndex = j;
			}
		}
	}
}


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
	var current;
	var parent;
	for (var i = 0; i < 3; i++) {
		current = select1[i];
		selectCourant.id="id_eleve"+String(i);
		selectCourant.name="eleve"+String(i);
		parent = current.parentNode;
		var eleve_id = parent.lastElementChild.value;
		select1[i] = selectCourant.cloneNode(true);
		parent.replaceChild(select1[i] ,current);
		if (eleve_id == "") {
			parent.lastElementChild.selectedIndex = 0;
		} else {
			for (var j = parent.lastElementChild.length - 1; j > 0; j--) {
				if (parent.lastElementChild[j].value == parseInt(eleve_id))
				{
					parent.lastElementChild.selectedIndex = j;
				}
			}
		}
	}
}

majLangues();

if (lv1select != null)
{
	lv1select.addEventListener('change',function(){
		majLangues();
	},true)
}

if (lv2select != null)
{
	lv2select.addEventListener('change',function(){
		majLangues();
	},true)
}


function maj2Langues() // mise à jour du selectCourant en fonction des langues sélectionnées
{
	var lv12 = lv1select2==null?null:parseInt(lv1select2.value);
	var lv22 = lv2select2==null?null:parseInt(lv2select2.value);
	var optionmatiere = optionmatiereselect==null?null:parseInt(optionmatiereselect.value);
	selectCourant = selectFull2.cloneNode(true);
	for (var i = selectFull2.length - 1; i > 0; i--)
	{
		if ((lv12 && eleves[i-1][1] != lv12) || (lv22 && eleves[i-1][2] != lv22) || (optionmatiere && eleves[i-1][3] != optionmatiere))
		{
			selectCourant.removeChild(selectCourant[i]);
		}
	}
	maj2SelectLangues();
}


function maj2SelectLangues() // met à jour les listes déroulantes des selects
{
	var current;
	var parent;
	for (var i = 0; i < 3; i++) {
		current = select2[i];
		selectCourant.id="id_eleve2"+String(i);
		selectCourant.name="eleve2"+String(i);
		parent = current.parentNode;
		var eleve_id = parent.lastElementChild.value;
		select2[i] = selectCourant.cloneNode(true);
		parent.replaceChild(select2[i] ,current);
		if (eleve_id == "") {
			parent.lastElementChild.selectedIndex = 0;
		} else {
			for (var j = parent.lastElementChild.length - 1; j > 0; j--) {
				if (parent.lastElementChild[j].value == parseInt(eleve_id))
				{
					parent.lastElementChild.selectedIndex = j;
				}
			}
		}
	}
}

maj2Langues();

if (lv1select2 != null)
{
	lv1select2.addEventListener('change',function(){
		maj2Langues();
	},true)
}

if (lv2select2 != null)
{
	lv2select2.addEventListener('change',function(){
		maj2Langues();
	},true)
}

if (optionmatiereselect != null)
{
	optionmatiereselect.addEventListener('change',function(){
		maj2Langues();
	},true)
}

