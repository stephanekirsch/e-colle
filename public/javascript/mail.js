lien = document.getElementById("email");
tableau = document.getElementById("suppr");
lien.onclick=function()
	{
		mail();
	}
function mail(){
	var emails = [];
	for (var i = 1, row; row = tableau.rows[i]; i++) {
		if (row.cells[0].firstElementChild.firstElementChild && row.cells[0].firstElementChild.firstElementChild.checked) {
			email = row.cells[4].innerHTML;
			if (email!= "") {
				emails.push(email);
			}
		}
	}
	var mailto = document.createElement('a');
	mailto.href= "mailto:" + emails.join(";"); 
  	mailto.click();
}
