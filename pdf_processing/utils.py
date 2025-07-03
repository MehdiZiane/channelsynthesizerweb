import os
import re
import subprocess

import pandas as pd
from pathlib import Path
from django.conf import settings  # Import Django settings

#BASE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))


def get_provider_and_year(filename):
    """
    cette fonction determine le nom du fournisseur et l'année du fichier
    le nom du fournisseur est chercher dans la liste et l'année est trouvé par une expression regulière
    """
    provider_names = ['voo', 'orange', 'telenet']
    provider = None
    year = None

    for name in provider_names:
        if name.lower() in filename.lower():
            provider = name.capitalize()
            break

    year_match = re.search(r'\d{4}', filename)
    if year_match:
        year = year_match.group(0)

    return provider, year


def read_section_names(file_path):
    """
    lis les noms des sections à partir d'un fichier, retournes une liste des noms
    chaque ligne du fichier est traité comme un nom de section
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        section_names = [line.strip() for line in f.readlines()]
    return section_names


def parse_tsv(tsv_path, section_names, provider):
    """
    analyse un fichier TSV, ignors les codes d'info VOO et retourne les données importantes
    :param tsv_path: chemin vers le fichier TSV
    :param section_names: liste des noms de sections
    :param provider: le nom du fournisseur (e.g., "Voo", "Telenet", "Orange")
    :return: liste des données analysées
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    data = []
    current_section = None

    for line in lines:
        stripped_line = line.strip()
        if stripped_line in section_names:
            current_section = stripped_line
        elif not stripped_line.isdigit() and not re.match(r'^\d{1,3}$', stripped_line):
            if current_section:
                data.append([current_section, stripped_line])

    return data


def ensure_region_columns_exist(df):
    """verifier que toutes les colonnes des régions existent dans le DataFrame."""
    region_columns = ['Region Flanders', 'Brussels', 'Region Wallonia', 'Communauté Germanophone']
    for col in region_columns:
        if col not in df.columns:
            df[col] = 0  # Initialiser la colonne avec des zéros
    return df


def find_file_pairs(section_dir, text_dir):
    """
    Trouver les paires de fichiers de section et texte basé sur leurs noms de fichier
    :param section_dir: répertoire contenant les fichiers de section
    :param text_dir: répertoire contenant les fichiers texte
    :return: liste de tuples, chaque tuple contient une paire de (section_file, text_file)
    """
    section_files = list(Path(section_dir).glob('*_sections.tsv'))
    text_files = list(Path(text_dir).glob('*.tsv'))

    file_pairs = []
    for section_file in section_files:
        base_name = section_file.stem.replace('_sections', '')
        text_file = next(
            (text_file for text_file in text_files if base_name in text_file.stem and '_text' in text_file.stem), None)
        if text_file:
            file_pairs.append((section_file, text_file))

    return file_pairs


def post_process_orange_regions(final_df):
    """
    verifier que tous les lignes pour Orange ont des codes de région cohérents
    :param final_df: Le DataFrame contenant toutes les données consolidées
    :return: Le DataFrame avec les codes de région Orange post-traités
    """
    # Filtrer seulement les lignes Orange
    orange_df = final_df[final_df['Provider_Period'].str.contains("Orange")]

    # Boucler à travers les lignes Orange pour appliquer la cohérence des régions
    for index, row in orange_df.iterrows():
        # Trouver quelle colonne de région a la valeur '1'
        regions = row[['Region Flanders', 'Brussels', 'Region Wallonia', 'Communauté Germanophone']]
        if regions.sum() > 1:  # Si plus d'une région est marqué comme disponible
            # Déterminer la bonne région en vérifiant les autres lignes avec le même nom de chaîne
            matching_rows = orange_df[orange_df['Channel'] == row['Channel']]
            correct_region = matching_rows[
                ['Region Flanders', 'Brussels', 'Region Wallonia', 'Communauté Germanophone']].sum(axis=0).idxmax()

            # Mettre seulement la région correcte à 1, et les autres à 0
            final_df.loc[index, ['Region Flanders', 'Brussels', 'Region Wallonia', 'Communauté Germanophone']] = 0
            final_df.loc[index, correct_region] = 1

    return final_df


def is_basic_section(section_name):
    """
    determine si un nom de section correspond à une offre de base
    :param section_name: Le nom de la section à vérifier
    :return: True si la section est considérée comme basique, sinon False
    """
    basic_sections = [
        r'BASISAANBOD',
        r'RADIOZENDERS',
        r'STINGRAY MUSIC',
        r'OFFRE DE BASE',
        r'CHAÎNES DE RADIO',
        r'CHAÎNES DE MUSIQUE',
        r'BASISAANBOD / OFFRE DE BASE',
        r'RADIOZENDERS / CHAÎNES DE RADIO',
        r'MUZIEKZENDERS/CHAÎNES DE MUSIQUE'
    ]

    # Compiler regex pour être insensible à la casse
    basic_sections_regex = re.compile('|'.join(basic_sections), re.IGNORECASE)

    return bool(basic_sections_regex.search(section_name))


def synchronize_channel_group_case(final_df):
    """
    synchroniser la casse pour les valeurs de 'Channel Group Level' qui diffèrent uniquement par la casse
    :param final_df: Le DataFrame contenant les données consolidées
    :return: DataFrame avec la casse 'Channel Group Level' synchronisé
    """
    # Grouper par minuscule 'Channel Group Level' pour trouver des doublons en ignorant la casse
    group_map = final_df.groupby(final_df['Channel Group Level'].str.lower())['Channel Group Level'].first().to_dict()

    # Appliquer la casse synchronisé
    final_df['Channel Group Level'] = final_df['Channel Group Level'].str.lower().map(group_map)

    return final_df


def create_summary_table(final_df):
    """
    cree un tableau récapitulatif basé sur les niveaux de groupe de chaînes uniques
    exclure les lignes où TV/Radio est 'Radio'
    :param final_df: Le DataFrame contenant les données consolidées
    :return: un DataFrame avec des statistiques récapitulatives
    """
    # Exclure les lignes où TV/Radio est 'Radio'
    filtered_df = final_df[final_df['TV/Radio'] != 'Radio']

    # Grouper par Provider_Period et Channel Group Level, puis supprimer les doublons
    unique_channels = filtered_df.drop_duplicates(subset=['Provider_Period', 'Channel Group Level'])

    # Tableau croisé pour compter les chaînes Basic et Option
    summary_df = unique_channels.pivot_table(index='Provider_Period',
                                             columns='Basic/Option',
                                             aggfunc='size',
                                             fill_value=0).reset_index()

    # Ajouter le total général
    summary_df['Grand Total'] = summary_df['Basic'] + summary_df['Option']

    # Renommer les colonnes
    summary_df.columns.name = None  # Retirer le nom de la colonne croisée
    summary_df = summary_df.rename(columns={'Provider_Period': 'Row Labels'})
    overall_totals = {
        'Row Labels': 'Grand Total',
        'Basic': summary_df['Basic'].sum(),
        'Option': summary_df['Option'].sum(),
        'Grand Total': summary_df['Grand Total'].sum()
    }

    # Ajouter la ligne des totaux généraux au DataFrame récapitulatif
    summary_df = summary_df._append(overall_totals, ignore_index=True)
    return summary_df


def create_consolidated_excel(all_data, output_path, channel_grouping_df):
    """
    cree un rapport excel consolide a partir des donnees analysees
    :param all_data: liste de tuples contenant le fournisseur, l'annee, les donnees et les noms de section
    :param output_path: chemin vers le fichier excel a enregistrer
    :param channel_grouping_df: dataframe contenant les correspondances de noms de chaines et de groupes
    """

    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    combined_data = []

    #dictionnaire des codes d'info voo pour mapper les noms des bouquets
    voo_info_codes = {
        "VS": "voosport",
        "w VS": "voosport world",
        "Pa": "bouquet panorama",
        "Ci": "option cine pass",
        "Doc": "be bouquet documentaires",
        "Div": "be bouquet divertissement",
        "Co": "be cool",
        "Enf": "be bouquet enfant",
        "Sp": "be bouquet sport",
        "Sel": "be bouquet selection",
        "Inf": "option infos",
        "Sen": "option sensation",
        "Ch": "option charme",
        "FF": "family fun",
        "DM": "discover more",
        "CX": "classe x",
        "MX": "man-x",
    }

    #regex pour identifier les mots cles des options orange
    orange_option_keywords = re.compile(
        r'Be |be series|be seri|be cin|cine\+|cine\+|eleven pro|voosport world',
        re.IGNORECASE
    )

    for provider, year, data, section_names, filename in all_data:
        print(f"processing provider: {provider}, year: {year}")
        print(f"data length: {len(data)}")
        period = f"{provider} {year}"
        static_columns = ['Region Flanders', 'Brussels', 'Region Wallonia', 'Communauté Germanophone']
        df_data = []

        for entry in data:
            section = entry[0]
            channel = entry[1]
            print(f"processing channel: {channel}")

            #initialiser les regions comme non disponibles
            regions = [0, 0, 0, 0]  #flanders, brussels, wallonia, germanophone

            #determiner les regions en fonction des codes de region dans le nom de la chaine
            if provider in ["Orange", "Voo"]:
                if 'W' in channel.split():
                    regions = [0, 0, 1, 0]  #seulement wallonie
                elif 'B' in channel.split():
                    regions = [0, 1, 0, 0]  #seulement bruxelles
                elif 'G' in channel.split():
                    regions = [0, 0, 0, 1]  #seulement germanophone
                elif 'F' in channel.split():
                    regions = [1, 0, 0, 0]  #seulement flandre
                else:
                    regions = [1, 1, 1, 1]  #par defaut toutes les regions

                #supprimer le code de region du nom de la chaine
                channel = re.sub(r'\b(W|B|G|F| w)\b', '', channel).strip()

            elif provider == "Telenet":
                if 'Flanders' in filename or 'Vlaanderen' in filename:
                    regions = [1, 0, 0, 0]
                elif 'Brussels' in filename or 'Bruxelles' in filename or 'Brussel' in filename:
                    regions = [0, 1, 0, 0]
                elif 'Wallonia' in filename or 'Wallonie' in filename or 'Wallonië' in filename:
                    regions = [0, 0, 1, 0]
                elif 'Germanophone' in filename or 'German-speaking' in filename or 'German' in filename:
                    regions = [0, 0, 0, 1]
                else:
                    regions = [1, 1, 0, 0]

            #determiner si la section est basic ou option pour voo
            if provider == "Voo":
                if section == 'Chaînes Be tv':
                    option = 'Option'
                elif any(code in channel.split() for code in voo_info_codes.keys()):
                    option = 'Option'
                else:
                    option = 'Basic'
                #supprimer les codes d'info voo du nom de la chaine
                channel = ' '.join([word for word in channel.split() if word not in voo_info_codes.keys()])
            elif provider == "Orange":
                #pour orange, par defaut basic sauf si le nom de la chaine correspond a un mot-cle d'option
                if orange_option_keywords.search(channel):
                    option = 'Option'
                else:
                    option = 'Basic'
            else:
                #pour d'autres fournisseurs, utiliser le nom de la section pour determiner basic ou option
                if is_basic_section(section):
                    option = 'Basic'
                else:
                    option = 'Option'

            #determiner si la chaine est tv ou radio en fonction du nom de la chaine
            if channel.endswith('TV'):
                tv_radio = 'TV'
                channel = channel[:-2].strip()  #supprimer le suffixe 'tv' du nom de la chaine
            elif channel.endswith('R'):
                tv_radio = 'Radio'
                channel = channel[:-1].strip()  #supprimer le suffixe 'r' du nom de la chaine
            else:
                tv_radio = 'TV'

            #determiner si la chaine est hd, sd, ou ni l'un ni l'autre
            if 'HD' in channel:
                hd_sd = 'HD'
            elif 'SD' in channel:
                hd_sd = 'SD'
            else:
                hd_sd = ''

            #ajouter les donnees traitees pour cette chaine
            df_data.append([channel, period] + regions + [option, tv_radio, hd_sd])

        #creer un dataframe a partir des donnees traitees
        df = pd.DataFrame(df_data,
                          columns=['Channel', 'Provider_Period'] + static_columns + ['Basic/Option', 'TV/Radio', 'HD/SD'])
        combined_data.append(df)

    # Combiner tous les DataFrames en un seul DataFrame final
    final_df = pd.concat(combined_data, ignore_index=True)

    # Appliquer un post-traitement pour la cohérence des régions Orange
    final_df = post_process_orange_regions(final_df)

    # Supprimer les lignes où la valeur de 'Channel' est simplement 'w'
    final_df = final_df[final_df['Channel'] != 'w']

    # Fusionner les données consolidées avec le DataFrame de groupement des chaînes
    if 'CHANNEL_NAME' in channel_grouping_df.columns and 'CHANNEL_NAME_GROUP' in channel_grouping_df.columns:
        final_df = final_df.merge(
            channel_grouping_df[['CHANNEL_NAME', 'CHANNEL_NAME_GROUP']],
            how='left',
            left_on='Channel',
            right_on='CHANNEL_NAME'
        )

        final_df.rename(columns={'CHANNEL_NAME_GROUP': 'Channel Group Level'}, inplace=True)
        final_df.drop(columns=['CHANNEL_NAME'], inplace=True)

        # Synchroniser la casse des noms de groupes de chaînes
        final_df = synchronize_channel_group_case(final_df)

        # Ajouter une colonne 'HD/SD'
        final_df['HD/SD'] = final_df['Channel'].apply(lambda x: 'HD' if 'HD' in x else ('SD' if 'SD' in x else ''))

        final_df = final_df[final_df['Channel'].str.strip() != '']

        # Maintenant, effectuer le groupby et l'agrégation
        region_columns = ['Region Flanders', 'Brussels', 'Region Wallonia', 'Communauté Germanophone']
        grouping_columns = ['Channel', 'Provider_Period', 'Basic/Option', 'TV/Radio', 'HD/SD', 'Channel Group Level']

        final_df = final_df.groupby(grouping_columns, as_index=False)[region_columns].max()

        # Écrire le DataFrame final dans un fichier Excel
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, sheet_name='Consolidated', index=False)

        print(f"Rapport Excel consolidé créé à : {output_path}")
    else:
        print("Les colonnes 'CHANNEL_NAME' et 'CHANNEL_NAME_GROUP' sont absentes du DataFrame de groupement.")
        

def open_file_with_default_app(file_path: str):
    """
    ouvre le fichier spécifié avec l'application par défaut du système.
    essaye d'utiliser la commande adaptée selon le système d'exploitation
    :param file_path: Chemin du fichier à ouvrir.
    """
    try:
        if os.name == 'nt':  #Windows
            os.startfile(file_path)
        elif os.uname().sysname == 'Darwin': #Mac
            subprocess.run(['open', file_path])
        else:  #Linux
            subprocess.run(['xdg-open', file_path])
    except Exception as e:
        print(f"Erreur lors de l'ouverture du fichier : {e}")


def clean_consolidated_sheet(output_path: str):
    """
    nettoyer la feuille consolidated en supprimant les lignes ou la valeur 'channel' correspond aux motifs specifies
    utilise une regex pour filtrer les chaines non valides dans le fichier excel consolide
    :param output_path: le chemin du fichier excel consolide a nettoyer
    """
    #charger la feuille 'consolidated' du fichier excel
    consolidated_df = pd.read_excel(output_path, sheet_name='Consolidated')

    #definir les motifs de suppression avec une regex
    pattern = (
        r"^[•/+-]"  #commence par •, /, -, +
        r"|^\d{1,2},\d{2}"  #commence par 1 ou 2 chiffres suivis d'une virgule (ex: 17,99)
        r"|^[a-z]+$"  #que des lettres minuscules (sans majuscules)
        r"|^[a-z]+ .+"  #commence par un mot en minuscule suivi d'un espace
        r"|\.\.\."  #contient "..." (ellipse)
        r"|\(.*\)"  #valeurs entre parentheses
    )

    #filtrer les lignes qui ne correspondent pas au motif
    cleaned_df = consolidated_df[~consolidated_df['Channel'].str.match(pattern, na=False)]

    #ecrire le dataframe nettoye dans le fichier excel
    with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        cleaned_df.to_excel(writer, sheet_name='Consolidated', index=False)

    print("les lignes correspondantes aux motifs specifies ont ete supprimees")



def check_if_file_open(file_path):
    """
    Vérifie si un fichier est actuellement ouvert par un autre programme.
    :param file_path: Chemin vers le fichier à vérifier.
    :return: True si le fichier est ouvert, False sinon.
    """
    try:
        with open(file_path, 'a'):
            pass
    except PermissionError:
        return True
    return False
