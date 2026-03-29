#!/bin/bash
# This script finds and compiles all top-level SDF source directories into Markdown documents.
set -e

OUTPUT_DIR="build/spec"

# Clean and create the output directory
echo "Preparing output directory: $OUTPUT_DIR"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Define SDF source roots
SDF_ROOT_DIRS=("spec")

echo "Compiling SDF sources..."

for root_dir in "${SDF_ROOT_DIRS[@]}"; do
    if [ -d "$root_dir" ]; then
        # Find all top-level directories within the root that contain a manifest
        for topic_dir in "$root_dir"/*/; do
            if [ -f "${topic_dir}_topic.manifest.yaml" ]; then
                topic_name=$(basename "$topic_dir")
                output_file="$OUTPUT_DIR/${topic_name}.md"
                echo "Compiling '$topic_dir' to '$output_file'..."
                poetry run python -m mvs_harness.cli.main docs compile "$topic_dir" -o "$output_file"
            fi
        done
    else
        echo "Warning: Source root directory '$root_dir' not found. Skipping."
    fi
done

echo "Documentation build complete. See '$OUTPUT_DIR' for compiled files."
