from pathlib import Path
import os
import pandas as pd
from django.conf import settings  # Import Django settings
from pdf_processing.utils import get_provider_and_year, read_section_names, parse_tsv, find_file_pairs, create_consolidated_excel

#definir le répertoire de base (un niveau au-dessus de 'src')
BASE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

def generate_excel_report(output_directory, channel_grouping_df):
    """
    genere un rapport Excel consolide a partir des fichiers de section et de texte.

    :param output_directory: repertoire contenant les fichiers de sortie
    :param channel_grouping_df: DataFrame contenant les informations de groupement des chaînes
    :return: Le chemin vers le fichier Excel genere
    """
    section_dir = Path(settings.MEDIA_ROOT) / 'outputs' / 'section'
    text_dir = Path(settings.MEDIA_ROOT) / 'outputs' / 'text'
    output_path = Path(output_directory) / 'xlsx' / 'consolidated_report.xlsx'

    all_data = []

    #lire et traiter les données des fournisseurs
    for section_file, text_file in find_file_pairs(section_dir, text_dir):
        provider, year = get_provider_and_year(text_file.stem)
        section_names = read_section_names(section_file)
        data = parse_tsv(text_file, section_names, provider)
        filename = text_file.name
        if data:
            print(f"Extraction des données pour le fournisseur: {provider}, année: {year}, taille des data: {len(data)}")
            all_data.append((provider, year, data, section_names, filename))
        else:
            print(f"Pas de data trouvé pour le fournisseur: {provider}, année: {year}")

    #creer le rapport Excel consolide
    create_consolidated_excel(all_data, output_path, channel_grouping_df)

    #renvoyer le chemin du fichier excel généré
    return output_path


if __name__ == "__main__":
    # Use settings.MEDIA_ROOT for output_directory
    output_directory = os.path.join(settings.MEDIA_ROOT, 'outputs')

    # Load or create channel_grouping_df before calling generate_excel_report
    try:
        latest_channel_grouping_file = os.path.join(settings.MEDIA_ROOT, 'groupings', 'Channel_Grouping_Latest_20240607.xlsx')
        channel_grouping_df = pd.read_excel(latest_channel_grouping_file)
    except FileNotFoundError:
        print("Fichier de groupement des chaînes non trouvé.")
        exit(1)

    output_path = generate_excel_report(output_directory, channel_grouping_df)
    print(f"Rapport Excel généré à : {output_path}")  #afficher le chemin du fichier généré
