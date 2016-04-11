checkbox = document.getElementById("check");
var liste = document.querySelectorAll("input[type='checkbox'][value]");
var tableaux = document.getElementById("suppr");
var taille = liste.length;
var nbcoche =0
for (var i = liste.length - 1; i >= 0; i--) 
{
	if (liste[i].checked)
	{
		nbcoche++;
	}
};

function verif(){
	if (nbcoche==0)
	{
		checkbox.checked=false;
		checkbox.indeterminate=false;
	}
	else if (nbcoche==taille) 
	{
		checkbox.checked=true;
		checkbox.indeterminate=false;
	}
	else
	{
		checkbox.indeterminate=true;
	}
}
verif();
checkbox.addEventListener("click",function(e){
	if (checkbox.checked)
	{
		for (var i =liste.length - 1; i >= 0; i--) {
			liste[i].checked=true;
		};
		nbcoche=taille;
	}
	else
	{
		for (var i =liste.length - 1; i >= 0; i--) {
			liste[i].checked=false;
		};
		nbcoche=0;
	}
},false);
tableaux.addEventListener("click",function(e){
	if (e.target.nodeName.toLowerCase()=="input" && e.target.type.toLowerCase()=="checkbox" && e.target!=checkbox){
		if (e.target.checked){
			nbcoche++;
		}
		else
		{
			nbcoche--;
		}
	}
	verif();
},false)
