from django.db import models

class Matiere(models.Model):
    LISTE_COULEURS=(
        ('#696969',"Gris mat"),('#808080',"Gris"),('#A9A9A9',"Gris foncé"),
        ('#C0C0C0',"Gris argent"),('#D3D3D3',"Gris clair"),('#DCDCDC',"Gris Gainsboro"),
        ('#FFC0CB',"Rose"),('#FFB6C1',"Rose clair"),('#FF69B4',"Rose passion"),
        ('#FF1493' ,"Rose profond"),('#DB7093',"Violet Pâle"),('#FF00FF',"Fushia"),
        ('#C71585',"Violet moyen"),('#D8BFD8',"Violet chardon"),('#DDA0DD',"Prune"),
        ('#EE82EE',"Violet"),('#DA70D6',"Orchidée"),('#9932CC',"Orchidée foncé"),
        ('#9400D3',"Violet foncé"),('#8A2BE2',"Bleu violet"),('#4B0082',"Indigo"),
        ('#7B68EE',"Bleu ardoise moyen"),('#6A5ACD',"Bleu ardoise"),('#483D8B',"Bleu ardoise foncé"),
        ('#9370DB',"Pourpre moyen"),('#8B008B',"Magenta foncé"),('#800080',"Pourpre"),
        ('#BC8F8F',"Brun rosé"),('#F08080',"Corail clair"),('#FF7F50',"Corail"),
        ('#FF6347',"Tomate"),('#FF4500',"Orangé"),('#FF0000',"Rouge"),
        ('#DC143C',"Rouge cramoisi"),('#FFA07A',"Saumon clair"),('#E9967A',"Saumon foncé"),
        ('#FA8072',"Saumon"),('#CD5C5C',"Rouge indien"),('#B22222',"Rouge brique"),
        ('#A52A2A',"Marron"),('#8B0000',"Rouge foncé"),('#800000',"Bordeaux"),
        ('#DEB887',"Brun bois"),('#D2B48C',"Brun roux"),('#F4A460',"Brun sable"),
        ('#FFA500',"Orange"),('#FF8C00',"Orange foncé"),('#D2691E',"Chocolat"),
        ('#CD853F',"Brun péro"),('#A0522D',"Terre de Sienne"),('#8B4513',"Brun cuir"),
        ('#F0E68C',"Brun kaki"),('#FFFF00',"Jaune"),('#FFD700',"Or"),
        ('#DAA520',"Jaune doré"),('#B8860B',"Jaune doré foncé"),('#BDB76B',"Brun kaki foncé"),
        ('#9ACD32',"Jaune vert"),('#6B8E23',"Kaki"),('#808000',"Olive"),
        ('#556B2F',"Olive foncé"),('#ADFF2F',"Vert jaune"),('#7FFF00',"Chartreuse"),
        ('#7CFC00',"Vert prairie"),('#00FF00',"Cirton vert"),('#32CD32',"Citron vers foncé"),
        ('#98FB98',"Vert pâle"),('#90EE90',"Vert clair"),('#00FF7F',"Vert printemps"),
        ('#00FA9A',"Vert printemps mpyen"),('#228B22',"Vert forêt"),('#008000',"Vert"),
        ('#006400',"Vert foncé"),('#8FBC8F',"Vert océan foncé"),('#3CB371',"Vert océan moyen"),
        ('#2E8B57',"Vert océan"),('#778899',"Gris aroise clair"),('#708090',"Gris ardoise"),
        ('#2F4F4F',"Gris ardoise foncé"),('#7FFFD4',"Aigue-marine"),('#66CDAA',"Aigue-marine moyen"),
        ('#00FFFF',"Cyan"),('#40E0D0',"Turquoise"),('#48D1CC',"Turquoise moyen"),
        ('#00CED1',"Turquoise foncé"),('#20B2AA',"Vert marin clair"),('#008B8B',"Cyan foncé"),
        ('#008080',"Vert sarcelle"),('#5F9EA0',"Bleu pétrole"),('#B0E0E6',"Bleu poudre"),
        ('#ADD8E6',"Bleu clair"),('#87CEFA',"Bleu azur clair"),('#87CEEB',"Bleu azur"),
        ('#00BFFF',"Bleu azur profond"),('#1E90FF',"Bleu toile"),('#B0C4DE',"Bleu acier clair"),
        ('#6495ED',"Bleuet"),('#4682B4',"Bleu acier"),('#4169E1',"Bleu royal"),
        ('#0000FF',"Bleu"),('#0000CD',"Bleu moyen"),('#00008B',"Bleu foncé"),
        ('#000080',"Bleu marin"),('#191970',"Bleu de minuit"),
    )
    nom = models.CharField(max_length=20)
    nomcomplet = models.CharField(max_length=30, default="")
    couleur = models.CharField(max_length=7, choices=LISTE_COULEURS, default='#696969')
    CHOIX_TEMPS = (
        (20, '20 min (par groupe de 3)'),
        (30, '30 min (solo)'),
        (60, '60 min (informatique)')
    )
    temps = models.PositiveSmallIntegerField(
        choices=CHOIX_TEMPS, 
        verbose_name="minutes/colle/élève", 
        default=20
    )
    lv = models.PositiveSmallIntegerField(
        verbose_name="Langue vivante",
        choices=enumerate(['---','LV1','LV2']),
        default=0
    )
    class Meta:
        ordering = ['nom', 'lv', 'temps']
        unique_together = (('nom','lv','temps'))

    def __str__(self):
        dico = {20:'Gr', 30:'So', 60:'Cl'}
        return self.nom.title() + "({})".format("/".join([dico[self.temps]] + (["LV{}".format(self.lv)] if self.lv else []))) 
