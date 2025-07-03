from .models import UploadedPDF, Channel
from .parsers.all_sections_parser import detect_provider_and_year
from .enablers.sections import process as process_sections
from .enablers.text import process_pdfs
from .utils import parse_tsv, read_section_names
from pdf_processing.enablers.excel import generate_excel_report
import os
from django.conf import settings
import pandas as pd
import shutil
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

def process_uploaded_pdfs(pdf_instances, excel_file_path, include_base_offers=False):
    pdf_paths = [pdf_instance.file.path for pdf_instance in pdf_instances]

    # Define input and output directories
    input_directory = os.path.dirname(pdf_paths[0])  # PDFs are in the same directory
    output_directory = os.path.join(settings.MEDIA_ROOT, 'outputs')
    output_path = os.path.join(output_directory, 'xlsx/consolidated_report.xlsx')
    grouping_input_directory = os.path.dirname(excel_file_path)

    # Effacer les répertoires temporaires avant le traitement
    temp_dirs = [
        os.path.join(settings.MEDIA_ROOT, 'outputs', 'section'),
        os.path.join(settings.MEDIA_ROOT, 'outputs', 'text'),
        # Ajoutez d'autres répertoires temporaires si nécessaire
    ]
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    # Continue with processing
    # Use the uploaded Excel file
    latest_channel_grouping_file = excel_file_path

    # Load the channel grouping data
    channel_grouping_df = pd.read_excel(latest_channel_grouping_file, sheet_name='Content_Channel_Grouping')

    # Process sections and text for each PDF
    for pdf_path in pdf_paths:
        process_sections(pdf_path)  # Adjusted to process a single PDF
        process_pdfs(pdf_path)      # Adjusted to process a single PDF

    # Generate the consolidated Excel report
    output_path = generate_excel_report(output_path, channel_grouping_df)

    # Enregistrer ou déplacer le rapport pour qu'il puisse être téléchargé
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    final_report_path = os.path.join(reports_dir, 'consolidated_report.xlsx')
    os.replace(output_path, final_report_path)

    # Si l'utilisateur a choisi d'inclure les offres de Base
    if include_base_offers:
        print("Scraping des offres BASE et ajout au rapport...")
        base_url = "https://www.prd.base.be/en/support/tv/your-base-tv-box-and-remote/what-channels-does-base-offer/"
        try:
            base_offer_df = scrape_base_offer(base_url)

            # Vérifier si le DataFrame n'est pas vide
            if base_offer_df.empty:
                raise ValueError("Aucune chaîne n'a été trouvée lors du scraping des offres BASE.")

            # Lire la feuille 'Consolidated' pour obtenir l'ordre des colonnes
            consolidated_df = pd.read_excel(final_report_path, sheet_name='Consolidated')
            columns_order = consolidated_df.columns.tolist()

            # Réorganiser les colonnes de base_offer_df
            base_offer_df = base_offer_df.reindex(columns=columns_order)

            # Ajouter les données de l'offre BASE au fichier Excel existant
            with pd.ExcelWriter(final_report_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                base_offer_df.to_excel(writer, sheet_name='Consolidated', index=False, header=False,
                                       startrow=writer.sheets['Consolidated'].max_row)
        except Exception as e:
            print(f"Erreur lors du scraping des offres BASE : {e}")
            # Ajouter un message d'erreur dans le rapport consolidé
            add_error_to_report(final_report_path, f"Erreur lors du scraping des offres BASE : {e}")


def scrape_base_offer(base_url):
    """
    Cette fonction scrape les offres de chaînes du site BASE pour extraire les données.
    Elle prend en paramètre l'URL de la page à scraper.
    Elle retourne un DataFrame contenant les informations extraites.
    """
    response = requests.get(base_url)
    response.raise_for_status()  # Vérifie si la requête a réussi

    soup = BeautifulSoup(response.content, 'html.parser')

    channel_data = []
    accordion_items = soup.select('.cmp-accordion__item')

    # Obtenir l'année actuelle pour la période du fournisseur
    scrape_year = datetime.now().year

    for accordion_item in accordion_items:
        region_name_element = accordion_item.select_one('.cmp-accordion__header h5, .cmp-accordion__header .heading--5')
        if not region_name_element:
            print("Warning: No region name found for an accordion item, skipping.")
            continue

        region_name = region_name_element.get_text().strip().lower()

        # Déterminer les codes des régions
        if 'dutch' in region_name:
            regions = [1, 1, 0, 0]   # Flandre et Bruxelles
        elif 'french' in region_name:
            regions = [0, 1, 1, 0]  # Wallonie et Bruxelles
        else:
            # Ignorer si le nom de la région n'est pas reconnu
            continue

        # Déterminer si la section est TV ou Radio
        if 'radio' in region_name:
            tv_radio = 'Radio'
        else:
            tv_radio = 'TV'

        # Scraper les chaînes
        channel_list_items = accordion_item.select('.cmp-text p')
        for item in channel_list_items:
            channel = item.get_text().strip()

            # Enlever la numérotation au début du nom de la chaîne
            channel = re.sub(r'^\d+\.\s*', '', channel)
            # Ajouter uniquement les lignes avec des noms de chaînes non vides
            if channel:
                # Créer le niveau de groupe de chaînes en supprimant certains mots clés
                channel_group_level = re.sub(
                    r'\b(HD|SD|FR|NL|Vlaams Brabant|Antwerpen|Limburg|Oost-Vlaanderen|West-Vlaanderen|60\'s & 70\'s|80\'s & 90\'s)\b',
                    '',
                    channel
                ).strip()

                # Déterminer HD/SD
                if 'HD' in channel:
                    hd_sd = 'HD'
                elif 'SD' in channel:
                    hd_sd = 'SD'
                else:
                    hd_sd = ''

                # Ajouter les données de la chaîne
                channel_data.append([
                    channel,                   # 'Channel'
                    f'BASE {scrape_year}',     # 'Provider_Period'
                    'Basic',                   # 'Basic/Option'
                    tv_radio,                  # 'TV/Radio'
                    hd_sd,                     # 'HD/SD'
                    channel_group_level,       # 'Channel Group Level'
                    *regions                   # 'Region Flanders', 'Brussels', 'Region Wallonia', 'Communauté Germanophone'
                ])

    # Créer un DataFrame avec les colonnes dans le bon ordre
    df = pd.DataFrame(
        channel_data,
        columns=[
            'Channel',
            'Provider_Period',
            'Basic/Option',
            'TV/Radio',
            'HD/SD',
            'Channel Group Level',
            'Region Flanders',
            'Brussels',
            'Region Wallonia',
            'Communauté Germanophone'
        ]
    )

    # Supprimer les lignes avec des valeurs 'Channel' vides
    df = df.dropna(subset=['Channel'])

    return df



def add_error_to_report(output_path, error_message):
    # Charger le fichier Excel existant
    with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
        # Obtenir le nombre de lignes actuelles
        start_row = writer.sheets['Consolidated'].max_row

        # Créer un DataFrame avec le message d'erreur
        error_df = pd.DataFrame({'Channel': [error_message]})

        # Écrire le message d'erreur dans le rapport
        error_df.to_excel(writer, sheet_name='Consolidated', index=False, header=False, startrow=start_row)