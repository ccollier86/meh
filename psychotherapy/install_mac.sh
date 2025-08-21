#!/bin/bash

# Therapy Compliance Processor - Mac Installation Script
# Requires macOS 10.15 or later

set -e

echo "======================================"
echo "🏥 Therapy Compliance Processor"
echo "   Mac Installation Script"
echo "======================================"
echo ""

# Check if running on Mac
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: This script is for macOS only"
    exit 1
fi

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "✅ Homebrew is installed"
fi

# Install Python 3.11 or later
echo ""
echo "🐍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3.11..."
    brew install python@3.11
else
    PYTHON_VERSION=$(python3 --version | cut -d" " -f2 | cut -d"." -f1,2)
    REQUIRED_VERSION="3.11"
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
        echo "✅ Python $PYTHON_VERSION is installed"
    else
        echo "⚠️  Python $PYTHON_VERSION found, installing Python 3.11..."
        brew install python@3.11
    fi
fi

# Install uv (fast Python package manager)
echo ""
echo "📦 Installing uv package manager..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add uv to PATH
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
    export PATH="$HOME/.cargo/bin:$PATH"
    
    echo "✅ uv installed successfully"
else
    echo "✅ uv is already installed"
fi

# Create project directory
echo ""
echo "📁 Setting up project directory..."
PROJECT_DIR="$HOME/therapy_compliance"
mkdir -p "$PROJECT_DIR"

# Copy files
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cp -r "$SCRIPT_DIR"/* "$PROJECT_DIR/"

# Navigate to project directory
cd "$PROJECT_DIR"

# Initialize Python project with uv
echo ""
echo "🔧 Setting up Python environment..."
uv venv
source .venv/bin/activate

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[project]
name = "therapy-compliance-processor"
version = "1.0.0"
description = "Automated therapy note compliance checking and correction"
requires-python = ">=3.11"
dependencies = [
    "pdfplumber>=0.10.0",
    "pymupdf>=1.24.0",
    "openai>=1.0.0",
    "python-dateutil>=2.8.2",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# Install dependencies
echo ""
echo "📚 Installing dependencies..."
uv pip install pdfplumber pymupdf openai python-dateutil

# Create command-line wrapper
echo ""
echo "🔗 Creating command-line tool..."
cat > /usr/local/bin/check_therapy_compliance << 'EOF'
#!/bin/bash
# Therapy Compliance Checker

PROJECT_DIR="$HOME/therapy_compliance"
cd "$PROJECT_DIR"
source .venv/bin/activate

# If no argument provided, use current directory
if [ $# -eq 0 ]; then
    python therapy_compliance_processor.py "$(pwd)"
else
    python therapy_compliance_processor.py "$1"
fi
EOF

chmod +x /usr/local/bin/check_therapy_compliance

# Create desktop app (optional)
echo ""
echo "🖥️  Creating desktop app..."
cat > "$HOME/Desktop/Therapy Compliance Checker.command" << 'EOF'
#!/bin/bash
# Therapy Compliance Checker Desktop App

echo "======================================"
echo "🏥 Therapy Compliance Checker"
echo "======================================"
echo ""
echo "Drag and drop a folder with PDF files or press Enter to use Desktop:"
read -p "Folder path: " folder_path

if [ -z "$folder_path" ]; then
    folder_path="$HOME/Desktop"
fi

# Remove quotes if dragged from Finder
folder_path="${folder_path%\'}"
folder_path="${folder_path#\'}"

/usr/local/bin/check_therapy_compliance "$folder_path"

echo ""
echo "Press any key to close..."
read -n 1
EOF

chmod +x "$HOME/Desktop/Therapy Compliance Checker.command"

# Setup API key
echo ""
echo "🔑 Setting up OpenAI API key..."
echo ""
echo "Please enter your OpenAI API key:"
echo "(Get one at https://platform.openai.com/api-keys)"
read -s API_KEY

# Update the API key in the script
sed -i '' "s/sk-proj-[A-Za-z0-9]*/$API_KEY/g" "$PROJECT_DIR/therapy_compliance_processor.py"

echo ""
echo "======================================"
echo "✅ Installation Complete!"
echo "======================================"
echo ""
echo "Usage:"
echo "  From Terminal:"
echo "    check_therapy_compliance ~/path/to/pdfs"
echo ""
echo "  From Desktop:"
echo "    Double-click 'Therapy Compliance Checker' on your Desktop"
echo ""
echo "The tool will:"
echo "  • Detect therapy vs medical notes"
echo "  • Check compliance issues"
echo "  • Auto-correct date and CPT code issues"
echo "  • Generate beautiful HTML reports"
echo "  • Organize files into folders"
echo ""
echo "Files are organized into:"
echo "  • medical_notes/ - Medical notes (skipped)"
echo "  • therapy_notes/ - Original therapy notes"
echo "  • processed/ - Corrected files"
echo "  • compliance_reports/ - HTML reports"
echo ""
echo "Enjoy! 🎉"