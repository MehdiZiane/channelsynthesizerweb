import re
import requests
import pandas as pd

from bs4 import BeautifulSoup
from datetime import datetime


def scrape_base_offer(base_url):
    """
    cette fonction scrape les offres de chaines du site BASE pour extraire les données
    elle prend en parametre l'URL de la page à scraper
    elle retourne un DataFrame contenant les informations extraites

    cette fonction va d'abord faire une requête à l'URL fournie, puis elle va parser la page HTML obtenue
    ensuite, elle va chercher les éléments des chaînes de TV ou de radio dans la page, selon les sections definies
    pour chaque chaîne trouve, les données seront ajoutees a  une liste qui sera ensuite transformée en DataFrame
    """
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    channel_data = []
    accordion_items = soup.select('.cmp-accordion__item')

    # obtenir l'année actuelle pour la période du fournisseur
    scrape_year = datetime.now().year

    for accordion_item in accordion_items:
        region_name_element = accordion_item.select_one('.cmp-accordion__header h5, .cmp-accordion__header .heading--5')
        if not region_name_element:
            print("Warning: No region name found for an accordion item, skipping.")
            continue

        region_name = region_name_element.get_text().strip().lower()

        # déterminer les codes des régions
        if 'dutch' in region_name:
            regions = [1, 1, 0, 0]   # flandre et bruxelles
        elif 'french' in region_name:
            regions = [0, 1, 1, 0]  # Wallonie et bruxelles
        else:
            # ignorer si le nom de la région n'est pas reconnu
            continue

        # déterminer si la section est TV ou Radio
        if 'radio' in region_name:
            tv_radio = 'Radio'
        else:
            tv_radio = 'TV'

        # scraper les chaînes
        channel_list_items = accordion_item.select('.cmp-text p')
        for item in channel_list_items:
            channel = item.get_text().strip()

            # enlever la numérotation au début du nom de la chaîne
            channel = re.sub(r'^\d+\.\s*', '', channel)
            # ajouter uniquement les lignes avec des noms de chaînes non vides
            if channel:
                # créer le niveau de groupe de chaînes en supprimant HD, SD, FR, et NL
                channel_group_level = re.sub(r'\b(HD|SD|FR|NL|Vlaams Brabant|Antwerpen|Limburg|Oost-Vlaanderen|West-Vlaanderen|60\'s & 70\'s|80\'s & 90\'s)\b', '', channel).strip()

                # ajouter les données de la chaîne
                channel_data.append([
                    channel,
                    f'BASE {scrape_year}',
                    *regions,
                    'Basic',
                    tv_radio,
                    # HD/SD sera déterminé plus tard, donc on laisse vide
                    '',
                    channel_group_level
                ])

    # créer un DataFrame
    df = pd.DataFrame(
        channel_data,
        columns=[
            'Channel',
            'Provider_Period',
            'Region Flanders',
            'Brussels',
            'Region Wallonia',
            'Communauté Germanophone',
            'Basic/Option',
            'TV/Radio',
            # la colonne HD/SD est ajoutee ici
            'HD/SD',
            # Channel Group Level est positionné correctement en tant que dernière colonne
            'Channel Group Level'
        ]
    )

    # supprimé les lignes avec des valeurs 'Channel' vide
    df = df.dropna(subset=['Channel'])

    return df
