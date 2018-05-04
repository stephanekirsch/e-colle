var modifprofcol = document.getElementById('id_modif_prof_col');
var modifprofgroupe = document.getElementById('id_modif_prof_groupe');
var ects = document.getElementById('id_ects');
var trmodifprofcol = document.getElementById('id_default_modif_col').parentNode.parentNode;
var trmodifprofgroupe = document.getElementById('id_default_modif_groupe').parentNode.parentNode;
var ects1 = ects.parentNode.parentNode.nextElementSibling;
var ects2 = ects1.nextElementSibling;
var ects3 = ects2.nextElementSibling;

function majcol()
{
	trmodifprofcol.style.display=modifprofcol.checked?'table-row':'none';
}
function majgroupe()
{
	trmodifprofgroupe.style.display=modifprofgroupe.checked?'table-row':'none';
}
function majects()
{
	if (ects.checked)
	{	
		ects1.style.display = 'table-row';
		ects2.style.display = 'table-row';
		ects3.style.display = 'table-row';
	}
	else
	{
		ects1.style.display = 'none';
		ects2.style.display = 'none';
		ects3.style.display = 'none';
	}
}
majcol();
majgroupe();
majects();

modifprofcol.addEventListener('change',function(){majcol()},true);
modifprofgroupe.addEventListener('change',function(){majgroupe()},true);
ects.addEventListener('change',function(){majects()},true);