import re
import fitz
import os
import json
from typing import List, Tuple, Dict, Optional
from django.conf import settings  # Import Django settings

# Update PAGE_SELECTION_FILE to use settings.BASE_DIR and include '.config' directory
PAGE_SELECTION_FILE = os.path.join(settings.BASE_DIR, 'pdf_processing', '.config', 'page_selection.json')

TELENET_WHITE_COLOR = 16777215
TELENET_BLACK_COLOR = 1113103  # (hex 11110f)

def is_bold_font(span: Dict) -> bool:
    return "bold" in span["font"].lower()

def is_parsable_telenet(text: str, color: int, is_bold: bool) -> bool:
    if color == TELENET_WHITE_COLOR:
        return True
    if color == TELENET_BLACK_COLOR and text.isupper() and len(text) >= 4 and not any(char.isdigit() for char in text):
        return True
    if is_bold:
        return True
    return False

def extract_text_from_page(page, provider: str, colors: List[int]) -> Tuple[List[Tuple], set]:
    extracted_text = []
    sizes = set()
    blocks = page.get_text("dict")["blocks"]

    for block in blocks:
        if 'lines' in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    if provider == "Telenet":
                        is_bold = is_bold_font(span)
                        sizes.add(span["size"])
                        extracted_text.append((span["text"], span["color"], span["size"], is_bold, line["bbox"]))
                    elif provider == "Orange" and span["color"] == TELENET_WHITE_COLOR and (
                            span["text"][0].isupper() or span["text"].startswith('+')):
                        extracted_text.append((span["text"], span["color"]))
                    elif span["color"] in colors:
                        sizes.add(span["size"])
                        extracted_text.append((span["text"], span["color"], span["size"]))

    return extracted_text, sizes

def extract_text(pdf_path: str, colors: List[int], provider: str, page_number: int) -> Tuple[List[Tuple], Optional[int]]:
    document = fitz.open(pdf_path)
    page = document.load_page(page_number - 1)
    extracted_text, sizes = extract_text_from_page(page, provider, colors)
    document.close()
    max_size = max(sizes) if provider == "VOO" else None
    return extracted_text, max_size

def parse_telenet_sections(lines: List[Tuple]) -> List[List[str]]:
    sections = []
    prev_line_info = None

    for line_info in lines:
        line, color, size, is_bold, bbox = line_info
        parsable = is_parsable_telenet(line, color, is_bold)

        if prev_line_info:
            prev_line, prev_color, prev_size, prev_is_bold, prev_bbox = prev_line_info
            prev_parsable = is_parsable_telenet(prev_line, prev_color, prev_is_bold)
            if parsable and prev_parsable and abs(bbox[1] - prev_bbox[3]) < 10:
                if prev_color == TELENET_WHITE_COLOR and color == TELENET_BLACK_COLOR:
                    sections[-1] = [line.strip()]
                elif color == TELENET_WHITE_COLOR:
                    sections[-1] = [line.strip()]
                prev_line_info = line_info
                continue

        if parsable:
            sections.append([line.strip()])
            prev_line_info = line_info
        else:
            prev_line_info = None

    return sections

def parse_other_providers_sections(lines: List[Tuple], provider: str, max_size: Optional[int] = None) -> List[List[str]]:
    sections = []
    current_section = None

    for line_info in lines:
        if provider == "VOO":
            line, color, size = line_info
            if size > 13:
                continue
            if color == TELENET_WHITE_COLOR and len(line) >= 5:
                if current_section:
                    sections.append(current_section)
                current_section = [line.strip()]
                continue
        else:
            line, color = line_info

        words = line.split()
        if len(words) == 0:
            continue

        if provider == "Orange" and (len(words) > 0 and (line[0].isupper() or line.startswith('+'))):
            if current_section:
                sections.append(current_section)
            current_section = [line.strip()]
        elif 1 < len(words) <= 3 and not any(char.isdigit() for char in line):
            if current_section:
                sections.append(current_section)
            current_section = [line.strip()]
        else:
            if current_section is not None:
                current_section.append(line.strip())

    if current_section and current_section not in sections:
        sections.append(current_section)

    return sections

def parse(text: List[Tuple], provider: str, max_size: Optional[int] = None) -> List[List[str]]:
    if provider == "Telenet":
        return parse_telenet_sections(text)
    else:
        return parse_other_providers_sections(text, provider, max_size)

def remove_redundant_sections(sections: List[List[str]]) -> List[List[str]]:
    seen_sections = set()
    unique_sections = []
    for section in sections:
        section_name = section[0]
        if section_name and section_name not in seen_sections:
            unique_sections.append(section)
            seen_sections.add(section_name)
    return unique_sections

def save_sections(filename: str, sections: List[List[str]], output_dir: str) -> None:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_name = os.path.basename(filename)
    base_name_no_ext = os.path.splitext(base_name)[0]
    new_filename = base_name_no_ext + '_sections.tsv'
    output_path = os.path.join(output_dir, new_filename)

    write_section_tsv(output_path, sections)

def write_section_tsv(file: str, sections: List[List[str]]) -> None:
    with open(file, 'w', encoding='utf-8') as f:
        for section in sections:
            if section[0]:
                f.write(section[0] + '\n')

def get_provider_colors(provider: str) -> List[int]:
    if provider == "VOO":
        return [16777215, 14092940]
    elif provider == "Telenet":
        return [TELENET_WHITE_COLOR, TELENET_BLACK_COLOR]
    elif provider == "Orange":
        return [16777215]
    else:
        raise ValueError("Unknown provider")

def detect_provider_and_year(pdf_path: str) -> Tuple[str, str]:
    filename = os.path.basename(pdf_path).lower()
    if "voo" in filename:
        provider = "VOO"
    elif "telenet" in filename:
        provider = "Telenet"
    elif "orange" in filename:
        provider = "Orange"
    else:
        raise ValueError("Provider could not be determined from filename")

    year_match = re.search(r'\d{4}', filename)
    if year_match:
        year = year_match.group(0)
    else:
        raise ValueError("Year could not be determined from filename")

    return provider, year

def load_page_selection() -> Dict[str, List[int]]:
    # Remove directory creation code
    if os.path.exists(PAGE_SELECTION_FILE):
        try:
            with open(PAGE_SELECTION_FILE, "r") as file:
                return json.load(file)
        except (json.JSONDecodeError, ValueError):
            print(f"Warning: {PAGE_SELECTION_FILE} is corrupted.")
            return {}
    return {}

# Remove save_page_selection function since we're not writing to the file in a web app

def get_pages_to_process(pdf_path: str) -> List[int]:
    page_selection = load_page_selection()
    filename = os.path.basename(pdf_path)
    if filename in page_selection:
        return page_selection[filename]

    document = fitz.open(pdf_path)
    page_count = document.page_count
    document.close()

    # Process all pages by default
    return list(range(1, page_count + 1))
