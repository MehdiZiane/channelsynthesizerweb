import os
import fitz
from django.conf import settings  # Import Django settings

# from ChannelSynthesizer.src.utils import add_tv_radio_codes

VOO_info_codes = {
    "VS": "VOOsport",
    "w VS": "VOOsport World",
    "Pa": "Bouquet Panorama",
    "Ci": "Option Ciné Pass",
    "Doc": "Be Bouquet Documentaires",
    "Div": "Be Bouquet Divertissement",
    "Co": "Be Cool",
    "Enf": "Be Bouquet Enfant",
    "Sp": "Be Bouquet Sport",
    "Sel": "Be Bouquet Selection",
    "Inf": "Option Infos",
    "Sen": "Option Sensation",
    "Ch": "Option Charme",
    "FF": "Family Fun",
    "DM": "Discover More",
    "CX": "Classé X",
    "MX": "Man-X",
}

# lire les noms des sections à partir d'un fichier
def read_section_names(file_path):
    """
    cette fonction lit les noms des sections à partir du fichier donné. elle retourne une liste de noms de section.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        section_names = [line.strip() for line in f.readlines()]
    return section_names

# verifier si les noms de section sont dans une ligne
def is_section_name_in_row(words, section_names):
    """
    cette fonction vérifie si les mots donnés correspondent à un nom de section. elle retourne les indices si trouvé
    """
    section_indices = []
    for i in range(len(words)):
        for section in section_names:
            section_words = section.split()
            if words[i:i + len(section_words)] == section_words:
                section_indices.append((i, i + len(section_words) - 1))
    return section_indices

# modifier une ligne selon les noms de section
def modify_row(row, section_names):
    """
    modifie la ligne pour garder les codes d'info VOO et les regions. si rien de valides n'est trouvé, retourne la ligne originale.
    """
    words = row.split()
    filtered_words = []
    last_valid_index = -1

    for i, word in enumerate(words):
        if word in ['G', 'W', 'B', 'F']:
            last_valid_index = i
            filtered_words.append(word)
        elif word in VOO_info_codes:
            filtered_words.append(word)  # garder les codes info VOO dans la ligne
        else:
            filtered_words.append(word)

    if last_valid_index != -1:
        return " ".join(filtered_words[:last_valid_index + 1]), ""
    else:
        return " ".join(filtered_words), ""

# combiner des lignes avec les codes info VOO
def combine_lines_with_info_codes(lines):
    """
    combine les lignes qui contiennent des codes info VOO avec la ligne précédente. utile pour réduire les lignes séparées inutilement
    """
    combined_lines = []
    skip_next = False

    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue

        stripped_line = line.strip()
        if stripped_line in VOO_info_codes:
            # si cette ligne est un code info et qu'il y a une ligne suivante, on les combine
            if i < len(lines) - 1:
                combined_lines[-1] = combined_lines[-1].strip() + ' ' + stripped_line
                skip_next = True
            continue

        combined_lines.append(stripped_line)

    return combined_lines

# extraire le texte du fichier PDF
def extract_text(pdf_path):
    """
    extrait le texte du fichier PDF spécifié. renvoie le texte extrait sous forme de chaîne de caractères
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
                        text.append(span["text"])

    return "\n".join(text)

# sauvegarder le texte extrait sous forme de TSV
def save_as_tsv(text, filename: str) -> None:
    """
    sauvegarde le texte extrait sous forme de fichier TSV. cree le repertoire de sortie si nécessaire.
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

# nettoyer le fichier TSV
def clean_tsv(tsv_path):
    """
    nettoie le fichier TSV en combinant les lignes qui devraient être ensemble et en supprimant les doublons. retourne le fichier nettoyé.
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    temp_line = ""
    last_number = None

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.isdigit():
            if temp_line:
                cleaned_lines.append(temp_line.strip())
                temp_line = ""
            if last_number == stripped_line:
                temp_line += " " + stripped_line
            else:
                cleaned_lines.append(stripped_line)
            last_number = stripped_line
        else:
            temp_line += " " + stripped_line

    if temp_line:
        cleaned_lines.append(temp_line.strip())

    with open(tsv_path, 'w', encoding='utf-8') as f:
        for line in cleaned_lines:
            f.write(line + '\n')

# traiter un seul fichier TSV
def process_single_tsv(tsv_path, section_names):
    """
    traite un seul fichier TSV en combinant les lignes et en ajoutant des sections si necessaire. sauve le resultat.
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines:
        print(f"Aucun contenu à traiter dans {tsv_path}")
        return

    modified_lines = []
    previous_line = ""

    for line in lines:
        stripped_line = line.strip()

        if stripped_line in ["TV", "R"]:
            # si la ligne est juste "TV" ou "R", l'ajoute à la ligne précédente
            previous_line += f" {stripped_line}"
        else:
            # s'il y a une ligne précédente avec du contenu, l'enregistrer avant de passer à la suivante
            if previous_line:
                modified_lines.append(previous_line + "\n")
            previous_line = stripped_line

    # ajouter la dernière ligne traitée
    if previous_line:
        modified_lines.append(previous_line + "\n")

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)

    print(f"Traitement et enregistrement de {tsv_path} terminé")

# insérer les noms de section dans les lignes du TSV
def insert_section_name_rows(tsv_path, section_names):
    """
    insère les noms de section dans le fichier TSV. utile pour garder une organisation claire des sections
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        words = line.strip().split()
        section_indices = is_section_name_in_row(words, section_names)
        if section_indices:
            for start, end in section_indices:
                section_name = " ".join(words[start:end + 1])
                if section_name.strip() != line.strip():
                    new_line = " ".join(words[:start] + words[end + 1:]).strip()
                    if new_line:
                        new_lines.append(new_line + "\n")
                    new_lines.append(section_name + "\n")
                else:
                    new_lines.append(line)
        else:
            new_lines.append(line)

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"Insertion des noms de section terminée pour {tsv_path}")

# retirer une chaîne spécifique du fichier TSV
def remove_specific_string(tsv_path, target_string):
    """
    supprime une chaîne spécifique du fichier TSV. utile pour nettoyer les lignes inutiles ou en double
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    i = 0
    while i < len(lines):
        if target_string in lines[i]:
            if i > 0:
                cleaned_lines.pop()
            i += 1
            if i < len(lines):
                i += 0
        else:
            cleaned_lines.append(lines[i])
        i += 1

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)

# retirer tout ce qui vient après un mot donné
def remove_everything_after_word(tsv_path, target_word):
    """
    retire tout le contenu après un mot donné dans le fichier TSV. utile pour tronquer des lignes à partir d'un point précis
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    for line in lines:
        if target_word in line:
            index = line.find(target_word)
            cleaned_lines.append(line[:index].strip() + "\n")
            break
        cleaned_lines.append(line)

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)

# traiter les lignes longues du fichier TSV
def parse_long_lines(tsv_path):
    """
    traite les lignes trop longues dans le fichier TSV en les divisant en morceaux plus petits. permet de garder un format lisible
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    processed_lines = []
    for line in lines:
        if len(line.strip()) > 15:
            processed_lines.extend(split_long_line(line))
        else:
            processed_lines.append(line)

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(processed_lines)

# diviser une ligne longue en plusieurs
def split_long_line(line):
    """
    divise une ligne trop longue en plusieurs lignes en fonction de mots spécifiques. utile pour garder les lignes courtes et pertinentes
    """
    words = line.split()
    new_lines = []
    current_line = []

    for i, word in enumerate(words):
        current_line.append(word)
        if word in ['G', 'W', 'B', 'F'] or word in VOO_info_codes:
            new_lines.append(" ".join(current_line) + "\n")
            current_line = []

    if current_line:
        new_lines.append(" ".join(current_line) + "\n")

    return new_lines

# retirer les lignes qui suivent une chaîne spécifique
def remove_following_lines(lines, start_string):
    """
    retire les lignes suivantes après une chaîne de départ donnée. utile pour enlever des sections entières après un point
    """
    for i, line in enumerate(lines):
        if line.startswith(start_string):
            return lines[:i]
    return lines

# insérer le catalogue à la demande dans le fichier TSV
def insert_catalogue_on_demand(tsv_path):
    """
    insère la ligne 'Catalogue à la demande' après une chaîne spécifique dans le fichier TSV.
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if 'JOE FM B' in line:
            if i < len(lines) - 1 and lines[i + 1].strip():
                lines.insert(i + 1, 'Catalogue à la demande\n')
            break

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"Insertion de 'Catalogue à la demande' terminée pour {tsv_path}")

# gérer les lignes avec 'w VS' dans le fichier TSV
def handle_w_vs_rows(tsv_path):
    """
    gère les lignes commençant par 'w VS' en les combinant avec la ligne précédente.
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    skip_next = False

    for i in range(len(lines)):
        if skip_next:
            skip_next = False
            continue

        if lines[i].strip().startswith('w VS'):
            if i > 0:
                new_lines[-1] = new_lines[-1].strip() + ' ' + lines[i].strip() + '\n'
            skip_next = True
        else:
            new_lines.append(lines[i])

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"Gestion des lignes commençant par 'w VS' terminée pour {tsv_path}")

# retirer les lignes contenant uniquement un code info VOO ou étant trop longues
def remove_voo_info_code_only_or_long_rows(tsv_path):
    """
    retire les lignes qui contiennent uniquement un code info VOO ou qui dépassent 35 caractères du fichier TSV.
    """
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    for line in lines:
        stripped_line = line.strip()
        # vérifie si la ligne contient uniquement un code info VOO ou dépasse 35 caractères
        if stripped_line not in VOO_info_codes and len(stripped_line) <= 35:
            cleaned_lines.append(line)

    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)

    print(f"Removed VOO info code-only and long rows in {tsv_path}")

# parser le fichier PDF VOO et appliquer les traitements nécessaires
def parse_voo_pdf(pdf_path):
    """
    parse le fichier PDF VOO pour extraire le texte, nettoyer et traiter le contenu, et sauvegarder les résultats sous forme de fichier TSV.
    """
    text = extract_text(pdf_path)
    save_as_tsv(text, pdf_path)
    tsv_path = os.path.join(settings.MEDIA_ROOT, 'outputs', 'text', os.path.splitext(os.path.basename(pdf_path))[0] + '_text.tsv')
    clean_tsv(tsv_path)
    print(f"Sauvegardé et nettoyé {tsv_path}")

    section_tsv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../outputs/section/', os.path.splitext(os.path.basename(pdf_path))[0] + '_sections.tsv'))

    section_names = []
    if os.path.exists(section_tsv_path):
        section_names = read_section_names(section_tsv_path)
        process_single_tsv(tsv_path, section_names)
        insert_section_name_rows(tsv_path, section_names)

    remove_specific_string(tsv_path, "Retrouvez votre chaîne locale ici")
    remove_everything_after_word(tsv_path, "Retrouvez les")

    parse_long_lines(tsv_path)

    insert_catalogue_on_demand(tsv_path)
    handle_w_vs_rows(tsv_path)

    # retirer les lignes qui contiennent uniquement un code info VOO ou dépassent 35 caractères
    remove_voo_info_code_only_or_long_rows(tsv_path)
