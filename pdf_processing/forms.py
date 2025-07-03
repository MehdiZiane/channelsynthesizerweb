import os
from django import forms
from .fields import MultipleFileField 
from .models import UploadedPDF, UploadedExcel
from .widgets import MultipleFileInput

class UploadFilesForm(forms.Form):
    pdf_files = MultipleFileField(
        required=False,
        widget=MultipleFileInput()
    )
    existing_pdf_files = forms.ModelMultipleChoiceField(
        queryset=UploadedPDF.objects.order_by('-uploaded_at'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Fichiers PDF existants",
    )
    excel_file = forms.FileField(required=False, label="Uploader un nouveau fichier Excel")
    existing_excel_file = forms.ModelChoiceField(
        queryset=UploadedExcel.objects.order_by('-uploaded_at'),
        required=False,
        empty_label="Choisissez un fichier Excel existant",
        label="Fichiers Excel existants",
    )
    include_base_offers = forms.BooleanField(
        required=False,
        label="Activer les offres de l'opérateur Base",
        initial=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Personnaliser le label pour afficher le nom du fichier et la date
        self.fields['existing_pdf_files'].label_from_instance = lambda obj: f"{os.path.basename(obj.file.name)} (uploadé le {obj.uploaded_at.strftime('%d/%m/%Y %H:%M')})"
        self.fields['existing_excel_file'].label_from_instance = lambda obj: f"{os.path.basename(obj.file.name)} (uploadé le {obj.uploaded_at.strftime('%d/%m/%Y %H:%M')})"

    def clean(self):
        cleaned_data = super().clean()
        pdf_files = cleaned_data.get('pdf_files')
        existing_pdf_files = cleaned_data.get('existing_pdf_files')
        excel_file = cleaned_data.get('excel_file')
        existing_excel_file = cleaned_data.get('existing_excel_file')
        include_base_offers = cleaned_data.get('include_base_offers')

        if not pdf_files and not existing_pdf_files and not include_base_offers:
            raise forms.ValidationError('Veuillez uploader au moins un fichier PDF, en sélectionner un existant, ou activer les offres de Base.')

        if not excel_file and not existing_excel_file:
            raise forms.ValidationError('Veuillez uploader un fichier Excel ou en sélectionner un existant.')