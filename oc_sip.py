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
from logger import make_desktop_logs_dir, generate_log
import toolkit.utils as utils


# --------------------------------------------------
# UID VALIDATION
# --------------------------------------------------
def validate_uid(uid):
    return re.match(r"^oc\d+$", uid) is not None


# --------------------------------------------------
# RUN CLAMSCAN (SOURCE WITH VALIDATION + PROMPT)
# --------------------------------------------------
def run_clamscan(target_dir, metadata_dir, log_file, label="source"):

    output_file = os.path.join(metadata_dir, f"clamscan_{label}.log")
    command = f'clamscan -r "{target_dir}"'

    print("running clamscan virus check on source directory")
    generate_log(log_file, f"Starting ClamAV scan on {label}: {target_dir}")

    with open(output_file, "w") as f:
        subprocess.run(command, shell=True, stdout=f, stderr=subprocess.STDOUT)

    infected = 0
    errors = 0

    try:
        with open(output_file, "r") as f:
            for line in f:
                if "Infected files:" in line:
                    infected = int(line.split(":")[1].strip())
                elif "Errors:" in line:
                    errors = int(line.split(":")[1].strip())
    except Exception:
        pass

    if infected == 0 and errors == 0:
        print("clamscan on source complete: no infected files, no errors")
        generate_log(log_file, "ClamAV scan complete on source: PASS")
        return True

    else:
        print(f"clamscan on source complete: {infected} infected files, {errors} errors. please see log for more information ({output_file})")
        generate_log(log_file, f"ClamAV scan complete on source: {infected} infected files, {errors} errors")

        answer = input(
            "do you want to continue creating this SIP? transferring infected files may compromise your destination environment. y/n\n"
        ).lower()

        if answer == "n":
            print("SIP creation aborted")
            generate_log(log_file, "SIP creation aborted by user")
            return False

        answer2 = input(
            f"are you very sure you want to proceed with {infected} infected files and {errors} errors y/n?\n"
        ).lower()

        if answer2 == "n":
            print("SIP creation aborted")
            generate_log(log_file, "SIP creation aborted by user")
            return False

        return True


# --------------------------------------------------
# RUN COPYIT (VERIFIED COPY)
# --------------------------------------------------
def run_copyit(source, objects_dir, log_file):
    """
    Uses copyit.py to copy and verify files into objects directory
    """

    command = ["python3", "copyit.py", source, objects_dir]

    generate_log(log_file, f"Starting verified transfer with copyit: {source}")
    subprocess.run(command)
    generate_log(log_file, "copyit transfer and verification complete")


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

    shutil.copy2(log_file, os.path.join(metadata_dir, os.path.basename(log_file)))


# --------------------------------------------------
# DETECT FILE FORMATS
# --------------------------------------------------
def detect_formats(objects_dir):

    files = utils.collect_files(objects_dir)

    image_exts, av_exts, other_exts = [], [], []

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

    class Args: pass

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
# MERGE METADATA CSVs (UNCHANGED)
# --------------------------------------------------
def merge_exif_outputs(metadata_dir, log_file):

    all_csv_files = utils.collect_files(metadata_dir, extensions=[".csv"])
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

    generate_log(log_file, "Running Brunnhilde without virus scan")

    subprocess.run([
        "brunnhilde.py",
        "--noclam",
        objects_dir,
        output
    ])

    generate_log(log_file, "Brunnhilde complete")


# --------------------------------------------------
# RUN JHOVE
# --------------------------------------------------
def run_jhove(objects_dir, metadata_dir, uid, log_file):

    jhove_bin = shutil.which("jhove") or os.path.expanduser("~/jhove/jhove")

    if not jhove_bin or not os.path.isfile(jhove_bin):
        generate_log(log_file, "JHOVE not found - skipping")
        print("JHOVE not found - skipping")
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
    os.makedirs(objects_dir, exist_ok=True)

    # CLAMSCAN FIRST
    if not run_clamscan(args.i, metadata_dir, log_file, "source"):
        return

    # VERIFIED COPY
    run_copyit(args.i, objects_dir, log_file)

    # SUPPLEMENTS
    copy_supplements(args.sup, supplement_dir, log_file)

    # OBJECTS MANIFEST
    create_manifest_for_directory(
        objects_dir,
        os.path.join(sip_dir, "objects_manifest.md5")
    )
    move_manifest_logs(sip_dir, metadata_dir)

    # METADATA
    run_metadata_extractors(objects_dir, sip_dir, log_file)
    merge_exif_outputs(metadata_dir, log_file)

    # TOOLS
    run_brunnhilde(objects_dir, metadata_dir, args.uid, log_file)
    run_jhove(objects_dir, metadata_dir, args.uid, log_file)

    # SIP MANIFEST
    create_manifest_for_directory(
        sip_dir,
        os.path.join(args.o, f"{args.uid}_sip_manifest.md5")
    )
    move_manifest_logs(sip_dir, metadata_dir)

    generate_log(log_file, "SIP creation completed successfully")

    # COPY LOG INTO SIP
    copy_log_to_metadata(log_file, metadata_dir)

    print(f"SIP created successfully: {sip_dir}")


if __name__ == "__main__":
    main()
