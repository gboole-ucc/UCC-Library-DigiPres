#!/usr/bin/env python3

import os
import csv
import argparse
from collections import defaultdict


# ----------------------------------------------------------
# RAW file extensions
# ----------------------------------------------------------
RAW_EXTENSIONS = {
    '.cr2', '.cr3', '.nef', '.nrw',
    '.arw', '.srf', '.sr2',
    '.raf', '.orf', '.rw2',
    '.pef', '.x3f', '.dng',
    '.iiq'
}


# ----------------------------------------------------------
# Function: Check if CSV looks like ExifTool output
# ----------------------------------------------------------
def is_exiftool_csv(fieldnames):
    exif_indicators = {
        "FileName", "Directory", "FileType",
        "CreateDate", "ModifyDate", "DateTimeOriginal"
    }
    return any(field in exif_indicators for field in fieldnames)


# ----------------------------------------------------------
# Function: Identify date and creator fields
# ----------------------------------------------------------
def classify_fields(fieldnames):

    date_fields = []
    creator_fields = []

    for field in fieldnames:
        field_lower = field.lower()

        # Date fields
        if any(k in field_lower for k in ["date", "time", "created", "creation", "modify"]):
            date_fields.append(field)

        # Creator fields (incl. software)
        if any(k in field_lower for k in ["creator", "author", "artist", "owner", "software"]):
            creator_fields.append(field)

    return date_fields, creator_fields


# ----------------------------------------------------------
# Function: Determine if CSV matches selected format filter
# ----------------------------------------------------------
def matches_format_filter(rows, fieldnames, args):
    """
    Returns True if the CSV matches the selected format filter.
    """

    # If no filter → accept all
    if not args.tiff and not args.raw:
        return True

    # Try to use FileType first (best method)
    if "FileType" in fieldnames:
        for row in rows:
            filetype = row.get("FileType", "").lower()

            if args.tiff and "tiff" in filetype:
                return True

            if args.raw:
                for ext in RAW_EXTENSIONS:
                    if ext.replace(".", "").lower() in filetype:
                        return True

    # Fallback: inspect FileName
    if "FileName" in fieldnames:
        for row in rows:
            filename = row.get("FileName", "").lower()

            if args.tiff and (filename.endswith(".tif") or filename.endswith(".tiff")):
                return True

            if args.raw:
                for ext in RAW_EXTENSIONS:
                    if filename.endswith(ext):
                        return True

    return False


# ----------------------------------------------------------
# Function: Process directory
# ----------------------------------------------------------
def process_directory(input_dir, args):

    date_field_total_counts = defaultdict(int)
    creator_field_total_counts = defaultdict(int)

    date_field_file_counts = defaultdict(int)
    creator_field_file_counts = defaultdict(int)

    creator_value_total_counts = defaultdict(int)
    creator_value_csv_sets = defaultdict(set)

    total_csvs = 0
    exif_csvs = 0
    filtered_csvs = 0

    for root, dirs, files in os.walk(input_dir):
        for file in files:

            if file.endswith("_merged.csv"):
                total_csvs += 1
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, newline='', encoding='utf-8') as csvfile:

                        reader = list(csv.DictReader(csvfile))

                        # Skip empty
                        if not reader:
                            continue

                        fieldnames = reader[0].keys()

                        if not is_exiftool_csv(fieldnames):
                            continue

                        exif_csvs += 1

                        # ✅ Apply format filter
                        if not matches_format_filter(reader, fieldnames, args):
                            continue

                        filtered_csvs += 1

                        date_fields, creator_fields = classify_fields(fieldnames)

                        for field in set(date_fields):
                            date_field_file_counts[field] += 1

                        for field in set(creator_fields):
                            creator_field_file_counts[field] += 1

                        for row in reader:

                            # Dates
                            for field in date_fields:
                                if row.get(field):
                                    date_field_total_counts[field] += 1

                            # Creators + values
                            for field in creator_fields:
                                value = row.get(field)

                                if value:
                                    creator_field_total_counts[field] += 1

                                    cleaned = value.strip()
                                    creator_value_total_counts[cleaned] += 1
                                    creator_value_csv_sets[cleaned].add(file_path)

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
        exif_csvs,
        filtered_csvs
    )


# ----------------------------------------------------------
# Function: Write log
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
        exif_csvs,
        filtered_csvs
    ) = results

    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, "sip_data_results.log")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as log:

        log.write("==== SIP METADATA ANALYSIS RESULTS ====\n\n")

        log.write("---- SUMMARY ----\n")
        log.write(f"Total *_merged.csv files: {total_csvs}\n")
        log.write(f"ExifTool CSVs: {exif_csvs}\n")
        log.write(f"CSV after format filter: {filtered_csvs}\n")
        log.write(f"Unique date fields: {len(date_total)}\n")
        log.write(f"Unique creator fields: {len(creator_total)}\n")
        log.write(f"Unique creator values: {len(creator_value_total)}\n\n")

        log.write("---- DATE FIELDS ----\n")
        for field in sorted(date_total):
            log.write(f"{field}: {date_total[field]} (in {date_file[field]} CSVs)\n")

        log.write("\n---- CREATOR FIELDS ----\n")
        for field in sorted(creator_total):
            log.write(f"{field}: {creator_total[field]} (in {creator_file[field]} CSVs)\n")

        log.write("\n---- CREATOR VALUES ----\n")
        for value in sorted(creator_value_total):
            log.write(f"{value}: {creator_value_total[value]} (in {len(creator_value_csv_sets[value])} CSVs)\n")

    print(f"Results written to: {output_path}")


# ----------------------------------------------------------
# Main
# ----------------------------------------------------------
def main():

    parser = argparse.ArgumentParser(
        description="Analyse ExifTool *_merged.csv files with optional format filtering."
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input directory containing SIP CSVs"
    )

    parser.add_argument(
        "-o", "--output",
        default="sip_data_results.log",
        help="Output log file or directory"
    )

    # ✅ NEW FLAGS
    parser.add_argument(
        "--tiff",
        action="store_true",
        help="Only analyse TIFF files"
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="Only analyse RAW formats"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input directory does not exist: {args.input}")
        return

    results = process_directory(args.input, args)
    write_log(args.output, results)


# ----------------------------------------------------------
# Entry point
# ----------------------------------------------------------
if __name__ == "__main__":
    main()