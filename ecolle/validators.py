from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class LowerCaseValidator:
    def __init__(self, min_minuscules=1):
        self.min_minuscules = min_minuscules

    def validate(self, password, user=None):
        if len([char for char in password if 'a' <= char <= 'z']) < self.min_minuscules:
            raise ValidationError(
                "Ce mot de passe doit contenir au moins {} lettre(s) minuscule(s)".format(self.min_minuscules),
                code="not_enough_lowercase",
                params={"min_lower_case": self.min_minuscules},
            )

    def get_help_text(self):
        return """Votre mot de passe doit contenir au moins {} lettres minuscule(s)
        """.format(self.min_minuscules)

class UpperCaseValidator:
    def __init__(self, min_majuscules=1):
        self.min_majuscules = min_majuscules

    def validate(self, password, user=None):
        if len([char for char in password if 'A' <= char <= 'Z']) < self.min_majuscules:
            raise ValidationError(
                "Ce mot de passe doit contenir au moins {} lettre(s) majuscule(s)".format(self.min_majuscules),
                code="not_enough_uppercase",
                params={"min_upper_case": self.min_majuscules},
            )

    def get_help_text(self):
        return """Votre mot de passe doit contenir au moins {} lettres majuscule(s)
        """.format(self.min_majuscules)

class DigitValidator:
    def __init__(self, min_chiffres=1):
        self.min_chiffres = min_chiffres

    def validate(self, password, user=None):
        if len([char for char in password if '0' <= char <= '9']) < self.min_chiffres:
            raise ValidationError(
                "Ce mot de passe doit contenir au moins {} chiffre(s)".format(self.min_chiffres),
                code="not_enough_digits",
                params={"min_digits": self.min_chiffres},
            )

    def get_help_text(self):
        return """Votre mot de passe doit contenir au moins {} chiffre(s)
        """.format(self.min_chiffres)

class PunctuationValidator:
    def __init__(self, min_ponctuation=1):
        self.min_ponctuation = min_ponctuation

    def validate(self, password, user=None):
        if len([char for char in password if char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"]) < self.min_ponctuation:
            raise ValidationError(
                "Ce mot de passe doit contenir au moins {} signe(s) de ponctuation".format(self.min_ponctuation),
                code="not_enough_punctuation",
                params={"min_ponctuation": self.min_ponctuation},
            )

    def get_help_text(self):
        return """Votre mot de passe doit contenir au moins {} signe(s) de ponctuation""".format(self.min_ponctuation)