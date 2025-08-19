# Dans pdf_processing/forms.py

import os
from django import forms
from .fields import MultipleFileField
from .models import UploadedPDF, UploadedExcel
from .widgets import MultipleFileInput


# On revient à un formulaire complet, mais structuré pour notre nouvelle interface.
class AnalysisForm(forms.Form):
    # Champ pour uploader de nouveaux PDF (un seul champ pour tous les fournisseurs)
    pdf_files = MultipleFileField(
        required=False,
        widget=MultipleFileInput(),
        label="Uploader un ou plusieurs nouveaux fichiers PDF",
    )

    # Champ pour sélectionner des PDF existants (un seul champ qui liste tout)
    existing_pdf_files = forms.ModelMultipleChoiceField(
        queryset=UploadedPDF.objects.order_by("-uploaded_at"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Sélectionner des fichiers PDF existants",
    )

    # Les champs pour le fichier Excel ne changent pas
    excel_file = forms.FileField(
        required=False, label="Uploader un nouveau fichier Excel de référence"
    )
    existing_excel_file = forms.ModelChoiceField(
        queryset=UploadedExcel.objects.order_by("-uploaded_at"),
        required=False,
        empty_label="Choisissez un fichier Excel existant",
        label="Ou sélectionner un fichier existant",
    )

    # Le champ pour BASE, qui sera géré comme un "fournisseur" via une case à cocher
    include_base_offers = forms.BooleanField(
        required=False, label="Analyser les offres de l'opérateur Base", initial=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personnaliser l'affichage des noms de fichiers pour les listes de sélection
        self.fields["existing_pdf_files"].label_from_instance = (
            lambda obj: f"{os.path.basename(obj.file.name)} (uploadé le {obj.uploaded_at.strftime('%d/%m/%Y %H:%M')})"
        )
        self.fields["existing_excel_file"].label_from_instance = (
            lambda obj: f"{os.path.basename(obj.file.name)} (uploadé le {obj.uploaded_at.strftime('%d/%m/%Y %H:%M')})"
        )

    def clean(self):
        # La logique de validation s'assure que l'utilisateur a bien fourni les fichiers nécessaires
        cleaned_data = super().clean()
        pdf_files = cleaned_data.get("pdf_files")
        existing_pdf_files = cleaned_data.get("existing_pdf_files")
        excel_file = cleaned_data.get("excel_file")
        existing_excel_file = cleaned_data.get("existing_excel_file")
        include_base_offers = cleaned_data.get("include_base_offers")

        # Il faut au moins une source de données
        if not pdf_files and not existing_pdf_files and not include_base_offers:
            raise forms.ValidationError(
                "Veuillez fournir un PDF (nouveau ou existant) ou activer l' analyse pour Base."
            )

        # Il faut obligatoirement un fichier Excel
        if not excel_file and not existing_excel_file:
            raise forms.ValidationError(
                "Veuillez fournir un fichier Excel de référence (nouveau ou existant)."
            )
