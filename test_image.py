import os
import fitz  # PyMuPDF
from dotenv import load_dotenv
from PIL import Image  # Pillow
from azure.core.credentials import AzureKeyCredential
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures

# --- 1. CONFIGURATION ET CHARGEMENT DES SECRETS ---
load_dotenv()
try:
    vision_endpoint = os.getenv("VISION_ENDPOINT")
    vision_key = os.getenv("VISION_KEY")
    if not vision_endpoint or not vision_key:
        raise ValueError("Erreur: Assurez-vous d'avoir défini VISION_ENDPOINT et VISION_KEY dans votre fichier .env")
except Exception as e:
    print(e)
    exit()

# !!! IMPORTANT : Vérifiez que le chemin et le nom du fichier sont corrects !!!
pdf_path = "test_files/Januari_2024_Telenet_Brussel.pdf"
output_dir = "extracted_images"
os.makedirs(output_dir, exist_ok=True)


# --- 2. EXTRACTION DES IMAGES DU PDF ---
print(f"--- Extraction des images du PDF : {pdf_path} ---")
doc = fitz.open(pdf_path)
image_paths = []
for page_num in range(len(doc)):
    page = doc[page_num]
    image_list = page.get_images(full=True)
    for img_index, img in enumerate(image_list):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]
        image_filename = f"image_page{page_num+1}_{img_index+1}.png"
        image_path = os.path.join(output_dir, image_filename)
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        image_paths.append(image_path)
print(f"--- {len(image_paths)} images extraites avec succès. ---")


# --- 3. ANALYSE DES IMAGES VALIDES AVEC AZURE AI VISION ---
print("\n--- Analyse des images avec Azure AI Vision ---")

client = ImageAnalysisClient(
    endpoint=vision_endpoint,
    credential=AzureKeyCredential(vision_key)
)
visual_features = [VisualFeatures.READ]

# On boucle sur TOUTES les images extraites
for image_path in image_paths:
    # Vérification de la taille de l'image avec Pillow
    with Image.open(image_path) as img:
        width, height = img.size

    # On ignore les images trop petites pour Azure
    if width < 50 or height < 50:
        print(f"Image ignorée (trop petite): {image_path} ({width}x{height})")
        continue  # On passe à l'image suivante

    print(f"Analyse du fichier valide : {image_path}")
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        result = client.analyze(
            image_data=image_data,
            visual_features=visual_features
        )

        print(f"--- Résultats de l'OCR pour {image_path} ---")
        if result.read is not None and result.read.blocks:
            for line in result.read.blocks[0].lines:
                print(f"  Ligne extraite: '{line.text}'")
        else:
            print("  Aucun texte n'a été détecté dans l'image.")
        print("-" * 20)
        
    except Exception as e:
        print(f"Une erreur est survenue lors de l'analyse de {image_path}: {e}")