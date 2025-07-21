# image_processing/models.py

from django.db import models
from pdf_processing.models import UploadedPDF # On importe le modèle du PDF

class ProcessedImage(models.Model):
    """
    Ce modèle représente une image extraite d'un fichier PDF.
    """
    # Lien vers le fichier PDF d'origine
    source_pdf = models.ForeignKey(UploadedPDF, on_delete=models.CASCADE, related_name='processed_images')
    
    # Chemin vers le fichier image sauvegardé
    image_file = models.ImageField(upload_to='extracted_images/')
    
    # Dimensions de l'image
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    
    # Date de création
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image from {self.source_pdf.file.name} - {os.path.basename(self.image_file.name)}"

class ImageAnalysis(models.Model):
    """
    Ce modèle stocke les résultats de l'analyse OCR d'une image.
    """
    # Lien vers l'image qui a été analysée
    processed_image = models.OneToOneField(ProcessedImage, on_delete=models.CASCADE, related_name='analysis')
    
    # Le résultat complet de l'OCR, stocké en format JSON
    ocr_result = models.JSONField(null=True, blank=True)
    
    # Indique si l'analyse a réussi
    analysis_successful = models.BooleanField(default=False)
    
    # Date de l'analyse
    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis for {self.processed_image}"