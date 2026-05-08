#!/usr/bin/env python3
"""
image_crop.py

Crop images horizontally using ffmpeg.
- Crops from the LEFT or RIGHT side
- Crop amount is specified in pixels
- Works on a single file or a directory (batch processing)
- Output directory is created if it does not exist
"""

# -------------------------
# Standard library imports
# -------------------------

import argparse
import subprocess
import sys
from pathlib import Path


# -------------------------
# Extended helper text
# -------------------------

HELPER_TEXT = """
EXTENDED HELPER
---------------

This script crops images horizontally using ffmpeg.

BASIC BEHAVIOUR
- Width only is changed
- Height is preserved
- Aspect ratio is NOT preserved
- Crop can occur from left or right

ARGUMENTS
- -i  Input file or directory
- -o  Output file or directory
- -s  Side to crop from: left | right
- -c  Pixels to remove
- -w  Optional original width (skips ffprobe)

EXAMPLES

Single image, crop 200px from the right:
python image_crop.py -i image.tif -o out.tif -s right -c 200

Batch crop directory from the left:
python image_crop.py -i scans_in -o scans_out -s left -c 300

Manual width override:
python image_crop.py -i img.jpg -o out.jpg -s right -c 150 -w 4000
"""


# -------------------------
# Argument parsing
# -------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Crop images horizontally using ffmpeg."
    )

    parser.add_argument(
        "-i",
        dest="input",
        help="Input image file or directory"
    )

    parser.add_argument(
        "-o",
        dest="output",
        help="Output image file or directory"
    )

    parser.add_argument(
        "-s",
        dest="side",
        choices=["left", "right"],
        help="Side of the image to crop from"
    )

    parser.add_argument(
        "-c",
        dest="crop_px",
        type=int,
        help="Number of pixels to crop"
    )

    parser.add_argument(
        "-w",
        dest="orig_width",
        type=int,
        help="Optional original image width in pixels"
    )

    parser.add_argument(
        "-H",
        "--helper",
        action="store_true",
        help="Show extended helper text and exit"
    )

    args = parser.parse_args()

    # Extended helper
    if args.helper:
        print(HELPER_TEXT)
        sys.exit(0)

    # Required arguments check
    missing = []
    if not args.input:
        missing.append("-i")
    if not args.output:
        missing.append("-o")
    if not args.side:
        missing.append("-s")
    if args.crop_px is None:
        missing.append("-c")

    if missing:
        parser.error(f"Missing required arguments: {', '.join(missing)}")

    return args


# -----------------------------------
# Get image width using ffprobe
# -----------------------------------

def get_image_width(image_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width",
        "-of", "csv=p=0",
        str(image_path)
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )

    return int(result.stdout.strip())


# -----------------------------------
# Build ffmpeg crop filter
# -----------------------------------

def build_crop_filter(orig_width, crop_px, side):
    new_width = orig_width - crop_px

    if new_width <= 0:
        raise ValueError("Crop size is larger than or equal to image width")

    x_offset = crop_px if side == "left" else 0

    return f"crop={new_width}:ih:{x_offset}:0"


# -----------------------------------
# Crop a single image
# -----------------------------------

def crop_image(input_path, output_path, side, crop_px, orig_width=None):
    if orig_width is None:
        orig_width = get_image_width(input_path)

    crop_filter = build_crop_filter(orig_width, crop_px, side)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vf", crop_filter,
        str(output_path)
    ]

    subprocess.run(cmd, check=True)


# -----------------------------------
# Main logic
# -----------------------------------

def main():
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Batch mode
    if input_path.is_dir():
        output_path.mkdir(parents=True, exist_ok=True)

        for file in input_path.iterdir():
            if file.suffix.lower() in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
                crop_image(
                    file,
                    output_path / file.name,
                    args.side,
                    args.crop_px,
                    args.orig_width
                )

    # Single file
    else:
        if output_path.is_dir():
            output_path.mkdir(parents=True, exist_ok=True)
            out_file = output_path / input_path.name
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_file = output_path

        crop_image(
            input_path,
            out_file,
            args.side,
            args.crop_px,
            args.orig_width
        )


if __name__ == "__main__":
    main()