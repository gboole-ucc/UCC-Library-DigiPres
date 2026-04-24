#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path


SUFFIX = "_web_image"


def show_help():
    """
    Display help text matching the original Bash script.
    """
    print(
        "Usage: python3 image_convert.py -i <input_dir> -o <output_dir> "
        "-if <jpg|tiff|dng> -of <jpg|tiff|png>\n\n"
        "Arguments:\n"
        "  -i    Path to the source folder containing images.\n"
        "  -o    Path to the destination folder for resized images.\n"
        "  -if   Input format to look for (jpg, tiff, or dng).\n"
        "  -of   Output format for the saved files (jpg, tiff, or png).\n"
        "  -h    Display this help message.\n\n"
        "Example:\n"
        "  python3 image_convert.py -i ./raw_photos -o ./processed -if dng -of jpg"
    )


def parse_arguments():
    """
    Parse command-line arguments using argparse.
    """
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-i", dest="input_dir")
    parser.add_argument("-o", dest="output_dir")
    parser.add_argument("-if", dest="input_format")
    parser.add_argument("-of", dest="output_format")
    parser.add_argument("-h", action="store_true")

    args = parser.parse_args()

    if args.h:
        show_help()
        sys.exit(0)

    # Validate required arguments
    if not all([args.input_dir, args.output_dir, args.input_format, args.output_format]):
        print("Error: Missing required arguments.\n")
        show_help()
        sys.exit(1)

    # Normalise formats (remove leading dots, force lowercase)
    args.input_format = args.input_format.lstrip(".").lower()
    args.output_format = args.output_format.lstrip(".").lower()

    return args


def run_ffmpeg(input_file: Path, output_file: Path):
    """
    Run FFmpeg with high-integrity image settings.
    """

    ffmpeg_command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(input_file),

        # Preserve metadata where possible
        "-map_metadata", "0",

        # High-quality scaling using Lanczos
        "-vf", "scale=iw/1.5:ih/1.5:flags=lanczos",

        # Conservative, high-quality defaults
        "-pix_fmt", "rgb24",

        str(output_file)
    ]

    subprocess.run(ffmpeg_command, check=True)


def main():
    args = parse_arguments()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    # Create output directory (fail fast if it cannot be created)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print(f"Error: Failed to create output directory: {exc}")
        sys.exit(1)

    print("--- Starting Processing ---")
    print(f"Input Dir:    {input_dir}")
    print(f"Output Dir:   {output_dir}")
    print(f"Input Type:   {args.input_format}")
    print(f"Output Type:  {args.output_format}")

    # Case-insensitive glob for input files
    files = sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() == f".{args.input_format}"
    )

    if not files:
        print("No matching files found.")
        sys.exit(0)

    for input_file in files:
        base_name = input_file.stem
        output_file = output_dir / f"{base_name}{SUFFIX}.{args.output_format}"

        print(f"Processing: {input_file.name} -> {output_file.name}")

        try:
            run_ffmpeg(input_file, output_file)
        except subprocess.CalledProcessError:
            print(f"Error processing file: {input_file.name}")

    print(f"Process complete. Your files can be found in: {output_dir}")


if __name__ == "__main__":
    main()


