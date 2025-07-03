from django.forms.widgets import FileInput

class MultipleFileInput(FileInput):
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs['multiple'] = True
        super().__init__(attrs)
