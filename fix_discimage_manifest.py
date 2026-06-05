#!/usr/bin/env python3

import argparse
import os


def parse_arguments():
    """
    Parse command-line arguments for input file and output directory.
    """
    parser = argparse.ArgumentParser(
        description="Remove lines containing '/.' from an MD5 manifest file."
    )

    # -i = input file
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Path to input .md5 file"
    )

    # -o = output directory
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Path to output directory"
    )

    return parser.parse_args()


def ensure_output_directory(output_dir):
    """
    Ensure the output directory exists. If not, create it.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)


def process_md5_file(input_file, output_dir):
    """
    Read input MD5 file, remove unwanted lines, and write cleaned output.
    """
    # Extract filename (e.g. manifest.md5)
    filename = os.path.basename(input_file)

    # Build full output file path
    output_file = os.path.join(output_dir, filename)

    # Open input file for reading
    with open(input_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()

    # Filter lines: remove any containing '/.'
    filtered_lines = []
    for line in lines:
        if "/." not in line:
            filtered_lines.append(line)
        # else → skip the line entirely

    # Write filtered lines to output file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.writelines(filtered_lines)

    print(f"Processed file written to: {output_file}")
    print(f"Removed {len(lines) - len(filtered_lines)} lines.")


def main():
    # Parse CLI arguments
    args = parse_arguments()

    input_file = args.input
    output_dir = args.output

    # Ensure output directory exists
    ensure_output_directory(output_dir)

    # Process the MD5 file
    process_md5_file(input_file, output_dir)


if __name__ == "__main__":
    main()