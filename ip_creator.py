#!/usr/bin/env python3

import os
import sys
import argparse
import time
import re
import shutil
import subprocess
from logger import generate_log, make_desktop_logs_dir, remove_bad_files
from metadata_extractor import (
    format_details,
    image_exiftool,
    av_mediainfo,
    others_exiftool,
)
from manifest import create_manifest_for_directory
from validate import validate_objects_against_manifest
from utils import resolve_input_files

# Empty class to create custom objects. Useful to modify argument lists.

class Arguments:
    pass

# parses input arguments from the command line provided by the user.

def arg_parse():
    """
    Parse command-line arguments for ip_creator.py
    """

    parser = argparse.ArgumentParser(
        description=(
            "Information Package creator. Packages files of a specific format "
            "into a standard IP structure, generates manifests, extracts metadata, "
            "and optionally runs JHOVE and Brunnhilde."
        )
    )

    # Input directory (existing behaviour)
    parser.add_argument(
        "-i",
        type=str,
        help="Full path of input directory"
    )

    parser.add_argument(
        "--files",
        nargs="+",
        type=str,
        help="One or more individual files to include instead of a directory"
    )

    parser.add_argument(
        "-format",
        required=True,
        type=str,
        help="Enter the format you would like to package"
    )

    parser.add_argument(
        "-uid",
        type=str,
        default="",
        help="Enter the destination uid name you would like to assign"
    )

    parser.add_argument(
        "-o",
        type=str,
        required=True,
        help="Full path of output directory"
    )

    parser.add_argument(
        "-supplement",
        type=str,
        default="",
        help="Enter supplementary formats to preserve"
    )

    parser.add_argument(
        "-kfs",
        action="store_true",
        help="Keep original folder structure (default is flattened)"
    )

    parser.add_argument(
        "--no-jhove",
        dest="jhove",
        action="store_false",
        help="Disable JHOVE validation (enabled by default)"
    )

    # Set JHove to run as default explicitly
    parser.set_defaults(jhove=True)

    parser.add_argument(
        "--no-brunnhilde",
        dest="brunnhilde",
        action="store_false",
        help="Disable Brunnhilde (enabled by default)"
    )

    # Set Brunnhilde to run as default explicitly
    parser.set_defaults(brunnhilde=True)

     # --noclam flag: disables ClamAV when running Brunnhilde
    parser.add_argument(
        "--noclam",
        action="store_true",
        help="Disable ClamAV when running Brunnhilde"
    )

    parser.add_argument(
        "-other_sup",
        type=str,
        default="",
        help="Additional file or directory to copy into supplement"
    )

    return parser.parse_args()



# Copy objects and supplementary files to structured folder with bagit compliance

def objects_and_supplements_ip(args, log_name_source):
    """
    Copies selected object files into the objects directory and
    supplementary files into the supplement directory.
    """

    file_formats = args.format_list
    supplement_formats = args.supplement or []

    objects_folder = args.objects_folder
    supplement_folder = args.supplement_folder

    for file_src in args.input_files:

        # Guard against missing or unstable files (e.g. network shares)
        if not os.path.exists(file_src):
            msg = f"Source file missing (skipping): {file_src}"
            print(msg)
            generate_log(log_name_source, msg)
            continue

        file = os.path.basename(file_src)
        file_ext = os.path.splitext(file)[1].lower()

        # Decide a logical "root" name for flattened files
        if args.files:
            root_name = "selected_files"
        else:
            root_name = os.path.basename(os.path.dirname(file_src))

        # ---------------- Objects ----------------
        if file_ext in file_formats:

            if not args.kfs:
                # Flattened structure
                dest_name = f"{root_name}_{file}"
                dest_path = os.path.join(objects_folder, dest_name)
                shutil.copy2(file_src, dest_path)

            else:
                # Keep folder structure relative to input directory
                rel_path = os.path.relpath(
                    os.path.dirname(file_src),
                    os.path.dirname(args.i)
                )
                dest_dir = os.path.join(objects_folder, rel_path)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(file_src, os.path.join(dest_dir, file))

            generate_log(log_name_source, f"Copied object: {file_src}")

        # ---------------- Supplement ----------------
        elif supplement_formats and file_ext in supplement_formats:

            dest_name = f"{root_name}_{file}"
            dest_path = os.path.join(supplement_folder, dest_name)
            shutil.copy2(file_src, dest_path)

            generate_log(log_name_source, f"Copied supplement: {file_src}")

    generate_log(
        log_name_source,
        f"Finished processing objects and supplements for {args.format}"
    )


# ------------------------------------------------------------------------------
# UID validation
# ------------------------------------------------------------------------------
def uid_pattern_check(uid):
    """
    Enforces UID format: 4 lowercase letters + 4 digits
    """
    pattern = re.compile(r"[a-z]{4}\d{4}")
    while not pattern.fullmatch(uid):
        print("UID must be 4 lowercase letters followed by 4 digits (e.g. doaa4321)")
        uid = input("Re-enter UID: ")
    return uid


# ------------------------------------------------------------------------------
# Main execution
# ------------------------------------------------------------------------------
def main():
    args = arg_parse()

    # --------------------------------------------------------------------------
    # Validate input source
    # --------------------------------------------------------------------------
    if args.files:
        for f in args.files:
            if not os.path.isfile(f):
                print(f"Input file does not exist: {f}")
                sys.exit()
    else:
        if not args.i or not os.path.isdir(args.i):
            print("Input must be a directory unless --files is used")
            sys.exit()

    # --------------------------------------------------------------------------
    # Logging setup
    # --------------------------------------------------------------------------
    input_label = (
        "selected_files"
        if args.files
        else os.path.basename(args.i)
    )

    log_name = (
        f"ip_creator_{input_label}"
        f"{time.strftime('_%Y_%m_%dT%H_%M_%S')}.log"
    )

    log_dir = make_desktop_logs_dir()
    log_path = os.path.join(log_dir, log_name)

    # --------------------------------------------------------------------------
    # UID handling
    # --------------------------------------------------------------------------
    if not args.uid:
        args.uid = uid_pattern_check(input("Enter UID: "))
    else:
        args.uid = uid_pattern_check(args.uid)

    # --------------------------------------------------------------------------
    # Resolve format → extensions → metadata function
    # --------------------------------------------------------------------------
    fmt = args.format

    if format_details(fmt, "image_format_mapper.csv"):
        args.format_list = format_details(fmt, "image_format_mapper.csv")
        metadata_func = image_exiftool
    elif format_details(fmt, "av_format_mapper.csv"):
        args.format_list = format_details(fmt, "av_format_mapper.csv")
        metadata_func = av_mediainfo
    elif format_details(fmt, "other_format_mapper.csv"):
        args.format_list = format_details(fmt, "other_format_mapper.csv")
        metadata_func = others_exiftool
    else:
        print("Unsupported format")
        sys.exit()

    # --------------------------------------------------------------------------
    # Resolve concrete list of files to process
    # --------------------------------------------------------------------------
    try:
        args.input_files = resolve_input_files(
            input_dir=None if args.files else args.i,
            input_files=args.files,
            extensions=args.format_list,
        )
    except Exception as e:
        print(str(e))
        generate_log(log_path, str(e))
        sys.exit()

    # --------------------------------------------------------------------------
    # Prepare output structure
    # --------------------------------------------------------------------------
    output_root = os.path.join(args.o, args.uid)
    os.makedirs(output_root, exist_ok=True)

    args.objects_folder = os.path.join(output_root, "objects")
    args.metadata_folder = os.path.join(output_root, "metadata")
    args.supplement_folder = os.path.join(output_root, "supplement")

    os.makedirs(args.objects_folder, exist_ok=True)
    os.makedirs(args.metadata_folder, exist_ok=True)
    os.makedirs(args.supplement_folder, exist_ok=True)

    # --------------------------------------------------------------------------
    # Remove bad files (directory mode only)
    # --------------------------------------------------------------------------
    if not args.files:
        remove_bad_files(args.i, log_path)

    # --------------------------------------------------------------------------
    # Copy objects and supplements
    # --------------------------------------------------------------------------
    objects_and_supplements_ip(args, log_path)

    # --------------------------------------------------------------------------
    # Manifest + fixity
    # --------------------------------------------------------------------------
    manifest_path = os.path.join(output_root, "objects_manifest.md5")

    create_manifest_for_directory(
        source_dir=args.objects_folder,
        manifest_path=manifest_path,
        use_sha512=False,
    )

    if not validate_objects_against_manifest(manifest_path):
        print("Fixity validation failed")
        sys.exit()

    # --------------------------------------------------------------------------
    # Metadata extraction
    # --------------------------------------------------------------------------
    meta_args = Arguments()
    meta_args.i = args.objects_folder
    meta_args.dest = output_root

    metadata_func(meta_args, log_path)

    # --------------------------------------------------------------------------
    # JHOVE + Brunnhilde (unchanged behaviour)
    # --------------------------------------------------------------------------
    if args.jhove:
        from ip_creator import jhove_audit
        jhove_audit(args, log_path)

    if args.brunnhilde:
        from ip_creator import brunnhilde_scan
        brunnhilde_scan(args, log_path)

    print("IP creation completed successfully")


# ------------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
