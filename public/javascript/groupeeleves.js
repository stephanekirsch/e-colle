var tableaueleves = document.getElementById("tableaueleves");
var groupes = document.querySelectorAll("input[id^=id_groupe]");
var listeEleves = document.querySelectorAll("input[id^=id_eleve]");
var listeGroupesEleves = new Array;
for (var i = 0; i < groupes.length; i++) {
	var eleves = new Array;
	var td = groupes[i].parentNode.parentNode;
	for (var j = 0; j < 3; j++) {
		eleves[j] = td.nextElementSibling.firstElementChild.firstElementChild;
		eleves[j].addEventListener('click', function (e) {
			var groupeCheck = e.currentTarget.parentNode.parentNode.parentNode.firstElementChild.firstElementChild.firstElementChild;
			var number = numberChecked(e.currentTarget);
			if (number == 0) {
				groupeCheck.checked = false;
				groupeCheck.indeterminate = false;
			} else if (number == 3) {
				groupeCheck.checked = true;
				groupeCheck.indeterminate = false;
			} else {
				groupeCheck.indeterminate = true;
			}
		}, true);
		td = td.nextElementSibling;
	}
	listeGroupesEleves[i] = eleves;
}

for (var i = groupes.length - 1; i >= 0; i--) {
	groupes[i].addEventListener('click', function (e) {
		selectAll(e.currentTarget, true)
	}, true)
}

function selectAll(target) {
	var check = target.checked; 
	td = target.parentNode.parentNode.nextElementSibling;
	for (var i = 0; i < 3; i++) {
		td.firstElementChild.firstElementChild.checked = check;
		td = td.nextElementSibling;
	}
}

function numberChecked(target) {
	var tr = target.parentNode.parentNode.parentNode;
	var td = tr.firstElementChild.nextElementSibling;
	var number = 0
	for (var i = 0; i < 3; i++) {
		if (td.firstElementChild.firstElementChild.checked) {
			number++;
		}
		td = td.nextElementSibling;
	}
	return number;
}






