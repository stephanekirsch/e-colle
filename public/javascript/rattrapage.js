checkbox = document.getElementById("id_rattrapee");
rattrapage = checkbox.parentNode.parentNode.nextElementSibling;
if (!checkbox.checked)
{
	rattrapage.hidden=true;
}
checkbox.addEventListener("change",function(){
		if (checkbox.checked)
		{
			rattrapage.hidden=false;
		}
		else
		{
			rattrapage.hidden=true;
		}
},true)
