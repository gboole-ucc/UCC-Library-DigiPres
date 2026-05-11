#!/usr/bin/env python3
"""
image_crop.py

Crop images using ffmpeg.
- Crops from LEFT, RIGHT, TOP, or BOTTOM
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

This script crops images using ffmpeg.

BASIC BEHAVIOUR
- Crop amount is specified in pixels
- Aspect ratio is NOT preserved
- Cropping can be horizontal or vertical

CROP DIRECTIONS
- left   : removes pixels from the left edge
- right  : removes pixels from the right edge
- top    : removes pixels from the top edge
- bottom : removes pixels from the bottom edge

ARGUMENTS
- -i  Input file or directory
- -o  Output file or directory
- -s  Side to crop from: left | right | top | bottom
- -c  Pixels to remove
- --orig-size  Optional original image size as HEIGHTxWIDTH (skips ffprobe)

EXAMPLES

Crop 200px from the right:
python image_crop.py -i image.tif -o out.tif -s right -c 200

Crop 300px from the top:
python image_crop.py -i image.tif -o out.tif -s top -c 300

Batch crop from the bottom:
python image_crop.py -i scans_in -o scans_out -s bottom -c 150

Manual size override:
python image_crop.py -i img.jpg -o out.jpg -s top -c 300 --orig-size 6000x4000
"""


# -------------------------
# Argument parsing
# -------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Crop images using ffmpeg."
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
        choices=["left", "right", "top", "bottom"],
        help="Side of the image to crop from"
    )

    parser.add_argument(
        "-c",
        dest="crop_px",
        type=int,
        help="Number of pixels to crop"
    )

    parser.add_argument(
        "--orig-size",
        dest="orig_size",
        help="Optional original image size as HEIGHTxWIDTH (e.g. 6000x4000)"
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

    # Parse --orig-size
    args.orig_height = None
    args.orig_width = None

    if args.orig_size:
        try:
            height_str, width_str = args.orig_size.lower().split("x")
            args.orig_height = int(height_str)
            args.orig_width = int(width_str)
        except ValueError:
            parser.error(
                "--orig-size must be in the format HEIGHTxWIDTH (e.g. 6000x4000)"
            )

    return args


# -----------------------------------
# ffprobe helper
# -----------------------------------

def get_image_dimensions(image_path):
    """
    Uses ffprobe to return (width, height) of an image.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x",
        str(image_path)
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )

    width, height = result.stdout.strip().split("x")
    return int(width), int(height)


# -----------------------------------
# Build ffmpeg crop filter
# -----------------------------------

def build_crop_filter(orig_width, orig_height, crop_px, side):
    """
    Returns an ffmpeg crop filter string based on crop direction.
    """

    # Horizontal crops
    if side in ("left", "right"):
        new_width = orig_width - crop_px
        if new_width <= 0:
            raise ValueError("Crop size is larger than or equal to image width")

        x_offset = crop_px if side == "left" else 0
        return f"crop={new_width}:ih:{x_offset}:0"

    # Vertical crops
    else:
        new_height = orig_height - crop_px
        if new_height <= 0:
            raise ValueError("Crop size is larger than or equal to image height")

        y_offset = crop_px if side == "top" else 0
        return f"crop=iw:{new_height}:0:{y_offset}"


# -----------------------------------
# Crop a single image
# -----------------------------------

def crop_image(input_path, output_path, side, crop_px,
               orig_width=None, orig_height=None):

    if orig_width is None or orig_height is None:
        detected_width, detected_height = get_image_dimensions(input_path)
        orig_width = orig_width or detected_width
        orig_height = orig_height or detected_height

    crop_filter = build_crop_filter(
        orig_width,
        orig_height,
        crop_px,
        side
    )

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
                    args.orig_width,
                    args.orig_height
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
            args.orig_width,
            args.orig_height
        )


# -----------------------------------
# Entry point
# -----------------------------------

if __name__ == "__main__":
    main()