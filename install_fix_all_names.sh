#!/bin/bash

# Installer script for fix_all_names command
# This will install the fix_all_names script as a system-wide command

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "========================================="
echo "     fix_all_names Installer"
echo "========================================="
echo ""

# Check if running as root (not recommended on macOS)
if [ "$EUID" -eq 0 ]; then 
   print_warning "Running as root is not recommended on macOS"
   print_info "Consider running without sudo"
fi

# Determine the installation directory
# On macOS, we'll use /usr/local/bin which is typically in PATH
INSTALL_DIR="/usr/local/bin"
SCRIPT_NAME="fix_all_names"
SCRIPT_PATH="$(dirname "$0")/fix_all_names.sh"

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    print_error "Script not found at: $SCRIPT_PATH"
    exit 1
fi

# Create /usr/local/bin if it doesn't exist
if [ ! -d "$INSTALL_DIR" ]; then
    print_info "Creating $INSTALL_DIR directory..."
    sudo mkdir -p "$INSTALL_DIR"
fi

# Check if command already exists
if [ -f "$INSTALL_DIR/$SCRIPT_NAME" ]; then
    print_warning "Command 'fix_all_names' already exists at $INSTALL_DIR/$SCRIPT_NAME"
    read -p "Do you want to overwrite it? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installation cancelled"
        exit 0
    fi
fi

# Copy the script to the installation directory
print_info "Installing fix_all_names to $INSTALL_DIR..."
sudo cp "$SCRIPT_PATH" "$INSTALL_DIR/$SCRIPT_NAME"

# Make it executable
print_info "Making script executable..."
sudo chmod +x "$INSTALL_DIR/$SCRIPT_NAME"

# Verify installation
if [ -f "$INSTALL_DIR/$SCRIPT_NAME" ] && [ -x "$INSTALL_DIR/$SCRIPT_NAME" ]; then
    print_success "Installation successful!"
else
    print_error "Installation failed"
    exit 1
fi

# Check if /usr/local/bin is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    print_warning "$INSTALL_DIR is not in your PATH"
    print_info "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "    export PATH=\"$INSTALL_DIR:\$PATH\""
    echo ""
fi

echo ""
echo "========================================="
print_success "fix_all_names has been installed!"
echo ""
echo "Usage:"
echo "  fix_all_names                 # Fix names in current directory"
echo "  fix_all_names /path/to/dir    # Fix names in specified directory"
echo ""
echo "The command will rename files from:"
echo "  LASTNAME.FIRSTNAME.MM.DD.YYYY_TH.pdf"
echo "To:"
echo "  LASTNAME_FIRSTNAME_MMDDYYYY_TH.pdf"
echo "========================================="