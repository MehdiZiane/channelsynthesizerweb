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
    pdf_paths = []
    for instance in pdf_instances:
        if hasattr(instance, "file") and hasattr(instance.file, "path"):
            pdf_paths.append(instance.file.path)
        else:
            print(f"AVERTISSEMENT : Objet invalide {instance} ignoré.")

    if not pdf_paths and not include_base_offers:
        return None

    reports_dir = os.path.join(settings.MEDIA_ROOT, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    final_report_path = os.path.join(reports_dir, "consolidated_report.xlsx")

    if os.path.exists(final_report_path):
        os.remove(final_report_path)

    all_extracted_data = []

    if pdf_paths:
        print("Traitement des fichiers PDF...")
        channel_grouping_df = pd.read_excel(
            excel_file_path, sheet_name="Content_Channel_Grouping"
        )

        for pdf_path in pdf_paths:
            print(f"--- Démarrage de sections.process pour : {pdf_path} ---")
            sections_from_pdf = process_sections(pdf_path)
            if sections_from_pdf:
                all_extracted_data.append(
                    {"path": pdf_path, "sections": sections_from_pdf}
                )

        if all_extracted_data:
            # On passe les VRAIES données extraites à la fonction de génération d'Excel
            # Note: on passe le chemin final du rapport directement
            generated_path = generate_excel_report(
                final_report_path, channel_grouping_df, all_extracted_data
            )

            if not generated_path or not os.path.exists(generated_path):
                print("AVERTISSEMENT : Le rapport Excel n'a pas été généré.")

    # --- Logique existante : Gérer l'option BASE ---
    if include_base_offers:
        print("Scraping des offres BASE et ajout au rapport...")
        base_url = "https://www.prd.base.be/en/support/tv/your-base-tv-box-and-remote/what-channels-does-base-offer/"
        try:
            base_offer_df = scrape_base_offer(base_url)

            if base_offer_df.empty:
                raise ValueError(
                    "Aucune chaîne n'a été trouvée lors du scraping des offres BASE."
                )

            if os.path.exists(final_report_path):
                consolidated_df = pd.read_excel(
                    final_report_path, sheet_name="Consolidated"
                )
                columns_order = consolidated_df.columns.tolist()
                base_offer_df = base_offer_df.reindex(columns=columns_order)

                with pd.ExcelWriter(
                    final_report_path,
                    engine="openpyxl",
                    mode="a",
                    if_sheet_exists="overlay",
                ) as writer:
                    base_offer_df.to_excel(
                        writer,
                        sheet_name="Consolidated",
                        index=False,
                        header=False,
                        startrow=writer.sheets["Consolidated"].max_row,
                    )
                print("Données BASE ajoutées au rapport consolidé existant.")
            else:
                base_offer_df.to_excel(
                    final_report_path, sheet_name="Consolidated", index=False
                )
                print(
                    f"Nouveau rapport créé uniquement avec les données BASE à : {final_report_path}"
                )

        except Exception as e:
            error_message = f"Erreur lors du scraping des offres BASE : {e}"
            print(error_message)
            if os.path.exists(final_report_path):
                add_error_to_report(final_report_path, error_message)

    return final_report_path


def scrape_base_offer(base_url):
    """
    Cette fonction scrape les offres de chaînes du site BASE pour extraire les données.
    Elle prend en paramètre l'URL de la page à scraper.
    Elle retourne un DataFrame contenant les informations extraites.
    """
    response = requests.get(base_url)
    response.raise_for_status()  # Vérifie si la requête a réussi

    soup = BeautifulSoup(response.content, "html.parser")

    channel_data = []
    accordion_items = soup.select(".cmp-accordion__item")

    # Obtenir l'année actuelle pour la période du fournisseur
    scrape_year = datetime.now().year

    for accordion_item in accordion_items:
        region_name_element = accordion_item.select_one(
            ".cmp-accordion__header h5, .cmp-accordion__header .heading--5"
        )
        if not region_name_element:
            print("Warning: No region name found for an accordion item, skipping.")
            continue

        region_name = region_name_element.get_text().strip().lower()

        # Déterminer les codes des régions
        if "dutch" in region_name:
            regions = [1, 1, 0, 0]  # Flandre et Bruxelles
        elif "french" in region_name:
            regions = [0, 1, 1, 0]  # Wallonie et Bruxelles
        else:
            # Ignorer si le nom de la région n'est pas reconnu
            continue

        # Déterminer si la section est TV ou Radio
        if "radio" in region_name:
            tv_radio = "Radio"
        else:
            tv_radio = "TV"

        # Scraper les chaînes
        channel_list_items = accordion_item.select(".cmp-text p")
        for item in channel_list_items:
            channel = item.get_text().strip()

            # Enlever la numérotation au début du nom de la chaîne
            channel = re.sub(r"^\d+\.\s*", "", channel)
            # Ajouter uniquement les lignes avec des noms de chaînes non vides
            if channel:
                # Créer le niveau de groupe de chaînes en supprimant certains mots clés
                channel_group_level = re.sub(
                    r"\b(HD|SD|FR|NL|Vlaams Brabant|Antwerpen|Limburg|Oost-Vlaanderen|West-Vlaanderen|60\'s & 70\'s|80\'s & 90\'s)\b",
                    "",
                    channel,
                ).strip()

                # Déterminer HD/SD
                if "HD" in channel:
                    hd_sd = "HD"
                elif "SD" in channel:
                    hd_sd = "SD"
                else:
                    hd_sd = ""

                # Ajouter les données de la chaîne
                channel_data.append(
                    [
                        channel,  # 'Channel'
                        f"BASE {scrape_year}",  # 'Provider_Period'
                        "Basic",  # 'Basic/Option'
                        tv_radio,  # 'TV/Radio'
                        hd_sd,  # 'HD/SD'
                        channel_group_level,  # 'Channel Group Level'
                        *regions,  # 'Region Flanders', 'Brussels', 'Region Wallonia', 'Communauté Germanophone'
                    ]
                )

    # Créer un DataFrame avec les colonnes dans le bon ordre
    df = pd.DataFrame(
        channel_data,
        columns=[
            "Channel",
            "Provider_Period",
            "Basic/Option",
            "TV/Radio",
            "HD/SD",
            "Channel Group Level",
            "Region Flanders",
            "Brussels",
            "Region Wallonia",
            "Communauté Germanophone",
        ],
    )

    # Supprimer les lignes avec des valeurs 'Channel' vides
    df = df.dropna(subset=["Channel"])

    return df


def add_error_to_report(output_path, error_message):
    # Charger le fichier Excel existant
    with pd.ExcelWriter(
        output_path, engine="openpyxl", mode="a", if_sheet_exists="overlay"
    ) as writer:
        # Obtenir le nombre de lignes actuelles
        start_row = writer.sheets["Consolidated"].max_row

        # Créer un DataFrame avec le message d'erreur
        error_df = pd.DataFrame({"Channel": [error_message]})

        # Écrire le message d'erreur dans le rapport
        error_df.to_excel(
            writer,
            sheet_name="Consolidated",
            index=False,
            header=False,
            startrow=start_row,
        )
