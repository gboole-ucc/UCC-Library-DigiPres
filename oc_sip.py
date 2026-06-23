#!/usr/bin/env python3

import os
import re
import shutil
import argparse
import subprocess
import time

from manifest import create_manifest_for_directory
from metadata_extractor import (
    image_exiftool,
    av_mediainfo,
    others_exiftool
)
from logger import make_desktop_logs_dir, generate_log, remove_bad_files
import toolkit.utils as utils


# --------------------------------------------------
# UID VALIDATION
# --------------------------------------------------
def validate_uid(uid):
    return re.match(r"^oc\d+$", uid) is not None


# --------------------------------------------------
# COPY SOURCE STRUCTURE INTO OBJECTS
# --------------------------------------------------
def copy_with_structure(src, objects_dir, log_file):

    dest_root = os.path.join(objects_dir, os.path.basename(src))

    for root, dirs, files in os.walk(src):

        dirs[:] = [
            d for d in dirs
            if d not in [".Spotlight-V100", ".Trashes", ".fseventsd"]
        ]

        rel_path = os.path.relpath(root, src)
        dest_dir = os.path.join(dest_root, rel_path)

        os.makedirs(dest_dir, exist_ok=True)

        for file in files:

            if file.startswith("._") or file == ".DS_Store":
                continue

            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_dir, file)

            try:
                shutil.copy2(src_file, dest_file)
            except Exception:
                generate_log(log_file, f"Error copying file: {src_file}")


# --------------------------------------------------
# COPY MULTIPLE SUPPLEMENTS
# --------------------------------------------------
def copy_supplements(sup_paths, supplement_dir, log_file):

    if not sup_paths:
        return

    for sup_path in sup_paths:

        if not os.path.exists(sup_path):
            generate_log(log_file, f"Supplement not found: {sup_path}")
            continue

        if os.path.isfile(sup_path):
            shutil.copy2(sup_path, supplement_dir)
            generate_log(log_file, f"Supplement file copied: {sup_path}")

        elif os.path.isdir(sup_path):
            dest = os.path.join(supplement_dir, os.path.basename(sup_path))
            shutil.copytree(sup_path, dest, dirs_exist_ok=True)
            generate_log(log_file, f"Supplement directory copied: {sup_path}")


# --------------------------------------------------
# MOVE MANIFEST LOGS INTO METADATA
# --------------------------------------------------
def move_manifest_logs(sip_dir, metadata_dir):

    for file in os.listdir(sip_dir):

        if file.startswith("manifest_creation") and file.endswith(".log"):

            shutil.move(
                os.path.join(sip_dir, file),
                os.path.join(metadata_dir, file)
            )


# --------------------------------------------------
# COPY LOG INTO METADATA
# --------------------------------------------------
def copy_log_to_metadata(log_file, metadata_dir):

    if not os.path.exists(log_file):
        return

    dest = os.path.join(metadata_dir, os.path.basename(log_file))
    shutil.copy2(log_file, dest)


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
def run_metadata_extractors(objects_dir, sip_dir, log_file):

    class Args:
        pass

    metadata_root = os.path.join(sip_dir, "metadata")

    img_formats, av_formats, other_formats = detect_formats(objects_dir)

    if img_formats or other_formats:

        exif_root = os.path.join(metadata_root, "exif")
        os.makedirs(exif_root, exist_ok=True)

        args = Args()
        args.i = objects_dir
        args.dest = exif_root

        if img_formats:
            args.img = " ".join(img_formats)
            image_exiftool(args, log_file)

        if other_formats:
            args.text = " ".join(other_formats)
            others_exiftool(args, log_file)

    if av_formats:

        mediainfo_root = os.path.join(metadata_root, "mediainfo")
        os.makedirs(mediainfo_root, exist_ok=True)

        args = Args()
        args.i = objects_dir
        args.dest = mediainfo_root
        args.av = " ".join(av_formats)

        av_mediainfo(args, log_file)


# --------------------------------------------------
# MERGE METADATA CSVs
# --------------------------------------------------
def merge_exif_outputs(metadata_dir, log_file):

    all_csv_files = utils.collect_files(metadata_dir, extensions=[".csv"])

    if not all_csv_files:
        return

    valid_csvs = []

    for csv_file in all_csv_files:

        if os.path.getsize(csv_file) == 0:
            continue

        try:
            import pandas as pd
            df = pd.read_csv(csv_file)

            if df.empty or len(df.columns) == 0:
                continue

            valid_csvs.append(csv_file)

        except Exception:
            continue

    if not valid_csvs:
        generate_log(log_file, "No valid CSVs to merge")
        return

    toolkit_dir = os.path.join(os.path.dirname(__file__), "toolkit")

    utils.merge_metadata_csvs_by_format(
        csv_files=valid_csvs,
        image_mapper_csv=os.path.join(toolkit_dir, "image_format_mapper.csv"),
        other_mapper_csv=os.path.join(toolkit_dir, "other_format_mapper.csv"),
        output_dir=metadata_dir
    )

    generate_log(log_file, "Metadata CSV merging complete")


# --------------------------------------------------
# RUN BRUNNHILDE
# --------------------------------------------------
def run_brunnhilde(objects_dir, metadata_dir, uid, log_file):

    output = os.path.join(metadata_dir, f"{uid}_brunnhilde")

    if os.path.exists(output):
        shutil.rmtree(output)

    subprocess.run(["brunnhilde.py", objects_dir, output])

    generate_log(log_file, "Brunnhilde complete")


# --------------------------------------------------
# RUN CLAMSCAN
# --------------------------------------------------
def run_clamscan(objects_dir, metadata_dir, log_file):

    output_file = os.path.join(metadata_dir, "clamscan.txt")

    command = f'clamscan -r "{objects_dir}"'

    with open(output_file, "w") as f:
        subprocess.run(command, shell=True, stdout=f, stderr=subprocess.STDOUT)

    generate_log(log_file, "ClamAV scan complete")


# --------------------------------------------------
# RUN JHOVE
# --------------------------------------------------
def run_jhove(objects_dir, metadata_dir, uid, log_file):

    jhove_bin = shutil.which("jhove")

    if not jhove_bin:
        return

    subprocess.run([
        jhove_bin,
        "-h", "Audit",
        "-o", os.path.join(metadata_dir, f"{uid}_jhove.xml"),
        objects_dir
    ])

    generate_log(log_file, "JHOVE complete")


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
        help="Output (Absolute) path of the directory to create the submission information package (sip)."
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
        print("Invalid UID format")
        return

    logs_dir = make_desktop_logs_dir()

    log_file = os.path.join(
        logs_dir,
        f"oc_sip_{args.uid}_{time.strftime('%Y%m%d_%H%M%S')}.log"
    )

    generate_log(log_file, "SIP creation started")

    sip_dir = os.path.join(args.o, f"{args.uid}_sip")

    if os.path.exists(sip_dir):
        print("SIP already exists")
        return

    objects_dir = os.path.join(sip_dir, "objects")
    metadata_dir = os.path.join(sip_dir, "metadata")
    supplement_dir = os.path.join(sip_dir, "supplement")

    os.makedirs(metadata_dir, exist_ok=True)
    os.makedirs(supplement_dir, exist_ok=True)

    copy_with_structure(args.i, objects_dir, log_file)

    remove_bad_files(objects_dir, log_file)

    copy_supplements(args.sup, supplement_dir, log_file)

    create_manifest_for_directory(
        objects_dir,
        os.path.join(sip_dir, "objects_manifest.md5")
    )
    move_manifest_logs(sip_dir, metadata_dir)

    run_metadata_extractors(objects_dir, sip_dir, log_file)

    merge_exif_outputs(metadata_dir, log_file)

    run_brunnhilde(objects_dir, metadata_dir, args.uid, log_file)
    run_clamscan(objects_dir, metadata_dir, log_file)
    run_jhove(objects_dir, metadata_dir, args.uid, log_file)

    create_manifest_for_directory(
        sip_dir,
        os.path.join(args.o, f"{args.uid}_sip_manifest.md5")
    )
    move_manifest_logs(sip_dir, metadata_dir)

    generate_log(log_file, "SIP creation completed successfully")

    copy_log_to_metadata(log_file, metadata_dir)

    print(f"SIP created successfully: {sip_dir}")


if __name__ == "__main__":
    main()
