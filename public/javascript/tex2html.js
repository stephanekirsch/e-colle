String.prototype.replaceAt=function(index, character, longueur) {
    return this.substr(0, index) + character + this.substr(index+longueur);
}

function replace_b_i(texte)
{
	var indexb = texte.indexOf('\\textbf{');
	if (indexb != -1){
		nbparentheses=1;
		position = indexb+8;
		lettre = texte.charAt(position)
		while (nbparentheses>0 && lettre !="")
		{
			if (lettre == "{")
			{
				nbparentheses++;
			} else if (lettre == "}"){
				nbparentheses--;
			}
			position++;
			lettre = texte.charAt(position);
		}
		if (nbparentheses==0){
			texte=texte.replaceAt(position-1,"</b>",1);
			texte=texte.replace("\\textbf{","<b>");
			return replace_b_i(texte);
		} else {
			return texte;
		}
	}
	var indexi = texte.indexOf('\\textit{');
	if (indexi != -1){
		nbparentheses=1;
		position = indexi+8;
		lettre = texte.charAt(position)
		while (nbparentheses>0 && lettre !="")
		{
			if (lettre == "{")
			{
				nbparentheses++;
			} else if (lettre == "}"){
				nbparentheses--;
			}
			position++;
			lettre = texte.charAt(position);
		}
		if (nbparentheses==0){
			texte=texte.replaceAt(position-1,"</i>",1);
			texte=texte.replace("\\textit{","<i>");
			return replace_b_i(texte);
		} else {
			return texte;
		}
	}
	return texte;
}

function replace_backslah(texte){
	// environnement: 0 = texte, 1 = equation inline, 2= equation block
	environnement = 0;
	position =0;
	lettre = texte.charAt(0);
	while (lettre !="")
	{
		if (lettre == "$"){ // mise à jour de l'environnement
			if (texte.charAt(position+1) == "$"){ // si on a un double $
				environnement = 2- environnement;
				position++;
			} else {
				if (environnement == 2){ // mauvais balisage, donc on s'arrête là.
					return texte;
				} else {
					environnement = 1-environnement;
				} 
			}
		} else if (lettre == "\\" && environnement == 0) {
			if (texte.charAt(position+1) == "\\"){ // si on a un double \\ donc un retour à la ligne
				texte = texte.replaceAt(position,"<br>",2);
				position = position +2;
			} else if (texte.charAt(position+1) == " ") {
				texte = texte.replaceAt(position," ",1);
			}
		 } else if (lettre == '\n' && environnement == 0) {
                texte = texte.replaceAt(position,"<br>",1);
            }
		position++;
		lettre = texte.charAt(position);
	}
	return texte;
}


var programmes = document.getElementsByClassName('prog_colle');
if (!programmes.length)
{
	programmes=document.getElementsByClassName('popup');
}
var n=programmes.length;
for (var i = 0; i < n; i++) {
	var texte=programmes[i].innerHTML;
	texte=texte.replace(/\\begin\{enumerate\}/g,'<ol><li>');
	texte=texte.replace(/\\end\{enumerate\}/g,'</li></ol>');
	texte=texte.replace(/\\begin\{itemize\}/g,'<ul><li>');
	texte=texte.replace(/\\end\{itemize\}/g,'</li></ul>');
	texte=texte.replace(/\\item/g,'</li><li>');
	texte=texte.replace(/<li>[\n|\r|<br>]*<\/li>/g,'');
	texte=texte.replace(/[\n|\r]*<\/li>/g,'</li>');
	texte=texte.replace(/[\n|\r]*<ul>/g,'<ul>');
	texte=texte.replace(/[\n|\r]*<ol>/g,'<ol>');
	texte=texte.replace(/\\([A-Z])(\W)/g,'\\mathbb{$1}$2');
	texte=texte.replace(/\\([A-Z])(\W)/g,'\\mathbb{$1}$2');
	texte=texte.replace(/\\vv/g,'\\vec');
	texte=texte.replace(/<li>[\n|\r|<br>]*<\/li>/g,'');
	texte=texte.replace(/<br>[\n|\r]+<br>/g,'<br>');
	texte=texte.replace(/\\begin\{displaymath\}/g,'\$\$');
	texte=texte.replace(/\\end\{displaymath\}/g,'\$\$');
	programmes[i].innerHTML=replace_backslah(replace_b_i(texte));
};


