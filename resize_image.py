#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path

SUFFIX = "_web_image"

def show_help():
    print("""
Usage:
  resize_images.py -i <input_dir> -o <output_dir> -pct <25|33|50|66|75>

Arguments:
  -i    Path to the source folder containing images.
  -o    Path to the destination folder for resized images.
  -pct  Resize percentage: 25, 33, 50, 66, or 75.
  -h    Display this help message.

Example:
  resize_images.py -i ./photos -o ./resized -pct 50
""")

def parse_arguments():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-i", dest="input_dir")
    parser.add_argument("-o", dest="output_dir")
    parser.add_argument("-pct", dest="pct")
    parser.add_argument("-h", action="store_true")

    args = parser.parse_args()

    if args.h:
        show_help()
        sys.exit(0)

    if not args.input_dir or not args.output_dir or not args.pct:
        print("Error: Missing required arguments.")
        show_help()
        sys.exit(1)

    return args

def get_scale(pct):
    scale_map = {
        "25":  "iw*0.25:ih*0.25",
        "33":  "iw*0.33:ih*0.33",
        "50":  "iw*0.5:ih*0.5",
        "66":  "iw*0.66:ih*0.66",
        "75":  "iw*0.75:ih*0.75",
    }

    if pct not in scale_map:
        print("Error: Invalid percentage. Choose 25, 33, 50, 66, or 75.")
        sys.exit(1)

    return scale_map[pct]

def main():
    args = parse_arguments()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    scale = get_scale(args.pct)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("--- Starting Processing ---")
    print(f"Input Dir:  {input_dir}")
    print(f"Output Dir: {output_dir}")
    print(f"Scale:      {args.pct}%")

    extensions = [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".dng"]

    for file in input_dir.iterdir():
        if file.suffix.lower() in extensions and file.is_file():
            output_file = output_dir / f"{file.stem}{SUFFIX}{file.suffix}"

            print(f"Processing: {file.name} -> {output_file.name}")

            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-i", str(file),
                "-vf", f"scale={scale}",
                str(output_file)
            ]

            subprocess.run(cmd, check=True)

    print("--- Process complete ---")

if __name__ == "__main__":
    main()