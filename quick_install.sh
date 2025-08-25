#!/bin/bash

# Quick installer for fix_all_names command
# This can be run with: curl -fsSL [URL] | bash

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Installing fix_all_names command...${NC}"

# Download the script
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Download from GitHub
curl -fsSL https://raw.githubusercontent.com/ccollier86/meh/main/fix_all_names.sh -o fix_all_names

# Install to /usr/local/bin
sudo mkdir -p /usr/local/bin
sudo mv fix_all_names /usr/local/bin/
sudo chmod +x /usr/local/bin/fix_all_names

# Clean up
cd ..
rm -rf "$TEMP_DIR"

echo -e "${GREEN}✓ Installation complete!${NC}"
echo ""
echo "========================================="
echo -e "${GREEN}fix_all_names has been installed!${NC}"
echo ""
echo "Usage:"
echo "  fix_all_names                 # Fix names in current directory"
echo "  fix_all_names /path/to/dir    # Fix names in specified directory"
echo ""
echo "This will rename files from:"
echo "  LASTNAME.FIRSTNAME.MM.DD.YYYY_TH.pdf"
echo "To:"
echo "  LASTNAME_FIRSTNAME_MMDDYYYY_TH.pdf"
echo "========================================="