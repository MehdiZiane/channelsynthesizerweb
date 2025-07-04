import os
from datetime import datetime
from pathlib import Path
import pandas as pd
from django.conf import settings  # Import Django settings
from parsers.providers.base import scrape_base_offer
from utils import create_summary_table, open_file_with_default_app, clean_consolidated_sheet, \
    check_if_file_open
from enablers.excel import generate_excel_report
from enablers.sections import process as process_sections
from enablers.text import process_pdfs

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


def find_latest_channel_grouping_file(input_folder: str) -> Path:
    """
    trouve le dernier fichier 'Channel_Grouping_Latest_YYYYMMDD.xlsx' dans le répertoire des inputs.
    Parcourt tous les fichiers de ce format dans le répertoire fourni
    et renvoie celui avec la date la plus récente.

    :param input_folder: répertoire où chercher le fichier de groupement des chaînes.
    :return: Le chemin vers le dernier fichier trouvé.
    """
    input_path = Path(input_folder)
    grouping_files = list(input_path.glob('Channel_Grouping_Latest_*.xlsx'))

    if not grouping_files:
        raise FileNotFoundError("Aucun fichier de groupement des chaînes trouvé dans le répertoire des inputs.")

    # trier les fichiers par date pour trouver le dernier fichier
    latest_file = max(
        grouping_files,
        key=lambda file: datetime.strptime(file.stem.split('_')[-1], '%Y%m%d')
    )

    return latest_file


def main():
    """
    script principale pour traiter les fichiers pdf en quatre étapes:
    1. extraire les sections.
    2. traiter le texte des pdfs
    3. générer le rapport excel consolidé
    4. ajouter les données de l'offre BASE (y compris les chaînes radio)

    Ce script gère l'ensemble du workflow depuis la lecture des fichiers jusqu'à la création d'un rapport consolidé
    au format Excel, en passant par l'extraction des données des PDF.
    """

    # Define input and output directories using Django settings
    input_directory = os.path.join(settings.MEDIA_ROOT, 'pdfs')
    output_directory = os.path.join(settings.MEDIA_ROOT, 'outputs')
    grouping_input_directory = os.path.join(settings.MEDIA_ROOT, 'groupings')

    print("Recherche du dernier fichier de groupement des chaînes...")
    try:
        latest_channel_grouping_file = find_latest_channel_grouping_file(grouping_input_directory)
        print(f"Fichier de groupement des chaînes trouvé : {latest_channel_grouping_file}")
    except FileNotFoundError as e:
        print(e)
        return

    # Check if the channel grouping Excel file is open
    if check_if_file_open(latest_channel_grouping_file):
        print(
            f"Veuillez fermer le fichier de groupement des chaînes : {latest_channel_grouping_file} avant de continuer.")
        return

    # Check if the consolidated output file is already open
    output_path = Path(output_directory) / 'xlsx/consolidated_report.xlsx'
    if output_path.exists() and check_if_file_open(output_path):
        print(f"Veuillez fermer le fichier de rapport consolidé : {output_path} avant de continuer.")
        return

    try:
        # Load the channel grouping data
        channel_grouping_df = pd.read_excel(latest_channel_grouping_file, sheet_name='Content_Channel_Grouping')
        print("Fichier de groupement des chaînes chargé avec succès.")
    except Exception as e:
        print(f"Erreur lors du chargement de la feuille Content_Channel_Grouping : {e}")
        return

    print("Traitement des sections...")
    process_sections(input_directory)  # Process the PDF sections

    print("Traitement du texte...")
    process_pdfs(input_directory)  # Extract text from PDFs

    print("Génération du rapport Excel consolidé...")
    output_path = generate_excel_report(output_directory, channel_grouping_df)

    if output_path:
        print("Nettoyage de la feuille Consolidated...")
        clean_consolidated_sheet(output_path)  # Clean the consolidated Excel sheet

    if output_path:
        print("Scraping des offres BASE et ajout au rapport...")
        base_url = "https://www.prd.base.be/en/support/tv/your-base-tv-box-and-remote/what-channels-does-base-offer/"
        base_offer_df = scrape_base_offer(base_url)

        # Append BASE offer data to the existing Excel file
        with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
            base_offer_df.to_excel(writer, sheet_name='Consolidated', index=False, header=False,
                                   startrow=writer.sheets['Consolidated'].max_row)

        # Generate the summary report after adding BASE data
        print("Génération du rapport de synthèse...")
        consolidated_df = pd.read_excel(output_path, sheet_name='Consolidated')
        summary_df = create_summary_table(consolidated_df)

        # Add the summary table to the Excel file
        with pd.ExcelWriter(output_path, engine='openpyxl', mode='a') as writer:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Since we're in a web app, you might serve the file for download instead
    else:
        print("Erreur : le rapport Excel consolidé n'a pas été généré.")

if __name__ == "__main__":
    main()  # exécution principale du script
