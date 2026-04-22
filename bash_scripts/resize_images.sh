#!/bin/bash

# Function to display help instructions
show_help() {
    echo "Usage: $0 -i <input_dir> -o <output_dir> -pct <25|33|50|66|75>"
    echo ""
    echo "Arguments:"
    echo "  -i    Path to the source folder containing images."
    echo "  -o    Path to the destination folder for resized images."
    echo "  -pct  Resize percentage: 25, 33, 50, 66, or 75."
    echo "  -h    Display this help message."
    echo ""
    echo "Example:"
    echo "  $0 -i ./photos -o ./resized -pct 50"
}

# Initialize variables
INPUT_DIR=""
OUTPUT_DIR=""
PCT=""
SUFFIX="_web_image"

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -i)   INPUT_DIR="$2"; shift ;;
        -o)   OUTPUT_DIR="$2"; shift ;;
        -pct) PCT="$2"; shift ;;
        -h)   show_help; exit 0 ;;
        *) echo "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
    shift
done

# Validate required arguments
if [[ -z "$INPUT_DIR" || -z "$OUTPUT_DIR" || -z "$PCT" ]]; then
    echo "Error: Missing required arguments."
    show_help
    exit 1
fi

# Convert percentage to FFmpeg scale factor
case $PCT in
    25) SCALE="iw*0.25:ih*0.25" ;;
    33) SCALE="iw*0.33:ih*0.33" ;;
    50) SCALE="iw*0.5:ih*0.5"   ;;
    66) SCALE="iw*0.66:ih*0.66" ;;
    75) SCALE="iw*0.75:ih*0.75" ;;
    *) echo "Error: Invalid percentage. Choose 25, 33, 50, 66, or 75."; exit 1 ;;
esac

# Create destination if it doesn't exist
mkdir -p "$OUTPUT_DIR" || { echo "Error: Failed to create $OUTPUT_DIR"; exit 1; }

# Enable nullglob (ignore empty matches) and nocaseglob (catch .JPG and .jpg)
shopt -s nullglob
shopt -s nocaseglob

echo "--- Starting Processing ---"
echo "Input Dir:  $INPUT_DIR"
echo "Output Dir: $OUTPUT_DIR"
echo "Scale:      $PCT%"

# Loop through common image types
for f in "$INPUT_DIR"/*.{jpg,jpeg,png,tiff,tif,dng}; do
    
    filename=$(basename "$f")
    extension="${f##*.}"      # Extracts the extension (e.g., jpg)
    basename="${filename%.*}" # Extracts the name without extension
    
    echo "Processing: $filename -> ${basename}${SUFFIX}.$extension"
    
    # FFmpeg Command
    # The output extension matches the input extension exactly
    ffmpeg -hide_banner -loglevel error -y -i "$f" \
    -vf "scale=$SCALE" \
    "$OUTPUT_DIR/${basename}${SUFFIX}.$extension"

done

shopt -u nullglob
shopt -u nocaseglob

echo "--- Process complete ---"
