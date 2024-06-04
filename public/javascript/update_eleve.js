const compareArrays = (a, b) =>
  a.length === b.length &&
  a.every((element, index) => element === b[index]);

var classes_div = document.getElementById('id_classes');
var eleves_select = document.getElementById('id_eleve');
var url = document.getElementById('geturl').value;
url = url.split("/");
url.pop();
url = url.join("/") + "/";

var classes = new Array();

function videEleve()
{
	var option = eleves_select.firstElementChild;
	while (option!=undefined)
	{
		eleves_select.removeChild(option);
		option = eleves_select.firstElementChild;
	}
}

function majClasses (){
	var old_classes = classes;
	classes = new Array();
	var div1 = classes_div.firstElementChild;
	while (div1 != undefined) {
		input = div1.firstElementChild.firstElementChild;
		if (input.checked) {
			classes = classes.concat([input.value]);
		}
		div1 = div1.nextElementSibling;
	}
	if (!compareArrays(old_classes,classes)) {
		majEleves();
	}
}

function majEleves() {
	var href;
	if (classes.length == 0) {
		href = url + "0"
	} else {
		href = url + classes.join("-");
	}
	xhr=new XMLHttpRequest;
	xhr.onreadystatechange = function() {
		if (xhr.readyState == 4) {
			if (xhr.status==200) 
			{
				var reponsejson=eval('('+xhr.responseText+')');
				videEleve();
				var opt1=document.createElement('option');
				opt1.innerHTML="personne";
				opt1.value="null";
				eleves_select.appendChild(opt1);
				for (var i = 0; i < reponsejson.length; i++)
				{
					var opt=document.createElement('option');
					opt.innerHTML=reponsejson[i]['nom'];
					opt.value=reponsejson[i]['pk'];
					eleves_select.appendChild(opt);
				}
			}
			else
			{
				alert('erreur du serveur');
			} 
		} 
	}	
	xhr.open('GET', href, true);
	xhr.send(null);
}

classes_div.addEventListener('click',function(){ majClasses()} ,false);

