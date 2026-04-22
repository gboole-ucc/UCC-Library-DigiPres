#!/bin/bash

# Function to display help instructions
show_help() {
    echo "Usage: $0 -i <input_dir> -o <output_dir> -if <jpg|tiff|dng> -of <jpg|tiff|png>"
    echo ""
    echo "Arguments:"
    echo "  -i    Path to the source folder containing images."
    echo "  -o    Path to the destination folder for resized images."
    echo "  -if   Input format to look for (jpg, tiff, or dng)."
    echo "  -of   Output format for the saved files (jpg, tiff, or png)."
    echo "  -h    Display this help message."
    echo ""
    echo "Example:"
    echo "  $0 -i ./raw_photos -o ./processed -if dng -of jpg"
}

# Initialize variables
INPUT_DIR=""
OUTPUT_DIR=""
INPUT_FORMAT=""
OUTPUT_FORMAT=""
SUFFIX="_web_image"

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -i)  INPUT_DIR="$2"; shift ;;
        -o)  OUTPUT_DIR="$2"; shift ;;
        -if) INPUT_FORMAT="${2#.}" ; shift ;; # Remove leading dot if user includes it
        -of) OUTPUT_FORMAT="${2#.}" ; shift ;; # Remove leading dot if user includes it
        -h)  show_help; exit 0 ;;
        *) echo "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
    shift
done

# Validate required arguments
if [[ -z "$INPUT_DIR" || -z "$OUTPUT_DIR" || -z "$INPUT_FORMAT" || -z "$OUTPUT_FORMAT" ]]; then
    echo "Error: Missing required arguments."
    show_help
    exit 1
fi

# Create destination if it doesn't exist; exit if creation fails
mkdir -p "$OUTPUT_DIR" || { echo "Error: Failed to create $OUTPUT_DIR"; exit 1; }

# Enable nullglob to avoid errors if no files match
shopt -s nullglob

echo "--- Starting Processing ---"
echo "Input Dir:    $INPUT_DIR"
echo "Output Dir:   $OUTPUT_DIR"
echo "Input Type:   $INPUT_FORMAT"
echo "Output Type:  $OUTPUT_FORMAT"

# Loop through files matching the specific input format
# We use case-insensitive matching in case files are .JPG vs .jpg
shopt -s nocaseglob
for f in "$INPUT_DIR"/*."$INPUT_FORMAT"; do
    
    # Get the base filename without path or extension
    filename=$(basename "$f")
    basename="${filename%.*}"
    
    echo "Processing: $filename -> ${basename}${SUFFIX}.$OUTPUT_FORMAT"
    
    # FFmpeg Command:
    ffmpeg -hide_banner -loglevel error -y -i "$f" \
    -vf "scale=iw/1.5:ih/1.5" \
    "$OUTPUT_DIR/${basename}${SUFFIX}.$OUTPUT_FORMAT"

done
shopt -u nocaseglob

echo "Process complete. Your files can be found in: $OUTPUT_DIR"
