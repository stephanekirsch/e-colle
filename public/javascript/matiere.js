var select=document.getElementById('id_couleur');
var child=select.firstElementChild;
while(child)
{
	child.style.backgroundColor=child.value;
	child=child.nextElementSibling;
}