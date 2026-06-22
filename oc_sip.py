#!/usr/bin/env python3

import os
import re
import shutil
import argparse
import subprocess

from manifest import create_manifest_for_directory
from metadata_extractor import (
    image_exiftool,
    av_mediainfo,
    others_exiftool
)

import toolkit.utils as utils


# --------------------------------------------------
# UID VALIDATION
# --------------------------------------------------
def validate_uid(uid):
    return re.match(r"^oc\d+$", uid) is not None


# --------------------------------------------------
# COPY SOURCE STRUCTURE INTO OBJECTS
# --------------------------------------------------
def copy_with_structure(src, objects_dir):
    os.makedirs(objects_dir, exist_ok=True)

    shutil.copytree(
        src,
        os.path.join(objects_dir, os.path.basename(src)),
        dirs_exist_ok=True
    )


# --------------------------------------------------
# COPY MULTIPLE SUPPLEMENTS
# --------------------------------------------------
def copy_supplements(sup_paths, supplement_dir):

    if not sup_paths:
        return

    for sup_path in sup_paths:

        if not os.path.exists(sup_path):
            print(f"Supplement path not found, skipping: {sup_path}")
            continue

        if os.path.isfile(sup_path):
            shutil.copy2(sup_path, supplement_dir)
            print(f"Supplement file copied: {sup_path}")

        elif os.path.isdir(sup_path):
            dest = os.path.join(supplement_dir, os.path.basename(sup_path))
            shutil.copytree(sup_path, dest, dirs_exist_ok=True)
            print(f"Supplement directory copied: {sup_path}")


# --------------------------------------------------
# MOVE MANIFEST LOGS INTO METADATA
# --------------------------------------------------
def move_manifest_logs(sip_dir, metadata_dir):

    for file in os.listdir(sip_dir):

        if file.startswith("manifest_creation") and file.endswith(".log"):

            src = os.path.join(sip_dir, file)
            dest = os.path.join(metadata_dir, file)

            shutil.move(src, dest)

            print(f"Moved manifest log to metadata: {file}")


# --------------------------------------------------
# DETECT FILE FORMATS
# --------------------------------------------------
def detect_formats(objects_dir):

    files = utils.collect_files(objects_dir)

    image_exts = []
    av_exts = []
    other_exts = []

    for f in files:
        ext = os.path.splitext(f)[1].lower()

        if ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
            image_exts.append(ext)
        elif ext in ['.wav', '.mp4', '.mov']:
            av_exts.append(ext)
        else:
            other_exts.append(ext)

    return (
        sorted(set(image_exts)),
        sorted(set(av_exts)),
        sorted(set(other_exts))
    )


# --------------------------------------------------
# RUN METADATA EXTRACTORS
# --------------------------------------------------
def run_metadata_extractors(objects_dir, sip_dir):

    class Args:
        pass

    metadata_root = os.path.join(sip_dir, "metadata")

    print("Detecting file formats for metadata extraction...")
    img_formats, av_formats, other_formats = detect_formats(objects_dir)

    if img_formats or other_formats:

        exif_root = os.path.join(metadata_root, "exif")
        os.makedirs(exif_root, exist_ok=True)

        args = Args()
        args.i = objects_dir
        args.dest = exif_root

        if img_formats:
            args.img = " ".join(img_formats)
            image_exiftool(args, "oc_sip_log")

        if other_formats:
            args.text = " ".join(other_formats)
            others_exiftool(args, "oc_sip_log")

    if av_formats:

        mediainfo_root = os.path.join(metadata_root, "mediainfo")
        os.makedirs(mediainfo_root, exist_ok=True)

        args = Args()
        args.i = objects_dir
        args.dest = mediainfo_root

        args.av = " ".join(av_formats)
        av_mediainfo(args, "oc_sip_log")


# --------------------------------------------------
# MERGE METADATA CSVs (FIXED)
# --------------------------------------------------
def merge_exif_outputs(metadata_dir):

    print("Merging metadata CSVs...")

    all_csv_files = utils.collect_files(metadata_dir, extensions=[".csv"])

    if not all_csv_files:
        print("No CSV files found.")
        return

    valid_csvs = []

    for csv_file in all_csv_files:

        if os.path.getsize(csv_file) == 0:
            print(f"Skipping empty CSV: {csv_file}")
            continue

        try:
            import pandas as pd
            df = pd.read_csv(csv_file)

            if df.empty or len(df.columns) == 0:
                print(f"Skipping invalid CSV: {csv_file}")
                continue

            valid_csvs.append(csv_file)

        except Exception:
            print(f"Skipping unreadable CSV: {csv_file}")
            continue

    if not valid_csvs:
        print("No valid CSVs to merge.")
        return

    toolkit_dir = os.path.join(os.path.dirname(__file__), "toolkit")

    image_mapper = os.path.join(toolkit_dir, "image_format_mapper.csv")
    other_mapper = os.path.join(toolkit_dir, "other_format_mapper.csv")

    utils.merge_metadata_csvs_by_format(
        csv_files=valid_csvs,
        image_mapper_csv=image_mapper,
        other_mapper_csv=other_mapper,
        output_dir=metadata_dir
    )

    print("Metadata CSV merging complete.")


# --------------------------------------------------
# RUN BRUNNHILDE
# --------------------------------------------------
def run_brunnhilde(objects_dir, metadata_dir, uid):

    brunnhilde_output = os.path.join(metadata_dir, f"{uid}_brunnhilde")

    if os.path.exists(brunnhilde_output):
        shutil.rmtree(brunnhilde_output)

    subprocess.run([
        "brunnhilde.py",
        objects_dir,
        brunnhilde_output
    ])

    report = os.path.join(brunnhilde_output, "report.html")
    if os.path.exists(report):
        os.rename(report, os.path.join(brunnhilde_output, f"{uid}_report.html"))

    siegfried = os.path.join(brunnhilde_output, "siegfried.csv")
    if os.path.exists(siegfried):
        os.rename(siegfried, os.path.join(brunnhilde_output, f"{uid}_siegfried.csv"))


# --------------------------------------------------
# RUN CLAMSCAN
# --------------------------------------------------
def run_clamscan(objects_dir, metadata_dir):

    output_file = os.path.join(metadata_dir, "clamscan.txt")

    command = (
        f'clamscan -r "{objects_dir}" '
        '--exclude-dir="\\.Spotlight-V100" '
        '--exclude-dir="\\.Trashes" '
        '--exclude-dir="\\.fseventsd"'
    )

    with open(output_file, "w") as f:
        subprocess.run(command, shell=True, stdout=f, stderr=subprocess.STDOUT)


# --------------------------------------------------
# RUN JHOVE
# --------------------------------------------------
def run_jhove(objects_dir, metadata_dir, uid):

    txt_output = os.path.join(metadata_dir, "jhove_output.txt")
    if os.path.exists(txt_output):
        os.remove(txt_output)

    jhove_bin = shutil.which("jhove") or os.path.expanduser("~/jhove/jhove")

    if not jhove_bin or not os.path.isfile(jhove_bin):
        return

    subprocess.run([
        jhove_bin,
        "-h", "Audit",
        "-o", os.path.join(metadata_dir, f"{uid}_jhove.xml"),
        objects_dir
    ])


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():

    parser = argparse.ArgumentParser(description="OC SIP creator")

    parser.add_argument(
        "-i",
        required=True,
        help="Input (Absolute) path of the object carrier's directory to inspect."
    )

    parser.add_argument(
        "-o", 
        required=True,
        help="Output (Absolute) path of the destination directory where the SIP will be created."
    )
    parser.add_argument(
        "-uid",
        required=True,
        help="Unique Identifier (must follow pattern oc + numbers, e.g. oc1234)."
    )

    parser.add_argument(
        "-sup",
        nargs="+",
        default=[],
        help="Enter one or more additional directories/files to be copied from a different source to the destination"
    )

    args = parser.parse_args()

    if not validate_uid(args.uid):
        print("uid input pattern incorrect. Please input following pattern oc****")
        return

    sip_dir = os.path.join(args.o, f"{args.uid}_sip")

    if os.path.exists(sip_dir):
        print("a folder named oc**** already exists in the destination directory. please choose a different uid")
        return

    objects_dir = os.path.join(sip_dir, "objects")
    metadata_dir = os.path.join(sip_dir, "metadata")
    supplement_dir = os.path.join(sip_dir, "supplement")

    os.makedirs(metadata_dir, exist_ok=True)
    os.makedirs(supplement_dir, exist_ok=True)

    copy_with_structure(args.i, objects_dir)

    copy_supplements(args.sup, supplement_dir)

    create_manifest_for_directory(
        objects_dir,
        os.path.join(sip_dir, "objects_manifest.md5")
    )

    move_manifest_logs(sip_dir, metadata_dir)

    run_metadata_extractors(objects_dir, sip_dir)

    merge_exif_outputs(metadata_dir)

    run_brunnhilde(objects_dir, metadata_dir, args.uid)
    run_clamscan(objects_dir, metadata_dir)
    run_jhove(objects_dir, metadata_dir, args.uid)

    create_manifest_for_directory(
        sip_dir,
        os.path.join(args.o, f"{args.uid}_sip_manifest.md5")
    )

    move_manifest_logs(sip_dir, metadata_dir)

    print(f"\nSIP created successfully: {sip_dir}")


if __name__ == "__main__":
    main()