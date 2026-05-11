#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path


SUFFIX = "_web_image"
DEFAULT_LONG_EDGE = 1600  # pixels


def show_help():
    """
    Display help text.
    """
    print(
        "Usage: python3 resize_image.py -i <input_dir> -o <output_dir> "
        "-if <jpg|jpeg|png|tif|tiff|dng> [-le <pixels>]\n\n"
        "Arguments:\n"
        "  -i     Path to the source folder containing images.\n"
        "  -o     Path to the destination folder for resized images.\n"
        "  -if    Input format to look for (jpg/jpeg, png, tif/tiff, or dng).\n"
        "  -le    Long edge size in pixels (default: 1600).\n"
        "  -h     Display this help message.\n"
    )


def parse_arguments():
    """
    Parse and normalise command-line arguments.
    """
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-i", dest="input_dir")
    parser.add_argument("-o", dest="output_dir")
    parser.add_argument("-if", dest="input_format")
    parser.add_argument("-le", dest="long_edge", type=int, default=DEFAULT_LONG_EDGE)
    parser.add_argument("-h", action="store_true")

    args = parser.parse_args()

    if args.h:
        show_help()
        sys.exit(0)

    if not all([args.input_dir, args.output_dir, args.input_format]):
        print("Error: Missing required arguments.\n")
        show_help()
        sys.exit(1)

    args.input_format = args.input_format.lstrip(".").lower()

    return args


def accepted_suffixes(input_format: str):
    """
    Return accepted suffixes for a logical input format.
    Case-insensitive matching is achieved via suffix.lower().
    """

    if input_format in {"tif", "tiff"}:
        return {".tif", ".tiff"}

    if input_format in {"jpg", "jpeg"}:
        return {".jpg", ".jpeg"}

    if input_format == "png":
        return {".png"}

    return {f".{input_format}"}


def ffmpeg_output_options(output_suffix: str):
    """
    Return format-specific, maximum-quality FFmpeg options.
    Output format is inferred from the file suffix.
    """

    if output_suffix in {".jpg", ".jpeg"}:
        return [
            "-q:v", "1",            # Highest JPEG quality
            "-pix_fmt", "yuv444p",  # No chroma subsampling (4:4:4)
        ]

    if output_suffix == ".png":
        return [
            "-compression_level", "9"  # Lossless
        ]

    if output_suffix in {".tif", ".tiff"}:
        return [
            "-compression", "lzw"      # Lossless TIFF compression
        ]

    return []


def run_ffmpeg(input_file: Path, output_file: Path, long_edge: int):
    """
    Resize image while preserving maximum non-spatial characteristics.
    Output format is the same as input format.
    """

    scale_filter = (
        f"scale="
        f"'if(gt(iw,ih),{long_edge},-2):"
        f"if(gt(iw,ih),-2,{long_edge})'"
        f":flags=lanczos"
    )

    ffmpeg_command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",

        "-i", str(input_file),

        # High-quality resizing
        "-vf", scale_filter,

        # Preserve metadata
        "-map_metadata", "0",
        "-map_metadata:s:v", "0:s:v",
    ]

    ffmpeg_command.extend(
        ffmpeg_output_options(output_file.suffix.lower())
    )

    ffmpeg_command.append(str(output_file))

    subprocess.run(ffmpeg_command, check=True)


def main():
    args = parse_arguments()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    valid_suffixes = accepted_suffixes(args.input_format)

    print("--- Starting Resize Processing ---")
    print(f"Input Dir:     {input_dir}")
    print(f"Output Dir:    {output_dir}")
    print(f"Input Type:    {args.input_format}")
    print(f"Long Edge:     {args.long_edge}px")
    print(f"Accepting:     {', '.join(sorted(valid_suffixes))}")

    files = sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in valid_suffixes
    )

    if not files:
        print("No matching files found.")
        sys.exit(0)

    print(f"Files found:   {len(files)}")

    for input_file in files:
        output_file = (
            output_dir /
            f"{input_file.stem}{SUFFIX}{input_file.suffix.lower()}"
        )

        print(f"Resizing: {input_file.name} -> {output_file.name}")

        try:
            run_ffmpeg(input_file, output_file, args.long_edge)
        except subprocess.CalledProcessError:
            print(f"Error processing file: {input_file.name}")

    print(f"Resize complete. Files written to: {output_dir}")


if __name__ == "__main__":
    main()