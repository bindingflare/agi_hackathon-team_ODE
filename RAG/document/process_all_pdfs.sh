#!/bin/bash

# Set up directories
BASE_DIR="Database"
GUIDE_DIR="$BASE_DIR/Guide"
PARSED_DIR="$BASE_DIR/Parsed"
EMBEDDED_DIR="$BASE_DIR/Embedded"

# Create output directories if they don't exist
mkdir -p "$PARSED_DIR" "$EMBEDDED_DIR"

# Get total number of PDF files
total_files=$(find "$GUIDE_DIR" -name "*.pdf" | wc -l)
echo "Found $total_files PDF files to process"

# Process each PDF file
processed=0
failed=0

for pdf_file in "$GUIDE_DIR"/*.pdf; do
    if [ ! -f "$pdf_file" ]; then
        continue
    fi
    
    filename=$(basename "$pdf_file")
    echo -e "\nProcessing file $((processed + 1))/$total_files: $filename"
    
    # Run the Python script
    if python RAG/document_embedding/main.py "$filename"; then
        echo "✅ Successfully processed $filename"
        ((processed++))
    else
        echo "❌ Failed to process $filename"
        ((failed++))
    fi
done

# Print summary
echo -e "\nProcessing complete!"
echo "Successfully processed: $processed files"
echo "Failed: $failed files"
echo "Total files: $total_files" 