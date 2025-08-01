import os
import pandas as pd

# !!! IMPORTANT : Mettez ici le chemin vers le dossier contenant vos fichiers Excel !!!
# D'après la structure de votre projet, ils sont probablement dans 'media/excel'
excel_directory = "media/excel"

print(f"--- Inspection des fichiers Excel dans le dossier: {excel_directory} ---\n")

if not os.path.exists(excel_directory):
    print(f"Erreur : Le dossier '{excel_directory}' n'a pas été trouvé.")
else:
    # Lister tous les fichiers qui se terminent par .xlsx ou .xls
    excel_files = [
        f for f in os.listdir(excel_directory) if f.endswith((".xlsx", ".xls"))
    ]

    if not excel_files:
        print("Aucun fichier Excel trouvé dans ce dossier.")
    else:
        for filename in excel_files:
            file_path = os.path.join(excel_directory, filename)
            try:
                # On lit uniquement les 5 premières lignes pour ne pas charger tout le fichier
                df = pd.read_excel(file_path, nrows=5)

                print(f"Fichier : {filename}")
                print(f"  Colonnes : {list(df.columns)}")
                print("-" * 20)

            except Exception as e:
                print(f"Impossible de lire le fichier {filename}: {e}")
                print("-" * 20)
