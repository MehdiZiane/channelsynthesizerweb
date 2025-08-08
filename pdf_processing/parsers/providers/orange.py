import os
import re
from typing import List
import fitz
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures

# Charger les variables d'environnement pour Azure
load_dotenv()
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")


def parse_orange_pdf(pdf_path: str) -> List[List[str]]:
    """
    Parse un PDF Orange en utilisant Azure AI Vision pour l'extraction de texte,
    puis applique une logique de section robuste sur le texte propre.
    VERSION DÉFINITIVE.
    """
    print("--- Utilisation du parser Orange DÉFINITIF (Azure) ---")

    if not VISION_ENDPOINT or not VISION_KEY:
        print("ERREUR CRITIQUE: Clés Azure non configurées.")
        return []

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Erreur à l'ouverture du PDF : {e}")
        return []

    client = ImageAnalysisClient(
        endpoint=VISION_ENDPOINT, credential=AzureKeyCredential(VISION_KEY)
    )
    visual_features = [VisualFeatures.READ]

    # Étape 1 : Extraire toutes les lignes de texte propre avec Azure
    azure_lines = []
    for page_num, page in enumerate(doc):
        print(f"Analyse de la page {page_num + 1} du PDF via Azure...")
        pix = page.get_pixmap(dpi=300)
        image_bytes = pix.tobytes("png")

        try:
            result = client.analyze(
                image_data=image_bytes, visual_features=visual_features
            )
            if result.read is not None:
                for line in result.read.blocks[0].lines:
                    azure_lines.append(line.text.strip())
        except Exception as e:
            print(f"Erreur lors de l'appel à Azure pour la page {page_num + 1}: {e}")

    if not azure_lines:
        print("AVERTISSEMENT : Azure n'a retourné aucun texte.")
        return []

    # Étape 2 : Analyser la liste de lignes propre pour créer les sections
    all_sections = []
    current_section = []

    section_titles_pattern = re.compile(
        r"Nederlandstalig|Franstalig|Internationaal|Nieuws|Kids|Sport|Muziek|Regionale zenders|"
        r"Radio|Be tv|Orange Football|VOOSPORT WORLD|\+18|Optie|Zenders",
        re.IGNORECASE,
    )

    # Titre par défaut pour les premières chaînes de la page 1
    current_title = "Offre de base"
    current_section.append(current_title)

    i = 0
    while i < len(azure_lines):
        line = azure_lines[i]

        match = section_titles_pattern.search(line)
        # Un titre est une ligne courte qui correspond à nos mots-clés
        if match and len(line.split()) < 4:
            if len(current_section) > 1:
                all_sections.append(current_section)
            current_section = [line]
            i += 1
            continue

        # Logique pour assembler "numéro" + "nom de chaîne"
        # Si la ligne est un numéro et qu'il y a une ligne suivante
        if line.isdigit() and len(line) < 4 and (i + 1) < len(azure_lines):
            channel_name = azure_lines[i + 1]

            # On s'assure que la ligne suivante n'est pas aussi un numéro
            if not channel_name.isdigit():
                current_section.append(channel_name)
                i += 2  # On saute les deux lignes qu'on vient de traiter
                continue

        i += 1

    if len(current_section) > 1:
        all_sections.append(current_section)

    print(
        f"--- Parser Azure DÉFINITIF a trouvé {len(all_sections)} sections valides. ---"
    )
    return all_sections
