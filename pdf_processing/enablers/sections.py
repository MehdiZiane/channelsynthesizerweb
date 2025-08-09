from pdf_processing.parsers.providers.orange import parse_orange_pdf
from pdf_processing.parsers.providers.voo import parse_voo_pdf
from pdf_processing.parsers.providers.telenet import parse_telenet_pdf

# Importer les autres parsers si vous les créez
# from pdf_processing.parsers.providers.telenet import parse_telenet_pdf


def process(pdf_path: str, provider: str):
    """
    Aiguilleur qui appelle le bon parser expert. (Version avec casse corrigée)
    """
    print(f"--- Aiguillage vers le parser expert pour {provider} ---")

    # --- CORRECTION ---
    # On compare en majuscules pour être sûr de ne pas avoir d'erreur de casse
    provider_upper = provider.upper()

    if provider_upper == "ORANGE":
        return parse_orange_pdf(pdf_path)
    elif provider_upper == "VOO":
        return parse_voo_pdf(pdf_path)
    elif provider_upper == "TELENET":  # <-- AJOUTEZ CE BLOC
        return parse_telenet_pdf(pdf_path)
    else:
        print(
            f"AVERTISSEMENT: Aucun parser expert trouvé pour {provider}. Il sera ignoré."
        )
        return []
