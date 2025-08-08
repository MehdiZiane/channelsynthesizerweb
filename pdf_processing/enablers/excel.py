import os
import pandas as pd
from pathlib import Path
from django.conf import settings

# On importe uniquement les fonctions dont on a vraiment besoin
from pdf_processing.utils import get_provider_and_year, create_consolidated_excel


def generate_excel_report(output_path, channel_grouping_df, all_extracted_data):
    """
    Génère un rapport Excel consolidé directement à partir des données extraites en mémoire.
    C'est la version finale et corrigée.
    """
    print("--- Utilisation de la version CORRIGÉE de generate_excel_report ---")

    # Cette variable va contenir les données formatées pour la fonction suivante
    all_data_for_consolidation = []

    # 'all_extracted_data' est la liste que nous avons construite dans processing.py
    # Elle contient [{'path': ..., 'sections': [['Titre1', 'ch1'], ['Titre2', 'ch2']]}]
    for data_item in all_extracted_data:
        pdf_path = data_item["path"]
        sections = data_item[
            "sections"
        ]  # sections = [['Titre1', 'ch1'], ['Titre2', 'ch2']]

        # On extrait le fournisseur et l'année depuis le chemin du fichier
        provider, year = get_provider_and_year(os.path.basename(pdf_path))

        # On recrée la structure de données que l'ancienne fonction attendait
        # C'est un tuple : (fournisseur, année, données des sections, noms des sections, nom du fichier)
        section_names = [section[0] for section in sections if section]

        # On ajoute ce tuple à notre liste
        all_data_for_consolidation.append(
            (provider, year, sections, section_names, os.path.basename(pdf_path))
        )

    # On appelle la fonction qui crée l'Excel, mais cette fois avec les données directement
    # au lieu de la forcer à lire des fichiers intermédiaires.
    create_consolidated_excel(
        all_data_for_consolidation, output_path, channel_grouping_df
    )

    # On renvoie le chemin du fichier excel qui a été créé
    return str(output_path)  # Convertir en string pour plus de sécurité
