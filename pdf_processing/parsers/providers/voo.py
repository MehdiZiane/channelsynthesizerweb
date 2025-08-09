import fitz, re, os
from typing import List, Dict
from azure.core.credentials import AzureKeyCredential
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from dotenv import load_dotenv

load_dotenv()
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")


def parse_voo_pdf(pdf_path: str) -> List[Dict]:
    """
    Parse un PDF VOO via Azure et retourne une liste de dictionnaires
    contenant les données propres pour chaque chaîne.
    """
    print("--- Utilisation du parser VOO Expert (Azure) ---")
    if not VISION_ENDPOINT or not VISION_KEY:
        return []

    doc = fitz.open(pdf_path)
    client = ImageAnalysisClient(
        endpoint=VISION_ENDPOINT, credential=AzureKeyCredential(VISION_KEY)
    )
    azure_lines = []

    for page_num, page in enumerate(doc):
        print(f"Analyse de la page {page_num + 1} (VOO) via Azure...")
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

    # --- Logique d'assemblage et de classification VOO ---
    voo_option_codes = [
        "Pa",
        "Ci",
        "Doc",
        "Div",
        "Co",
        "Enf",
        "Sp",
        "Sel",
        "Inf",
        "Sen",
        "Ch",
        "FF",
        "DM",
        "CX",
        "MX",
    ]
    channels_data = []
    i = 0
    while i < len(azure_lines):
        line = azure_lines[i]
        if re.match(r"^\d{1,3}$", line) and (i + 1) < len(azure_lines):
            channel_name_raw = azure_lines[i + 1]
            i += 2
            codes = []
            while (
                i < len(azure_lines)
                and len(azure_lines[i]) < 5
                and not re.match(r"^\d", azure_lines[i])
            ):
                codes.append(azure_lines[i])
                i += 1

            # Classification
            regions = [1, 1, 1, 1]  # [F, B, W, G]
            if "W" in codes:
                regions = [0, 0, 1, 0]
            elif "B" in codes:
                regions = [0, 1, 0, 0]
            elif "F" in codes:
                regions = [1, 0, 0, 0]

            basic_option = (
                "Option" if any(code in codes for code in voo_option_codes) else "Basic"
            )

            # Nettoyage
            hd_sd = (
                "HD"
                if "HD" in channel_name_raw.upper()
                else "SD" if "SD" in channel_name_raw.upper() else ""
            )
            clean_channel_name = re.sub(
                r"\s*\(?HD\)?", "", channel_name_raw, flags=re.IGNORECASE
            ).strip()

            channels_data.append(
                {
                    "Channel": clean_channel_name,
                    "Basic/Option": basic_option,
                    "TV/Radio": "TV",  # Simplification, VOO PDF ne semble lister que la TV
                    "HD/SD": hd_sd,
                    "Region Flanders": regions[0],
                    "Brussels": regions[1],
                    "Region Wallonia": regions[2],
                    "Communauté Germanophone": regions[3],
                }
            )
            continue
        i += 1

    print(f"--- Parser VOO Expert a trouvé {len(channels_data)} chaînes. ---")
    return channels_data
