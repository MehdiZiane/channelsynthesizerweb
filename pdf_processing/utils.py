import os
import re
import subprocess
import pandas as pd
from pathlib import Path
from django.conf import settings


def get_provider_and_year(filename):
    # ... (code inchangé)
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


def is_basic_section(section_name: str) -> bool:
    section_lower = section_name.lower()
    option_keywords = [
        "optie",
        "option",
        "be tv",
        "football",
        "voosport",
        "discover more",
        "family fun",
        "penthouse",
        "+18",
    ]
    if any(keyword in section_lower for keyword in option_keywords):
        return False
    return True


def create_consolidated_excel(all_data, output_path, channel_grouping_df):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    processed_rows = []

    for provider, year, data, _, filename in all_data:
        period = f"{provider} {year}"
        for section_list in data:
            if len(section_list) < 2:
                continue

            section_title = section_list[0]

            for channel_name in section_list[1:]:
                basic_option = "Basic" if is_basic_section(section_title) else "Option"
                tv_radio = "Radio" if "radio" in section_title.lower() else "TV"

                hd_sd = ""
                if "HD" in channel_name.upper():
                    hd_sd = "HD"
                elif "SD" in channel_name.upper():
                    hd_sd = "SD"

                clean_channel_name = re.sub(
                    r"\s+(HD|SD)\b", "", channel_name, flags=re.IGNORECASE
                ).strip()

                if len(clean_channel_name) < 2:
                    continue

                regions = [0, 0, 0, 0]
                fname_lower = filename.lower()
                if "brussel" in fname_lower or "bruxelles" in fname_lower:
                    regions = [0, 1, 0, 0]
                elif "vlaanderen" in fname_lower:
                    regions = [1, 0, 0, 0]
                elif "wallonie" in fname_lower:
                    regions = [0, 0, 1, 0]
                elif "german" in fname_lower:
                    regions = [0, 0, 0, 1]

                row = (
                    [clean_channel_name, period]
                    + regions
                    + [basic_option, tv_radio, hd_sd]
                )
                processed_rows.append(row)

    if not processed_rows:
        return

    columns = [
        "Channel",
        "Provider_Period",
        "Region Flanders",
        "Brussels",
        "Region Wallonia",
        "Communauté Germanophone",
        "Basic/Option",
        "TV/Radio",
        "HD/SD",
    ]
    final_df = pd.DataFrame(processed_rows, columns=columns).drop_duplicates()

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
    # ... (code inchangé)
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


# Fonctions gardées par sécurité
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
