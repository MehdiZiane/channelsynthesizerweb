import os
import re
import subprocess
import pandas as pd
from pathlib import Path
from django.conf import settings


def get_provider_and_year(filename):
    provider_names = ["voo", "orange", "telenet"]
    provider = "Unknown"
    year = "Unknown"
    for name in provider_names:
        if name.lower() in filename.lower():
            provider = name.capitalize()
            break
    year_match = re.search(r"\d{4}", filename)
    if year_match:
        year = year_match.group(0)
    return provider, year


def create_consolidated_excel(all_data, output_path, channel_grouping_df):
    """
    Crée un rapport excel consolidé à partir de données DÉJÀ PROPRES ET STRUCTURÉES.
    Cette fonction est maintenant générique.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    all_dfs = []

    for provider_data in all_data:
        provider, year = get_provider_and_year(os.path.basename(provider_data["path"]))
        period = f"{provider} {year}"

        # Les données sont une liste de dictionnaires venant du parser expert
        df = pd.DataFrame(provider_data["channels"])
        df["Provider_Period"] = period
        all_dfs.append(df)

    if not all_dfs:
        print("AVERTISSEMENT : Aucune donnée à consolider.")
        return

    final_df = pd.concat(all_dfs, ignore_index=True)

    # Fusion avec les données de groupement (Channel Grouping)
    if "CHANNEL_NAME" in channel_grouping_df.columns:
        final_df = final_df.merge(
            channel_grouping_df[["CHANNEL_NAME", "CHANNEL_NAME_GROUP"]],
            how="left",
            left_on="Channel",
            right_on="CHANNEL_NAME",
        )
        final_df.rename(
            columns={"CHANNEL_NAME_GROUP": "Channel Group Level"}, inplace=True
        )
        final_df.drop(columns=["CHANNEL_NAME"], inplace=True)

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        final_df.to_excel(writer, sheet_name="Consolidated", index=False)
        summary_df = create_summary_table(final_df)
        if not summary_df.empty:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

    print(f"Rapport Excel consolidé créé à : {output_path}")


def create_summary_table(final_df):
    if final_df.empty or not all(
        col in final_df.columns
        for col in ["TV/Radio", "Provider_Period", "Basic/Option"]
    ):
        return pd.DataFrame()
    filtered_df = final_df[final_df["TV/Radio"] != "Radio"]
    if filtered_df.empty:
        return pd.DataFrame()
    if "Channel Group Level" not in filtered_df.columns:
        filtered_df["Channel Group Level"] = "N/A"
    filtered_df["Channel Group Level"] = filtered_df["Channel Group Level"].fillna(
        "N/A"
    )
    unique_channels = filtered_df.drop_duplicates(
        subset=["Provider_Period", "Channel Group Level"]
    )
    summary_df = unique_channels.pivot_table(
        index="Provider_Period", columns="Basic/Option", aggfunc="size", fill_value=0
    ).reset_index()
    if "Basic" not in summary_df.columns:
        summary_df["Basic"] = 0
    if "Option" not in summary_df.columns:
        summary_df["Option"] = 0
    summary_df["Grand Total"] = summary_df["Basic"] + summary_df["Option"]
    summary_df.columns.name = None
    summary_df = summary_df.rename(columns={"Provider_Period": "Row Labels"})
    overall_totals = {
        "Row Labels": "Grand Total",
        "Basic": summary_df["Basic"].sum(),
        "Option": summary_df["Option"].sum(),
        "Grand Total": summary_df["Grand Total"].sum(),
    }
    summary_df = pd.concat(
        [summary_df, pd.DataFrame([overall_totals])], ignore_index=True
    )
    return summary_df


# Gardées par sécurité
def read_section_names(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]


def parse_tsv(tsv_path, section_names, provider):
    with open(tsv_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    data, current_section = [], None
    for line in lines:
        stripped_line = line.strip()
        if stripped_line in section_names:
            current_section = stripped_line
        elif not stripped_line.isdigit() and not re.match(r"^\d{1,3}$", stripped_line):
            if current_section:
                data.append([current_section, stripped_line])
    return data


def add_error_to_report(output_path, error_message):
    """
    Ajoute un message d'erreur à la fin de la feuille 'Consolidated'.
    """
    try:
        with pd.ExcelWriter(
            output_path, engine="openpyxl", mode="a", if_sheet_exists="overlay"
        ) as writer:
            df = pd.DataFrame({"Error": [error_message]})
            df.to_excel(
                writer,
                sheet_name="Consolidated",
                index=False,
                header=False,
                startrow=writer.sheets["Consolidated"].max_row,
            )
    except Exception as e:
        print(f"Impossible d'ajouter le message d'erreur au rapport : {e}")
