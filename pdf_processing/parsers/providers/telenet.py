import os
import fitz
import re
from django.conf import settings  # Import Django settings

def extract_text(pdf_path, pages_to_process, min_font_size=5.0):
    """
    Extrait le texte d'un fichier PDF en filtrant le texte en fonction de la taille minimale de police
    et des pages spécifiées.

    Arguments:
    pdf_path -- le chemin du fichier PDF
    pages_to_process -- les pages à traiter
    min_font_size -- la taille minimale de la police à inclure (par défaut 5.0)

    Retourne:
    Le texte extrait du PDF sous forme de chaîne de caractères.
    """
    document = fitz.open(pdf_path)
    text = []

    for page_num in pages_to_process:
        page = document.load_page(page_num - 1)
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if 'lines' in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span['size'] >= min_font_size:
                            text.append(span['text'])

    return "\n".join(text)

def read_section_names(section_tsv_path):
    """
    Lit les noms de sections à partir d'un fichier TSV.

    Arguments:
    section_tsv_path -- le chemin du fichier TSV contenant les noms des sections

    Retourne:
    Une liste de noms de sections.
    """
    section_names = []
    with open(section_tsv_path, 'r', encoding='utf-8') as f:
        section_names = [line.strip() for line in f if line.strip()]
    return section_names


def process_final_tsv(tsv_path):
    """
    Traite le fichier TSV final pour déplacer des lignes spécifiques.

    Arguments:
    tsv_path -- le chemin du fichier TSV à traiter
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    joe_easy_index = None
    vox_index = None
    one_world_radio_index = None
    chaines_de_radio_index = None

    for i, line in enumerate(lines):
        if 'Joe Easy' in line:
            joe_easy_index = i
        if 'VOX' in line:
            vox_index = i
        if 'One World Radio' in line:
            one_world_radio_index = i
        if 'CHAÎNES DE RADIO' in line:
            chaines_de_radio_index = i

    if joe_easy_index is not None and vox_index is not None and one_world_radio_index is not None and chaines_de_radio_index is not None:
        block_to_move = lines[joe_easy_index:one_world_radio_index + 1]
        del lines[joe_easy_index:one_world_radio_index + 1]

        lines = lines[:chaines_de_radio_index + 1] + block_to_move + lines[chaines_de_radio_index + 1:]

    mnm_index = None
    rtl_television_index = None
    radiozenders_index = None
    one_world_radio_index = None

    for i, line in enumerate(lines):
        if re.match(r'\bMNM\b', line):
            mnm_index = i
        if 'RTL Television' in line:
            rtl_television_index = i
        if 'RADIOZENDERS' in line:
            radiozenders_index = i
        if 'One World Radio' in line:
            one_world_radio_index = i

    if mnm_index is not None and rtl_television_index is not None and mnm_index > rtl_television_index and one_world_radio_index is not None and radiozenders_index is not None:
        block_to_move = lines[mnm_index:one_world_radio_index + 1]
        del lines[mnm_index:one_world_radio_index + 1]

        lines = lines[:radiozenders_index + 1] + block_to_move + lines[radiozenders_index + 1:]

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def save_as_tsv(text, filename: str) -> str:
    """
    Enregistre le texte extrait dans un fichier TSV.

    Arguments:
    text -- le texte extrait à enregistrer
    filename -- le nom du fichier PDF original pour générer le nom du fichier TSV

    Retourne:
    Le chemin vers le fichier TSV enregistré.
    """
    output_dir = os.path.join(settings.MEDIA_ROOT, 'outputs', 'text')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_name = os.path.basename(filename)
    base_name_no_ext = os.path.splitext(base_name)[0]
    new_filename = base_name_no_ext + '_text.tsv'
    output_path = os.path.join(output_dir, new_filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        for line in text.splitlines():
            f.write(line.strip() + '\n')

    print(f"Saved TSV to {output_path}")
    return output_path


def parse_telenet_pdf(pdf_path, pages_to_process, min_font_size=5.0):
    """
    Extrait le texte d'un PDF Telenet et l'enregistre dans un fichier TSV.

    Arguments:
    pdf_path -- le chemin du fichier PDF
    pages_to_process -- les pages à traiter
    min_font_size -- la taille minimale de la police à inclure (par défaut 5.0)
    """
    print(f"Extracting text from {pdf_path} for pages {pages_to_process} with minimum font size {min_font_size}")
    text = extract_text(pdf_path, pages_to_process, min_font_size)

    section_tsv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../outputs/section/', os.path.splitext(os.path.basename(pdf_path))[0] + '_sections.tsv'))
    if os.path.exists(section_tsv_path):
        section_names = read_section_names(section_tsv_path)
    else:
        section_names = []

    cleaned_text = clean_text(text, section_names)
    tsv_path = save_as_tsv(cleaned_text, pdf_path)
    process_final_tsv(tsv_path)


def clean_text(text, section_names):
    remove_strings = [
        'telenetv.be ou l’appli Telenet TV',
        'Disponibles via le guide TV:',
        'Offre de base',
        'Région de Bruxelles',
        'et Wallonie',
        'Disponible en fonction de la région',
        'de fautes matérielles.',
        'Digiboxen.',
        'vergissingen en materiële fouten.',
        'Zenderaanbod',
        'Vlaanderen',
        '\x07',
        '*',
        'via l’appli ou le site.',
        'Basisaanbod',
        'Regio Brussel en Wallonië',
        'Al je kanalen',
        'in één oogopslag',
        'Regio Brussel en Wallonië',
        'Toutes vos chaînes',
        'en un clin d’oeil',
        '61 digitale radiozenders',
        '10 digitale muziekzenders',
        'Extra zenderpakketten',
        'van HBO Max',
        'alleen op Streamz te bekijken',
        'Meer dan 80 digitale tv-zenders',
        '+ 32 zenders',
        'Beleef sport zoals nooit tevoren',
        '2. 	Belgisch voetbal en Eredivisie',
        'en exclusieve losse crossen',
        '7. 	 24/7 golf kanaal',
        'altijd en overal',
        '+ Onbeperkt',
        'toegang  tot onze',
        'brede waaier',
        'van erotische films',
        'op aanvraag',
        'Topseries',
        'van overal en',
        'van bij onz.',
        'Voor de',
        'filmliefhebbers',
        'onder onz.',
        'Alles van Streamz+, én daarnaast:',
        '•	 Een heleboel themazenders',
        'met non-stop films.',
        'TV-gids:',
        '5',
        '€',
        '19,95',
        '24,95',
        '19,95',
        '19,95',
        '/maand',
        '11,95',
        'Via je',
        'TV-box',
        'heb je toegang tot',
        ',...',
        'Deze zenders vind je via je',
        'TV - gids:',
        'Antwerpen',
        'Brabant',
        'Internationale',
        '10 CHAÎNES DE MUSIQUE DIGITALE',
        'mentés par la rédaction sport',
        'dédiés au cinéma et aux',
        'séries.',
        'Inclus dans votre',
        'abonnement.'
    ]
    radio_channels = [
        'MNM', 'Studio Brussel', 'Klara', 'Klara Continuo', 'MNM Hits', 'VRT NWS', 'De Tijdloze', 'Q-music radio',
        'JOE fm', 'Radio Maria', 'TOPradio', 'Radio 2 Antwerpen', 'Radio 2 Limburg', 'Radio 2 Oost Vlaanderen',
        'Radio 2 West Vlaanderen', 'Play Nostalgie', 'ROXX', 'La Première', 'VivaCité', 'Musiq3', 'Tipik', 'Classic21',
        'RTBF Mix', 'Bel RTL', 'Radio Contact', 'Mint', 'Radio France Internationale', 'Family Radio', 'Willy',
        'Q-Allstars', 'Q-Foute Radio', 'Joe 60’s-70’s', 'Joe 80’s & 90’s', 'Willy Class X', 'Joe Easy', 'Nostalgie+',
        'Be One', 'Top Zen', 'NRJ', 'Radio Judaïca', 'BRF1', 'Stadradio Vlaanderen', 'One World Radio'
    ]
    cleaned_lines = []

    for line in text.splitlines():
        if line.strip() and not any(remove_string in line for remove_string in remove_strings):
            if 'L’offre de chaînes' in line:
                line = line.split('L’offre de chaînes')[0].rstrip()
            cleaned_lines.append(line)

    final_lines = []
    skip = False
    for line in cleaned_lines:
        if 'L’offre de chaînes' in line:
            skip = True
        elif skip and any(keyword in line for keyword in section_names):
            skip = False
        if not skip:
            if len(line) > 35 and not any(section in line for section in section_names):
                continue
            match = re.match(r'(\d{3})(.*)', line)
            if match:
                channel_name = match.group(2).strip()
                if channel_name in radio_channels:
                    channel_name += ' R'
                else:
                    channel_name += ' TV'
                final_lines.append(match.group(1))
                final_lines.append(channel_name)
            else:
                final_lines.append(line)

    i = 0
    while i < len(final_lines) - 1:
        if final_lines[i].isupper() and final_lines[i + 1].isupper():
            del final_lines[i + 1]
        else:
            i += 1

    return "\n".join(final_lines)
