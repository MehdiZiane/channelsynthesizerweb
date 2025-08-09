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


def is_basic_section_orange(section_name: str) -> bool:
    """
    Logique de classification spécifique pour les titres de section d'Orange.
    """
    section_lower = section_name.lower()
    option_keywords = [
        "optie",
        "option",
        "be tv",
        "football",
        "voosport",
        "discover more",
        "family fun",
        "penthouse",
        "+18",
    ]
    if any(keyword in section_lower for keyword in option_keywords):
        return False
    return True


def parse_orange_pdf(pdf_path: str) -> List[Dict]:
    """
    Parse un PDF Orange via Azure et retourne une liste de dictionnaires
    contenant les données propres pour chaque chaîne (FORMAT STANDARDISÉ).
    """
    print("--- Utilisation du parser Orange DÉFINITIF (Standardisé) ---")
    if not VISION_ENDPOINT or not VISION_KEY:
        return []

    doc = fitz.open(pdf_path)
    client = ImageAnalysisClient(
        endpoint=VISION_ENDPOINT, credential=AzureKeyCredential(VISION_KEY)
    )
    azure_lines = []

    for page_num, page in enumerate(doc):
        print(f"Analyse de la page {page_num + 1} (Orange) via Azure...")
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
    current_title = "Offre de base"

    # On itère avec un index pour pouvoir regarder la ligne suivante
    i = 0
    while i < len(azure_lines):
        line = azure_lines[i]

        # Logique pour identifier un titre de section
        # Un titre est généralement court et ne commence pas par un numéro
        if len(line.split()) < 5 and not re.match(r"^\d", line):
            current_title = line
            i += 1
            continue

        # Logique pour identifier une paire "numéro" -> "nom de chaîne"
        if line.isdigit() and len(line) < 4 and (i + 1) < len(azure_lines):
            channel_name_raw = azure_lines[i + 1]

            # On s'assure que la ligne suivante n'est pas aussi un numéro
            if not channel_name_raw.isdigit():
                # Classification en utilisant le titre de section
                basic_option = (
                    "Basic" if is_basic_section_orange(current_title) else "Option"
                )
                tv_radio = "Radio" if "radio" in current_title.lower() else "TV"

                hd_sd = "HD" if "HD" in channel_name_raw.upper() else ""
                clean_channel_name = re.sub(
                    r"\s+HD\b", "", channel_name_raw, flags=re.IGNORECASE
                ).strip()

                # Détermination de la région basée sur le nom du fichier (plus simple)
                regions = [0, 0, 0, 0]
                fname_lower = os.path.basename(pdf_path).lower()
                if "brussel" in fname_lower or "bruxelles" in fname_lower:
                    regions = [0, 1, 0, 0]
                elif "vlaanderen" in fname_lower:
                    regions = [1, 0, 0, 0]
                elif "wallonie" in fname_lower:
                    regions = [0, 0, 1, 0]
                elif "german" in fname_lower:
                    regions = [0, 0, 0, 1]

                channels_data.append(
                    {
                        "Channel": clean_channel_name,
                        "Basic/Option": basic_option,
                        "TV/Radio": tv_radio,
                        "HD/SD": hd_sd,
                        "Region Flanders": regions[0],
                        "Brussels": regions[1],
                        "Region Wallonia": regions[2],
                        "Communauté Germanophone": regions[3],
                    }
                )
                i += 2  # On saute le numéro et le nom
                continue

        i += 1

    print(f"--- Parser Orange Standardisé a trouvé {len(channels_data)} chaînes. ---")
    return channels_data
