#!/usr/bin/env python3

import os
import csv
import argparse
from collections import defaultdict


# ----------------------------------------------------------
# Function: Check if a CSV file looks like it was created by ExifTool
# ----------------------------------------------------------
def is_exiftool_csv(fieldnames):
    exif_indicators = {
        "FileName",
        "Directory",
        "FileType",
        "CreateDate",
        "ModifyDate",
        "DateTimeOriginal"
    }
    return any(field in exif_indicators for field in fieldnames)


# ----------------------------------------------------------
# Function: Identify date fields and creator fields
# ----------------------------------------------------------
def classify_fields(fieldnames):
    date_fields = []
    creator_fields = []

    for field in fieldnames:
        field_lower = field.lower()

        if any(keyword in field_lower for keyword in [
            "date", "time", "created", "creation", "modify"
        ]):
            date_fields.append(field)

        if any(keyword in field_lower for keyword in [
            "creator", "author", "artist", "by-line", "owner", "software"
        ]):
            creator_fields.append(field)

    return date_fields, creator_fields


# ----------------------------------------------------------
# Function: Process directory
# ----------------------------------------------------------
def process_directory(input_dir):

    date_field_total_counts = defaultdict(int)
    creator_field_total_counts = defaultdict(int)

    date_field_file_counts = defaultdict(int)
    creator_field_file_counts = defaultdict(int)

    # ✅ NEW: track creator values
    creator_value_total_counts = defaultdict(int)
    creator_value_csv_sets = defaultdict(set)

    total_csvs = 0
    exif_csvs = 0

    for root, dirs, files in os.walk(input_dir):
        for file in files:

            if file.endswith("_merged.csv"):
                total_csvs += 1

                file_path = os.path.join(root, file)

                try:
                    with open(file_path, newline='', encoding='utf-8') as csvfile:

                        reader = csv.DictReader(csvfile)

                        if not reader.fieldnames:
                            continue

                        if not is_exiftool_csv(reader.fieldnames):
                            continue

                        exif_csvs += 1

                        date_fields, creator_fields = classify_fields(reader.fieldnames)

                        # Count fields per file
                        for field in set(date_fields):
                            date_field_file_counts[field] += 1

                        for field in set(creator_fields):
                            creator_field_file_counts[field] += 1

                        # Process rows
                        for row in reader:

                            # Date fields
                            for field in date_fields:
                                if row.get(field):
                                    date_field_total_counts[field] += 1

                            # Creator fields + VALUE tracking
                            for field in creator_fields:
                                value = row.get(field)

                                if value:
                                    creator_field_total_counts[field] += 1

                                    # ✅ Track value usage
                                    cleaned_value = value.strip()

                                    creator_value_total_counts[cleaned_value] += 1
                                    creator_value_csv_sets[cleaned_value].add(file_path)

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    return (
        date_field_total_counts,
        date_field_file_counts,
        creator_field_total_counts,
        creator_field_file_counts,
        creator_value_total_counts,
        creator_value_csv_sets,
        total_csvs,
        exif_csvs
    )


# ----------------------------------------------------------
# Function: Write log file
# ----------------------------------------------------------
def write_log(output_path, results):

    (
        date_total,
        date_file,
        creator_total,
        creator_file,
        creator_value_total,
        creator_value_csv_sets,
        total_csvs,
        exif_csvs
    ) = results

    # Handle directory output
    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, "sip_data_results.log")

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as log:

        log.write("==== SIP METADATA ANALYSIS RESULTS ====\n\n")

        # Summary
        log.write("---- SUMMARY ----\n")
        log.write(f"Total *_merged.csv files found: {total_csvs}\n")
        log.write(f"ExifTool CSVs processed: {exif_csvs}\n")
        log.write(f"Unique date fields: {len(date_total)}\n")
        log.write(f"Unique creator fields: {len(creator_total)}\n")
        log.write(f"Unique creator values: {len(creator_value_total)}\n\n")

        # Date fields
        log.write("---- DATE FIELDS ----\n")
        for field in sorted(date_total):
            log.write(f"Field: {field}\n")
            log.write(f"  Total occurrences: {date_total[field]}\n")
            log.write(f"  CSVs containing field: {date_file[field]}\n\n")

        # Creator fields
        log.write("---- CREATOR FIELDS ----\n")
        for field in sorted(creator_total):
            log.write(f"Field: {field}\n")
            log.write(f"  Total occurrences: {creator_total[field]}\n")
            log.write(f"  CSVs containing field: {creator_file[field]}\n\n")

        # ✅ NEW: Creator values analysis
        log.write("---- CREATOR FIELD VALUES ----\n")
        for value in sorted(creator_value_total):
            log.write(f"Value: {value}\n")
            log.write(f"  Total occurrences: {creator_value_total[value]}\n")
            log.write(f"  CSVs containing this value: {len(creator_value_csv_sets[value])}\n\n")

        log.write("==== END OF REPORT ====\n")

    print(f"Results written to: {output_path}")


# ----------------------------------------------------------
# Main CLI
# ----------------------------------------------------------
def main():

    parser = argparse.ArgumentParser(
        description="Analyse ExifTool *_merged.csv files for date and creator metadata."
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Directory containing SIP folders and CSV files"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="sip_data_results.log",
        help="Output log file or directory"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input directory does not exist: {args.input}")
        return

    results = process_directory(args.input)
    write_log(args.output, results)


# ----------------------------------------------------------
# Entry point
# ----------------------------------------------------------
if __name__ == "__main__":
    main()
