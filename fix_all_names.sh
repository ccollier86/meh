#!/bin/bash

# fix_all_names - Rename medical note files from dot format to underscore format
# Converts: LASTNAME.FIRSTNAME.MM.DD.YYYY_TH.pdf → LASTNAME_FIRSTNAME_MMDDYYYY_TH.pdf
# Usage: fix_all_names [directory_path]
# If no directory is provided, it will work in the current directory

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if directory argument is provided
TARGET_DIR="."
if [ $# -eq 1 ]; then
    if [ ! -d "$1" ]; then
        print_error "Directory '$1' does not exist"
        exit 1
    fi
    TARGET_DIR="$1"
fi

# Change to target directory
cd "$TARGET_DIR" || exit 1

print_info "Working in directory: $(pwd)"
echo "========================================="

count=0
skipped=0
already_correct=0

print_info "Scanning for files to rename..."
echo ""

# Find all PDF files
shopt -s nullglob  # Handle case when no files match
for file in *.pdf; do
    # Skip already corrected files
    if [[ $file == *"_CORRECTED"* ]]; then
        continue
    fi
    
    # Check if file matches the pattern we need to fix
    # Pattern: LASTNAME.FIRSTNAME.MM.DD.YYYY_SUFFIX.pdf
    if [[ $file =~ ^([A-Z][A-Z0-9\-]+)\.([A-Z][A-Z0-9\-]+)\.([0-9]{2})\.([0-9]{2})\.([0-9]{4})(_[A-Z]+)?\.pdf$ ]]; then
        lastname="${BASH_REMATCH[1]}"
        firstname="${BASH_REMATCH[2]}"
        month="${BASH_REMATCH[3]}"
        day="${BASH_REMATCH[4]}"
        year="${BASH_REMATCH[5]}"
        suffix="${BASH_REMATCH[6]}"  # This includes the underscore if present
        
        newname="${lastname}_${firstname}_${month}${day}${year}${suffix}.pdf"
        
        # Check if target file already exists
        if [ -f "$newname" ]; then
            if [ "$file" != "$newname" ]; then
                print_warning "Cannot rename $file → $newname (target already exists)"
                ((skipped++))
            else
                ((already_correct++))
            fi
            continue
        fi
        
        # Rename the file
        mv "$file" "$newname"
        print_success "Renamed: $file → $newname"
        ((count++))
        
    # Also handle pattern without suffix: LASTNAME.FIRSTNAME.MM.DD.YYYY.pdf
    elif [[ $file =~ ^([A-Z][A-Z0-9\-]+)\.([A-Z][A-Z0-9\-]+)\.([0-9]{2})\.([0-9]{2})\.([0-9]{4})\.pdf$ ]]; then
        lastname="${BASH_REMATCH[1]}"
        firstname="${BASH_REMATCH[2]}"
        month="${BASH_REMATCH[3]}"
        day="${BASH_REMATCH[4]}"
        year="${BASH_REMATCH[5]}"
        
        newname="${lastname}_${firstname}_${month}${day}${year}.pdf"
        
        # Check if target file already exists
        if [ -f "$newname" ]; then
            if [ "$file" != "$newname" ]; then
                print_warning "Cannot rename $file → $newname (target already exists)"
                ((skipped++))
            else
                ((already_correct++))
            fi
            continue
        fi
        
        # Rename the file
        mv "$file" "$newname"
        print_success "Renamed: $file → $newname"
        ((count++))
    else
        # Check if already in correct format
        if [[ $file =~ ^[A-Z][A-Z0-9\-]+_[A-Z][A-Z0-9\-]+_[0-9]{8}(_[A-Z]+)?\.pdf$ ]]; then
            ((already_correct++))
        else
            print_warning "Skipped: $file (doesn't match expected format)"
            ((skipped++))
        fi
    fi
done

echo ""
echo "========================================="
print_info "Process completed!"
echo ""
echo "  Files renamed:        $count"
echo "  Already correct:      $already_correct"
echo "  Files skipped:        $skipped"
echo "========================================="

if [ $count -gt 0 ]; then
    print_success "Successfully renamed $count file(s)"
elif [ $already_correct -gt 0 ]; then
    print_info "All files are already in the correct format"
else
    print_warning "No files found to rename"
fi