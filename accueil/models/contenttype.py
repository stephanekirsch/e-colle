from django.db.models import FileField
from django.forms import ImageField
from django.forms import forms
from django.utils.translation import ugettext_lazy as _

def fileformat(taille):
    if taille < 1000:
        return "{} bytes".format(taille)
    if taille < 1000000:
        return "{:.03f}".format(taille/1000).rstrip("0").rstrip(".") + " kB"
    if taille < 10**9:
        return "{:.03f}".format(taille/1000000).rstrip("0").rstrip(".") + " MB"
    if taille < 10**12:
        return "{:.03f}".format(taille/1000000000).rstrip("0").rstrip(".") + " GB"
    if taille < 10**15:
        return "{:.03f}".format(taille/1000000000000).rstrip("0").rstrip(".") + " TB"

class ContentTypeRestrictedFileField(FileField):
    """
    Same as FileField, but you can specify:
        * content_types - list containing allowed content_types. Example: ['application/pdf', 'image/jpeg']
        * max_upload_size - the maximum file size (in bytes) allowed for upload.
  """
    def __init__(self, content_types = [], max_upload_size = 1000000, *args, **kwargs):
        self.content_types = content_types
        self.max_upload_size = max_upload_size

        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):        
        data = super().clean(*args, **kwargs)
        file = data.file
        try:
            content_type = file.content_type
            if content_type in self.content_types:
                if file.size > self.max_upload_size:
                    raise forms.ValidationError(_("taille maximale d'un téléversement: {}. taille de votre fichier: {}".format(fileformat(self.max_upload_size), fileformat(file.size))))
            else:
                raise forms.ValidationError(_("type de fichier non supporté"))
        except AttributeError:
            pass           
        return data

class RestrictedImageField(ImageField):
    """
    Same as ImageField, but you can specify:
        * max_upload_size - the maximum file size (in bytes) allowed for upload.
    """
    def __init__(self, *args, **kwargs):
        self.max_upload_size = kwargs.pop("max_upload_size")

        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):        
        data = super().clean(*args, **kwargs)
        if data:
            file = data.file
            taille = file.getbuffer().nbytes
            if taille > self.max_upload_size:
                raise forms.ValidationError(_("taille maximale d'un téléversement: {}. taille de votre fichier: {}".format(fileformat(self.max_upload_size), fileformat(taille))))
        return data