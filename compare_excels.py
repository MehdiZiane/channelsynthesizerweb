import os
import pandas as pd

# Définir le chemin vers le dossier contenant vos fichiers Excel
excel_directory = "media/excel"

print(f"--- Comparaison des fichiers Excel dans le dossier: {excel_directory} ---\n")

try:
    # Lister tous les fichiers Excel dans le dossier
    excel_files = [
        f for f in os.listdir(excel_directory) if f.endswith((".xlsx", ".xls"))
    ]

    if len(excel_files) < 2:
        print(
            "Il faut au moins deux fichiers Excel pour pouvoir faire une comparaison."
        )
    else:
        # Charger le premier fichier comme base de comparaison
        base_file_path = os.path.join(excel_directory, excel_files[0])
        print(f"Fichier de référence : {excel_files[0]}")
        df_base = pd.read_excel(base_file_path).fillna(
            ""
        )  # Remplacer les cellules vides pour une comparaison juste

        # Drapeau pour suivre si on trouve des différences
        all_files_are_identical = True

        # Comparer les autres fichiers au fichier de base
        for filename in excel_files[1:]:
            current_file_path = os.path.join(excel_directory, filename)
            df_current = pd.read_excel(current_file_path).fillna(
                ""
            )  # Remplacer aussi les cellules vides ici

            # La méthode .equals() de pandas compare tout : la forme, les colonnes et toutes les valeurs.
            if not df_base.equals(df_current):
                print(
                    f"  -> ALERTE : Le fichier '{filename}' est différent du fichier de référence."
                )
                all_files_are_identical = False
            else:
                print(f"  -> Le fichier '{filename}' est identique.")

        print("\n--- Résultat Final de la Comparaison ---")
        if all_files_are_identical:
            print(
                "✅ Confirmation : Tous les fichiers Excel dans le dossier sont identiques."
            )
        else:
            print(
                "❌ Attention : Des différences ont été détectées entre les fichiers."
            )

except FileNotFoundError:
    print(f"Erreur : Le dossier '{excel_directory}' n'a pas été trouvé.")
except Exception as e:
    print(f"Une erreur inattendue est survenue : {e}")
