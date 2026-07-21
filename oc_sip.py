#!/usr/bin/env python3

import os
import re
import shutil
import argparse
import subprocess
import time

from manifest import create_manifest_for_directory
from logger import (
    make_desktop_logs_dir,
    generate_log,
    premis_event
)
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

    print("\n--------------------------------------------------")
    print("STEP 1/7 - CLAMAV VIRUS SCAN")
    print("--------------------------------------------------")
    print(f"Scanning source directory:\n{target_dir}")
    print("Please wait...\n")
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
        print("✓ ClamAV scan completed successfully")
        print("✓ Infected files: 0")
        print("✓ Errors: 0\n")
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
# RUN COPYIT (VERIFIED COPY WITH RESULT LOGGING)
# --------------------------------------------------
def run_copyit(source, objects_dir, log_file):
    """
    Uses copyit.py to copy and verify files into objects directory
    and logs transfer outcome
    """

    command = ["python3", "copyit.py", source, objects_dir]

    print("\n--------------------------------------------------")
    print("STEP 2/7 - VERIFIED FILE TRANSFER")
    print("--------------------------------------------------")
    print(f"Source: {source}")
    print(f"Destination: {objects_dir}")
    print("Launching copyit.py...")
    print("Please wait.\n")

    premis_event(
        log_file,
        "replication",
        "started",
        f"Verified transfer initiated from {source}",
        "copyit.py",
        os.path.basename(source)
   )

    # Capture stdout/stderr from copyit
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    output = ""

    if process.stdout:
        for line in process.stdout:
            print(line.rstrip())
            output += line

    process.wait()

    if process.returncode != 0:
        print(
            f"Warning: copyit.py exited with return code "
            f"{process.returncode}"
        )

    # --------------------------------------------------
    # CHECK RESULT
    # --------------------------------------------------

    if "eventOutcome=pass" in output or "checksums match" in output:

        premis_event(
            log_file,
            "replication",
            "pass",
            "Verified copy completed. Source and destination manifests match.",
            "copyit.py"
        )
        print("✓ Verified copy completed successfully")
        print("✓ Source and destination manifests match")
        print("✓ Fixity verification passed\n")

    else:

        premis_event(
            log_file,
            "replication",
            "fail",
            "Checksum verification failed following copy operation.",
            "copyit.py"
        )
        print("✖ Copy verification failed")
        print("✖ Source and destination manifests do not match")
        print("✖ Fixity verification failed\n")

        generate_log(
            log_file,
            "Copyit output:\n" + output
        )

    generate_log(log_file, "copyit transfer and verification complete")


# --------------------------------------------------
# COPY MULTIPLE SUPPLEMENTS
# --------------------------------------------------
def copy_supplements(sup_paths, supplement_dir, log_file):

    if not sup_paths:
        print("\nSTEP 3/7 - SUPPLEMENTS")
        print("No supplements supplied.\n")
        return
    print("\n--------------------------------------------------")
    print("STEP 3/7 - COPYING SUPPLEMENTS")
    print("--------------------------------------------------")

    for sup_path in sup_paths:

        if not os.path.exists(sup_path):
            print(f"⚠ Supplement not found: {sup_path}")
            generate_log(log_file, f"Supplement not found: {sup_path}")
            continue

        if os.path.isfile(sup_path):
            print(f"Copying supplement file:")
            print(f"  {sup_path}")    
            shutil.copy2(sup_path, supplement_dir)
            print("✓ Supplement copied\n")
            generate_log(log_file, f"Supplement file copied: {sup_path}")

        elif os.path.isdir(sup_path):
            print(f"Copying supplement directory:")
            print(f"  {sup_path}")
            dest = os.path.join(supplement_dir, os.path.basename(sup_path))
            shutil.copytree(sup_path, dest, dirs_exist_ok=True)
            print("✓ Supplement directory copied\n")   
            generate_log(log_file, f"Supplement directory copied: {sup_path}")

# --------------------------------------------------
# MOVE COPYIT MANIFEST OUT OF SIP
# --------------------------------------------------
def move_copyit_manifest(objects_dir, log_file):
    """
    Move the destination manifest created by copyit.py
    from the objects directory to the Desktop moveit_manifests folder.
    """

    desktop = os.path.expanduser("~/Desktop")
    manifest_dir = os.path.join(desktop, "moveit_manifests")

    # Ensure destination folder exists
    os.makedirs(manifest_dir, exist_ok=True)

    for root, dirs, files in os.walk(objects_dir):
        for file in files:
            if file.endswith(".md5"):

                source_path = os.path.join(root, file)
                dest_path = os.path.join(manifest_dir, file)

                try:

                    print(
                        f"Moving manifest:\n"
                        f"  {file}"
                    )

                    shutil.move(source_path, dest_path)

                    print("✓ Manifest moved to Desktop/moveit_manifests\n")
                    generate_log(
                        log_file,
                        f"Moved copyit manifest: {source_path} → {dest_path}"
                    )
                except Exception as e:

                    print(
                        f"⚠ Error moving manifest:\n"
                        f"  {source_path}\n"
                        f"  {e}\n"
                    )

                    generate_log(
                        log_file,
                        f"Error moving manifest {source_path}: {e}"
                    )

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
# MERGE METADATA CSVs
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

    print("\n--------------------------------------------------")
    print("STEP 5/7 - BRUNNHILDE")
    print("--------------------------------------------------")
    print("Running Brunnhilde format identification")
    print("This may take some time...\n")
    
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
    print("✓ Brunnhilde analysis complete\n")
    generate_log(log_file, "Brunnhilde complete")


# --------------------------------------------------
# RUN JHOVE
# --------------------------------------------------
def run_jhove(objects_dir, metadata_dir, uid, log_file):

    print("\n--------------------------------------------------")
    print("STEP 6/7 - JHOVE")
    print("--------------------------------------------------")
    print("Running JHOVE validation")
    print("Please wait...\n")
    
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

    print("✓ JHOVE validation complete\n")
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

    parser.add_argument(
        '--noclam',
        action='store_true',
        help='Disable ClamAV scan (enabled by default)'
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

    premis_event(
        log_file,
        "ingestion",
        "started",
        f"SIP creation started for {args.uid}",
        "oc_sip.py",
        args.uid
)

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

    # CLAMSCAN FIRST (optional)
    if not args.noclam:
        if not run_clamscan(args.i, metadata_dir, log_file, "source"):
            return
    else:
        message = "ClamAV scan skipped (--noclam enabled)"
        print(message)
        generate_log(log_file, message)

    # VERIFIED COPY
    run_copyit(args.i, objects_dir, log_file)
    # move copyit manifest out of sip to Desktop/moveit_manifests
    move_copyit_manifest(objects_dir, log_file)

    # SUPPLEMENTS
    copy_supplements(args.sup, supplement_dir, log_file)

    # OBJECTS MANIFEST
    print("\n--------------------------------------------------")
    print("STEP 4/7 - OBJECTS MANIFEST")
    print("--------------------------------------------------")
    print("Creating objects_manifest.md5...")
    
    create_manifest_for_directory(
        objects_dir,
        os.path.join(sip_dir, "objects_manifest.md5")
    )
    move_manifest_logs(sip_dir, metadata_dir)
    print("✓ objects_manifest.md5 created\n")
    
    # TOOLS
    run_brunnhilde(objects_dir, metadata_dir, args.uid, log_file)
    run_jhove(objects_dir, metadata_dir, args.uid, log_file)

    # SIP MANIFEST
    # --------------------------------------------------

    print("\n--------------------------------------------------")
    print("STEP 7/7 - SIP MANIFEST")
    print("--------------------------------------------------")
    print("Creating SIP manifest...")
    print("Calculating checksums for the entire SIP package.\n")

    create_manifest_for_directory(
        sip_dir,
        os.path.join(args.o, f"{args.uid}_sip_manifest.md5")
    )

    print("✓ SIP manifest created")
    print("✓ SIP-level fixity information recorded\n")

    move_manifest_logs(sip_dir, metadata_dir)

    premis_event(
        log_file,
        "ingestion",
        "pass",
        "SIP creation completed successfully",
        "oc_sip.py",
        args.uid
    )

    # COPY LOG INTO SIP
    copy_log_to_metadata(log_file, metadata_dir)

    print("\n==================================================")
    print("SIP CREATION COMPLETE")
    print("==================================================")

    print("\nOutput locations:")

    print(
        f"  SIP:\n"
        f"    {sip_dir}"
    )

    print(
        f"  PREMIS Log:\n"
        f"    {log_file}"
    )

    print(
        f"  Copy manifests:\n"
        f"    ~/Desktop/moveit_manifests"
    )

    print("\n✓ SIP creation completed successfully")
    print("==================================================\n")


if __name__ == "__main__":
    main()
