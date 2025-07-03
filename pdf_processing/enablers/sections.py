import os
from django.conf import settings  # Import Django settings
from pdf_processing.parsers.all_sections_parser import extract_text, parse, get_provider_colors, detect_provider_and_year, get_pages_to_process, remove_redundant_sections, save_sections

def process(pdf_path: str) -> None:
    try:
        provider, year = detect_provider_and_year(pdf_path)
        colors = get_provider_colors(provider)
        pages = get_pages_to_process(pdf_path)

        all_sections = []

        for page_number in pages:
            text, max_size = extract_text(pdf_path, colors, provider, page_number)
            sections = parse(text, provider, max_size)
            all_sections.extend(sections)

        all_sections = remove_redundant_sections(all_sections)

        output_path = os.path.join(settings.MEDIA_ROOT, 'outputs', 'section')
        os.makedirs(output_path, exist_ok=True)
        save_sections(pdf_path, all_sections, output_dir=output_path)
        print(f"Saved sections for {os.path.basename(pdf_path)} for provider {provider} and year {year}")

    except ValueError as e:
        print(f"Error processing {os.path.basename(pdf_path)}: {e}")

if __name__ == "__main__":
    folder = os.path.join(settings.MEDIA_ROOT, 'pdfs')
    process(folder)
