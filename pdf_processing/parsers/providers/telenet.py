# Dans le nouveau fichier : pdf_processing/parsers/providers/telenet.py

import fitz
import re
from typing import List, Dict
from azure.core.credentials import AzureKeyCredential
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
import os
from dotenv import load_dotenv

load_dotenv()
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")


def parse_telenet_pdf(pdf_path: str) -> List[Dict]:
    """
    Parse un PDF Telenet via Azure et retourne une liste de dictionnaires
    contenant les données propres pour chaque chaîne.
    """
    print("--- Utilisation du nouveau parser dédié pour Telenet (avec Azure) ---")
    if not VISION_ENDPOINT or not VISION_KEY:
        return []

    doc = fitz.open(pdf_path)
    client = ImageAnalysisClient(
        endpoint=VISION_ENDPOINT, credential=AzureKeyCredential(VISION_KEY)
    )
    azure_lines = []

    for page_num, page in enumerate(doc):
        print(f"Analyse de la page {page_num + 1} (Telenet) via Azure...")
        pix = page.get_pixmap(dpi=300)
        image_bytes = pix.tobytes("png")
        try:
            result = client.analyze(
                image_data=image_bytes, visual_features=[VisualFeatures.READ]
            )
            if result.read:
                for line in result.read.blocks[0].lines:
                    azure_lines.append(line.text.strip())
        except Exception as e:
            print(f"Erreur Azure pour page {page_num + 1}: {e}")

    if not azure_lines:
        return []

    channels_data = []
    current_title = "OFFRE DE BASE"  # Par défaut, tout est dans l'offre de base

    for line in azure_lines:
        # Un titre est une ligne en majuscules avec peu de chiffres
        if (
            line.isupper()
            and len(re.findall(r"\d", line)) < 2
            and len(line.split()) < 5
        ):
            current_title = line
            continue

        # Une chaîne commence par un numéro
        match = re.match(r"^(\d{3})\s+(.*)", line)
        if match:
            channel_name_raw = match.group(2).strip()

            # Classification basée sur le titre de la section
            is_basic = (
                "base" in current_title.lower() or "radio" in current_title.lower()
            )
            basic_option = "Basic" if is_basic else "Option"

            is_radio = (
                "radio" in current_title.lower() or "stingray" in current_title.lower()
            )
            tv_radio = "Radio" if is_radio else "TV"

            hd_sd = "HD" if "HD" in channel_name_raw.upper() else ""
            clean_channel_name = re.sub(
                r"\s+HD\b", "", channel_name_raw, flags=re.IGNORECASE
            ).strip()

            if len(clean_channel_name) > 1:
                channels_data.append(
                    {
                        "Channel": clean_channel_name,
                        "Basic/Option": basic_option,
                        "TV/Radio": tv_radio,
                        "HD/SD": hd_sd,
                        # Telenet PDF est spécifique à une région via son nom de fichier
                        "Region Flanders": 0,
                        "Brussels": 0,
                        "Region Wallonia": 0,
                        "Communauté Germanophone": 0,
                    }
                )

    print(f"--- Parser Telenet a trouvé {len(channels_data)} chaînes. ---")
    return channels_data
