# image_processing/services.py

import os
import fitz  # PyMuPDF
from dotenv import load_dotenv
from PIL import Image
from django.core.files.base import ContentFile
from azure.core.credentials import AzureKeyCredential
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures

from .models import ProcessedImage, ImageAnalysis

# Charger les variables d'environnement une seule fois
load_dotenv()
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")


def analyze_pdf_images(uploaded_pdf_instance):
    """
    Service pour extraire, analyser les images d'un PDF et sauvegarder les résultats.
    Prend en argument une instance du modèle UploadedPDF.
    """
    if not VISION_ENDPOINT or not VISION_KEY:
        print("Erreur: Clés Azure non configurées.")
        return

    # Utiliser le chemin du fichier depuis l'instance du modèle Django
    pdf_path = uploaded_pdf_instance.file.path

    print(f"--- Démarrage de l'analyse pour le PDF : {pdf_path} ---")
    doc = fitz.open(pdf_path)

    # Authentification auprès du client Azure AI Vision
    client = ImageAnalysisClient(
        endpoint=VISION_ENDPOINT, credential=AzureKeyCredential(VISION_KEY)
    )
    visual_features = [VisualFeatures.READ]

    # Boucle sur les images du PDF
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_filename = (
                f"pdf_{uploaded_pdf_instance.id}_p{page_num+1}_{img_index+1}.png"
            )

            # Vérification de la taille avec Pillow
            try:
                with Image.open(ContentFile(image_bytes)) as pil_img:
                    width, height = pil_img.size
            except Exception as e:
                print(f"Impossible de lire l'image {image_filename}: {e}")
                continue

            if width < 50 or height < 50:
                continue

            # Création de l'objet ProcessedImage en BDD
            processed_image = ProcessedImage.objects.create(
                source_pdf=uploaded_pdf_instance, width=width, height=height
            )
            # Sauvegarde de l'image via le champ ImageField de Django
            processed_image.image_file.save(
                image_filename, ContentFile(image_bytes), save=True
            )

            # Analyse de l'image via Azure
            try:
                result = client.analyze(
                    image_data=image_bytes, visual_features=visual_features
                )

                # Sauvegarde du résultat dans le modèle ImageAnalysis
                ImageAnalysis.objects.create(
                    processed_image=processed_image,
                    ocr_result=result.as_dict(),  # Sauvegarde du résultat complet en JSON
                    analysis_successful=True,
                )
                print(f"Analyse réussie pour : {image_filename}")
            except Exception as e:
                print(f"Erreur d'analyse Azure pour {image_filename}: {e}")
                ImageAnalysis.objects.create(
                    processed_image=processed_image, analysis_successful=False
                )

    # Marquer le PDF comme traité
    uploaded_pdf_instance.processed = True
    uploaded_pdf_instance.save()
    print(f"--- Fin de l'analyse pour le PDF : {pdf_path} ---")


def diagnose_pdf_with_azure(uploaded_pdf_instance):
    """
    Fonction de diagnostic CORRIGÉE. Elle convertit chaque page du PDF en image
    avant de l'envoyer à Azure Vision pour une analyse fiable.
    """
    if not VISION_ENDPOINT or not VISION_KEY:
        print("Erreur: Clés Azure non configurées.")
        return

    pdf_path = uploaded_pdf_instance.file.path
    print(f"--- Démarrage de l'analyse de document pour : {pdf_path} ---")

    # Authentification et client Azure
    client = ImageAnalysisClient(
        endpoint=VISION_ENDPOINT, credential=AzureKeyCredential(VISION_KEY)
    )
    visual_features = [VisualFeatures.READ]

    # On ouvre le document PDF avec fitz
    doc = fitz.open(pdf_path)

    # On boucle sur chaque page du PDF
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"\n--- Analyse de la Page {page_num + 1} ---")

        # Conversion de la page en image (PNG) en mémoire
        pix = page.get_pixmap(dpi=200)  # dpi élevé pour une meilleure qualité d'OCR
        image_bytes = pix.tobytes("png")

        # Analyse de l'image de la page via Azure
        try:
            print(f"Envoi de l'image de la Page {page_num + 1} à Azure...")
            result = client.analyze(
                image_data=image_bytes, visual_features=visual_features
            )

            print(
                "\n"
                + "=" * 20
                + f" RÉSULTAT AZURE POUR LA PAGE {page_num + 1} "
                + "=" * 20
                + "\n"
            )

            if result.read is not None:
                # On affiche simplement le texte de chaque ligne détectée par Azure
                for line in result.read.blocks[0].lines:
                    print(line.text)
            else:
                print("Azure n'a retourné aucun texte lisible pour cette page.")

        except Exception as e:
            print(
                f"Une erreur est survenue lors de l'appel à Azure pour la Page {page_num + 1}: {e}"
            )

    print("\n\n" + "=" * 50)
    print("--- FIN DE L'ANALYSE AZURE COMPLÈTE ---")
    print("=" * 50 + "\n")
