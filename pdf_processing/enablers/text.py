# pdf_processing/enablers/text.py

import os
import json
import re
import fitz
from django.conf import settings  # Import Django settings
from pdf_processing.parsers.providers.orange import parse_orange_pdf
from pdf_processing.parsers.providers.voo import parse_voo_pdf
from pdf_processing.parsers.providers.telenet import parse_telenet_pdf
from pdf_processing.parsers.all_sections_parser import detect_provider_and_year
from pdf_processing.utils import read_section_names

CONFIG_PATH = os.path.join(settings.BASE_DIR, 'pdf_processing', '.config', 'page_selection.json')

def load_page_selection() -> dict:
    """
    Cette fonction charge la configuration de la sélection de pages à partir d'un fichier JSON.
    Elle retourne un dictionnaire de la sélection de pages.
    """
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_pages_to_process(pdf_path: str, total_pages: int) -> list:
    """
    Cette fonction obtient les pages à traiter selon la configuration.
    pdf_path est le chemin du fichier PDF, et total_pages est le nombre total de pages dans le PDF.
    Elle retourne une liste de numéros de pages à traiter.
    """
    page_selection = load_page_selection()
    filename = os.path.basename(pdf_path)
    return page_selection.get(filename, list(range(1, total_pages + 1)))

def add_tv_radio_codes(tsv_path, section_names):
    """
    Cette fonction ajoute les codes TV/Radio dans le fichier TSV.
    section_names sont les noms de section chargés pour vérifier la catégorie.
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_section = None
    processed_lines = []

    for line in lines:
        stripped_line = line.strip()

        # Mise à jour de la section actuelle si la ligne est un nom de section
        if stripped_line in section_names:
            current_section = stripped_line

        # Sauter les lignes qui sont seulement des chiffres ou des noms de section
        if stripped_line.isdigit() or stripped_line in section_names:
            processed_lines.append(line)
            continue

        # Vérifier si la section actuelle devrait être catégorisée comme radio
        is_radio_section = (
            current_section and re.search(r'radio|stingray|music|radios|radiozenders|CHAÎNES DE MUSIQUE', current_section, re.IGNORECASE)
        )

        # Corriger la catégorisation si la ligne a déjà un code TV/R incorrect
        if re.search(r'\s(R|TV)$', stripped_line):
            stripped_line = re.sub(r'\s(R|TV)$', '', stripped_line)

        # Ajouter le code correct
        if is_radio_section:
            processed_lines.append(f"{stripped_line} R\n")
        else:
            processed_lines.append(f"{stripped_line} TV\n")

    # Gérer des cas spécifiques où des chaînes devraient être TV au lieu de radio
    channels_to_correct = [
        "National Geographic", "Ketnet", "STAR channel", "Plattelands TV", "vtm Gold",
        "BBC Entertainment", "Disney Channel VL", "BBC First", "Nickelodeon NL", "Nick Jr NL",
        "Nickelodeon Ukraine", "Disney JR NL", "Play6", "MENT TV", "Q-music", "Play Crime",
        "MTV", "TLC", "Comedy Central", "Eclips TV", "VTM non stop dokters", "History",
        "Play 7", "Cartoon Network", "Vlaams Parlement TV", "ID", "OUTtv", "Play Sports Info",
        "Al Aoula Europe", "2M Monde", "Al Maghreb TV", "TRT Turk", "MBC", "TV Polonia",
        "Rai Uno", "Rai Due", "Rai Tre", "Mediaset Italia", "TVE Internacional",
        "The Israëli Network", "BBC One", "BBC Two", "NPO 1", "NPO 2", "NPO 3", "ARD", "ZDF", "VOX"
    ]

    final_lines = []
    for line in processed_lines:
        # Vérifier si la ligne correspond à une des chaînes à corriger en TV
        if any(channel in line for channel in channels_to_correct):
            final_lines.append(re.sub(r' R$', ' TV', line))
        else:
            final_lines.append(line)

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(final_lines)

    print(f"Codes TV/Radio traitées et enregistrées dans {tsv_path}")

def process_pdfs(pdf_path: str):
    """
    Cette fonction traite un seul fichier PDF.
    """
    filename = os.path.basename(pdf_path)
    try:
        provider, year = detect_provider_and_year(pdf_path)
        document = fitz.open(pdf_path)
        total_pages = document.page_count
        document.close()

        section_file = os.path.join(settings.MEDIA_ROOT, 'outputs', 'section', os.path.splitext(filename)[0] + '_sections.tsv')
        tsv_path = os.path.join(settings.MEDIA_ROOT, 'outputs', 'text', os.path.splitext(filename)[0] + '_text.tsv')

        # Charger les noms de section si disponibles
        section_names = []
        if os.path.exists(section_file):
            section_names = read_section_names(section_file)

        # Parser le PDF en fonction du fournisseur
        if provider == "VOO":
            parse_voo_pdf(pdf_path)
        elif provider == "Telenet":
            pages_to_process = get_pages_to_process(pdf_path, total_pages)
            parse_telenet_pdf(pdf_path, pages_to_process=[1])            
        elif provider == "Orange":
            parse_orange_pdf(pdf_path, section_names)
        else:
            print(f"Fournisseur non supporté {provider} pour le fichier {filename}")
            return

        # Appliquer les codes TV/Radio au fichier TSV
        add_tv_radio_codes(tsv_path, section_names)

        print(f"Traitement du texte terminé pour {filename} pour le fournisseur {provider} et l'année {year}")

    except Exception as e:
        print(f"Erreur en traitant {filename}: {e}")

if __name__ == "__main__":
    pdf_path = os.path.join(settings.MEDIA_ROOT, 'pdfs', 'your_pdf_file.pdf')
    process_pdfs(pdf_path)
