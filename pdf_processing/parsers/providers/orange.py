import os
import re
import fitz
from django.conf import settings  # Import Django settings

def extract_text(pdf_path, min_font_size=8.0):
    """
    extrait le texte d'un fichier pdf en utilisant un taille de police minimal
    parcourt les pages et récupère les spans de texte qui sont plus grand que la taille spécifié
    retourne tout le texte extrait sous forme de chaîne de caractères
    """
    document = fitz.open(pdf_path)
    text = []

    for i in range(document.page_count):
        page = document.load_page(i)
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if 'lines' in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span['size'] >= min_font_size:
                            text.append(span['text'])

    return "\n".join(text)

def clean_text(text):
    """
    nettoie le texte extrait en supprimant les lignes inutiles ou trop longues
    ignore les lignes qui sont vide ou contiennent des mots spécifiques
    """
    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower() == 'app':
            continue
        if len(line) > 35:
            continue
        if line.startswith("Optie") or line.startswith("(1)"):
            continue
        if "je regionale kanaal" in line.lower():  # exclut les lignes qui contiennent "Je regionale kanaal"
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def determine_region_from_filename(filename):
    """
    determine la region a partir du nom du fichier
    analyse le nom du fichier pour detecter des mots cles de regions
    renvoie le code de region approprie ou none si aucun mot cle n'est trouve
    """
    filename = filename.lower()
    if re.search(r'flanders|vlaanderen|flamande|flandre', filename, re.IGNORECASE):
        return 'F'
    elif re.search(r'brussels|brussel|bruxelles', filename, re.IGNORECASE):
        return 'B'
    elif re.search(r'wallonia|wallonie|walloon|wallonië', filename, re.IGNORECASE):
        return 'W'
    elif re.search(r'germanophone|german-speaking|german', filename, re.IGNORECASE):
        return 'G'
    else:
        return None

def is_channel_line(line, section_names):
    """
    verifie si une ligne represente un nom de chaîne
    exclut les lignes qui sont des chiffres ou qui correspondent à un nom de section
    """
    if line.isdigit():
        return False
    if any(line.lower().startswith(section.lower()) for section in section_names):
        return False
    return True

def append_region_code_to_text(text, region_code, section_names):
    """
    ajoute le code de region à la fin de chaque ligne qui represente une chaîne
    remplit les codes de region manquants en se basant sur les lignes adjacentes
    """
    if region_code:
        lines = text.splitlines()
        processed_lines = []
        for line in lines:
            if is_channel_line(line, section_names):
                if not re.search(r'\b(F|B|W|G)\b$', line):  # si aucun code de région n'est présent
                    processed_lines.append(f"{line} {region_code}")
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)

        # traitement postérieur pour remplir les codes de région manquants
        for i, line in enumerate(processed_lines):
            if is_channel_line(line, section_names) and not re.search(r'\b(F|B|W|G)\b$', line):
                # trouve le dernier code de région valide
                for j in range(i - 1, -1, -1):
                    match = re.search(r'\b(F|B|W|G)\b$', processed_lines[j])
                    if match:
                        processed_lines[i] = f"{line} {match.group(0)}"
                        break

        return "\n".join(processed_lines)
    return text

def save_as_tsv(text, filename: str) -> None:
    """
    sauvegarde le texte nettoyé dans un fichier tsv
    créer le répertoire de sortie s'il n'existe pas
    écrit chaque ligne du texte dans le fichier tsv
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
            f.write(line + '\n')

    print(f"Saved TSV to {output_path}")

def parse_orange_pdf(pdf_path, section_names, min_font_size=8.0):
    """
    extrait et traite le texte d'un fichier pdf orange
    nettoie le texte extrait et ajoute les codes de region si necessaire
    sauvegarde le resultat dans un fichier tsv
    """
    print(f"extraction du texte de {pdf_path} avec une taille de police minimum de {min_font_size}")
    text = extract_text(pdf_path, min_font_size)
    cleaned_text = clean_text(text)

    region_code = determine_region_from_filename(os.path.basename(pdf_path))
    text_with_region_code = append_region_code_to_text(cleaned_text, region_code, section_names)

    save_as_tsv(text_with_region_code, pdf_path)
