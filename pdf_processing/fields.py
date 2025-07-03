from django import forms
from .widgets import MultipleFileInput

class MultipleFileField(forms.FileField):
    
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        # data can be a list of files
        if not data:
            if self.required:
                raise forms.ValidationError(self.error_messages['required'], code='required')
            else:
                return []
        # Ensure that data is a list
        if not isinstance(data, list):
            data = [data]
        return data
