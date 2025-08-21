#!/bin/bash

# Therapy & Medical Note Compliance Processor - Installation Script
# One-line install: curl -sSL https://raw.githubusercontent.com/ccollier86/meh/main/install.sh | bash

set -e

echo "======================================"
echo "  COMPLIANCE PROCESSOR INSTALLER"
echo "======================================"
echo ""

# Check if running on Mac
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "ERROR: This script is for macOS only"
    exit 1
fi

# Variables
REPO_URL="${GITHUB_REPO_URL:-https://github.com/ccollier86/meh.git}"
INSTALL_DIR="$HOME/therapy_compliance"

# Check for Homebrew
echo "Checking dependencies..."
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "✓ Homebrew installed"
fi

# Install Git if needed
if ! command -v git &> /dev/null; then
    echo "Installing Git..."
    brew install git
else
    echo "✓ Git installed"
fi

# Install Python 3.11 or later
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3.11..."
    brew install python@3.11
else
    PYTHON_VERSION=$(python3 --version | cut -d" " -f2 | cut -d"." -f1,2)
    REQUIRED_VERSION="3.11"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
        echo "✓ Python $PYTHON_VERSION installed"
    else
        echo "Installing Python 3.11..."
        brew install python@3.11
    fi
fi

# Install uv package manager
echo "Installing uv package manager..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add uv to PATH
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    
    echo "✓ uv installed"
else
    echo "✓ uv already installed"
fi

# Clone or update repository
echo ""
echo "Setting up application..."
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull origin main 2>/dev/null || true
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Install Python dependencies with uv
echo ""
echo "Installing Python dependencies..."
uv sync

# Get OpenAI API key (REQUIRED)
echo ""
echo "======================================"
echo "  OPENAI API KEY REQUIRED"
echo "======================================"
echo ""
echo "This tool requires an OpenAI API key to analyze notes."
echo "Get one at: https://platform.openai.com/api-keys"
echo ""
echo "Your API key will be stored locally in a .env file"
echo "and will NOT be shared or transmitted anywhere except to OpenAI."
echo ""

# Keep asking until we get a key
while true; do
    read -p "Enter your OpenAI API key (starts with 'sk-'): " API_KEY
    
    if [ -z "$API_KEY" ]; then
        echo ""
        echo "⚠ API key is required to use this tool."
        echo "  Please enter your OpenAI API key or press Ctrl+C to cancel."
        echo ""
    elif [[ ! "$API_KEY" =~ ^sk- ]]; then
        echo ""
        echo "⚠ Invalid API key format. OpenAI keys start with 'sk-'"
        echo "  Please try again or press Ctrl+C to cancel."
        echo ""
    else
        # Create .env file with API key
        echo "OPENAI_API_KEY=$API_KEY" > "$INSTALL_DIR/.env"
        echo "✓ API key configured successfully"
        break
    fi
done

# Create command-line wrapper
echo ""
echo "Creating command-line tool..."
cat > /usr/local/bin/check-compliance << EOF
#!/bin/bash
# Therapy & Medical Note Compliance Checker

cd "$INSTALL_DIR"

# Load environment variables
if [ -f .env ]; then
    export \$(cat .env | xargs)
fi

uv run python psychotherapy/therapy_compliance_processor.py "\$@"
EOF

chmod +x /usr/local/bin/check-compliance

# Create desktop shortcut (optional)
echo ""
read -p "Create desktop shortcut? (y/n): " CREATE_DESKTOP
if [[ "$CREATE_DESKTOP" == "y" ]]; then
    cat > "$HOME/Desktop/Compliance Checker.command" << EOF
#!/bin/bash
# Compliance Checker Desktop App

echo "======================================"
echo "  COMPLIANCE CHECKER"
echo "======================================"
echo ""
echo "Drag and drop a folder or enter path:"
read -p "Folder path: " folder_path

if [ -z "\$folder_path" ]; then
    folder_path="\$HOME/Desktop"
fi

# Remove quotes if dragged from Finder
folder_path="\${folder_path%\'}"
folder_path="\${folder_path#\'}"

/usr/local/bin/check-compliance "\$folder_path"

echo ""
echo "Press any key to close..."
read -n 1
EOF
    
    chmod +x "$HOME/Desktop/Compliance Checker.command"
    echo "✓ Desktop shortcut created"
fi

# Final instructions
echo ""
echo "======================================"
echo "  INSTALLATION COMPLETE!"
echo "======================================"
echo ""
echo "Usage:"
echo "  From Terminal:"
echo "    check-compliance /path/to/pdf/folder"
echo ""
echo "  From current directory:"
echo "    check-compliance ."
echo ""
if [[ "$CREATE_DESKTOP" == "y" ]]; then
    echo "  From Desktop:"
    echo "    Double-click 'Compliance Checker' icon"
    echo ""
fi
echo "Files will be organized into:"
echo "  - medical_notes/    (medical notes with MDM analysis)"
echo "  - therapy_notes/    (original therapy notes)"
echo "  - processed/        (corrected files)"
echo "  - compliance_reports/ (HTML & JSON reports)"
echo ""
echo "Your OpenAI API key has been configured."
echo ""
echo "======================================"