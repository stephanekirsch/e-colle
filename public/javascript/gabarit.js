var widgets1=document.getElementsByClassName("to_hide1");
var widgets2=document.getElementsByClassName("to_hide2");
var gabarit=document.getElementById("gabarit").firstElementChild;

function change()
{
	if (gabarit.checked) 
	{
		for (var i = widgets2.length - 1; i >= 0; i--) {
			widgets2[i].style.display="none";
		}
		for (var i = widgets1.length - 1; i >= 0; i--) {
			widgets1[i].style.display="table-row";
		}
	}
	else
	{
		for (var i = widgets2.length - 1; i >= 0; i--) {
			widgets2[i].style.display="table-row";
		}
		for (var i = widgets1.length - 1; i >= 0; i--) {
			widgets1[i].style.display="none";
		}
	}	
}
change();
gabarit.addEventListener("change",change,true);
