import os
from django.conf import settings
from pdf_processing.parsers.all_sections_parser import (
    extract_text,
    parse,
    get_provider_colors,
    detect_provider_and_year,
    get_pages_to_process,
    remove_redundant_sections,
)
from pdf_processing.parsers.providers.orange import parse_orange_pdf


def process(pdf_path: str):
    """
    Version corrigée qui retourne les données au lieu de les perdre.
    """
    print("--- Exécution de la version CORRIGÉE de sections.py ---")
    try:
        provider, year = detect_provider_and_year(pdf_path)
        all_sections = []

        if provider == "Orange":
            all_sections = parse_orange_pdf(pdf_path)
        else:
            colors = get_provider_colors(provider)
            pages = get_pages_to_process(pdf_path)
            for page_number in pages:
                text, max_size = extract_text(pdf_path, colors, provider, page_number)
                sections = parse(text, provider, max_size)
                all_sections.extend(sections)

        if all_sections:
            all_sections = remove_redundant_sections(all_sections)

        # On retourne les vraies données !
        return all_sections

    except Exception as e:
        print(f"ERREUR dans sections.process() : {e}")
        return []  # Retourner une liste vide en cas d'erreur
