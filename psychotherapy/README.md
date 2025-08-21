# 🏥 Therapy Compliance Processor

Professional tool for automated psychotherapy note compliance checking and correction.

## Features

✅ **Smart Note Detection**
- Automatically identifies therapy notes vs medical notes
- Recognizes LCSW, LPCC, LPCA, LPC, LCADC, LMFT, LMHC credentials
- Skips medical notes to focus only on therapy documentation

✅ **Compliance Checking**
- **Date Compliance**: Ensures signing within 4-6 days of service
- **CPT Code Accuracy**: Verifies code matches session duration
  - 90832 (16-37 minutes)
  - 90834 (38-52 minutes)  
  - 90837 (53 minutes or more)
- **Treatment Goals**: Ensures 2 properly formatted goals are present

✅ **Automatic Corrections**
- Fixes incorrect signing dates
- Corrects CPT codes based on actual session time
- Generates missing treatment goals using AI

✅ **Smart Organization**
- Automatically sorts files into organized folders
- Keeps originals separate from corrected versions
- Medical notes separated from therapy notes

✅ **Beautiful Reporting**
- Modern, professional HTML reports
- Clickable links to view files
- Clear statistics and issue tracking

## Installation (Mac)

### Quick Install

1. Download the `install_mac.sh` script
2. Open Terminal
3. Run:
```bash
chmod +x install_mac.sh
./install_mac.sh
```

The installer will:
- Install Python 3.11+ if needed
- Install uv package manager
- Set up all dependencies
- Create command-line tool
- Create desktop app
- Configure your OpenAI API key

### Manual Installation

If you prefer to install manually:

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone or download this repository
cd therapy_compliance

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install pdfplumber pymupdf openai python-dateutil

# Add your OpenAI API key to the script
# Edit therapy_compliance_processor.py and replace the API key
```

## Usage

### From Terminal

```bash
check_therapy_compliance ~/Documents/therapy_notes
```

Or navigate to the folder and run:
```bash
check_therapy_compliance .
```

### From Desktop

Double-click the "Therapy Compliance Checker" icon on your Desktop and drag a folder onto it.

### What Happens

1. **Scanning**: The tool scans all PDF files in the folder
2. **Detection**: Identifies therapy notes vs medical notes
3. **Analysis**: Checks each therapy note for compliance issues
4. **Correction**: Automatically fixes date and CPT code issues
5. **Organization**: Moves files into organized folders:
   - `medical_notes/` - Medical notes (skipped)
   - `therapy_notes/` - Original therapy notes
   - `processed/` - Corrected files
   - `compliance_reports/` - HTML reports
6. **Reporting**: Generates a beautiful HTML report with all findings

## File Organization

After processing, your folder will be organized like this:

```
your_folder/
├── medical_notes/          # Medical notes (not processed)
├── therapy_notes/          # Original therapy notes
├── processed/              # Corrected therapy notes
│   └── *_CORRECTED.pdf
└── compliance_reports/     # HTML and JSON reports
    ├── therapy_compliance_YYYYMMDD_HHMMSS.html
    └── therapy_compliance_YYYYMMDD_HHMMSS.json
```

## Requirements

- macOS 10.15 or later
- Python 3.11 or later
- OpenAI API key (for AI-powered corrections)
- Internet connection (for AI processing)

## API Key

You'll need an OpenAI API key:
1. Go to https://platform.openai.com/api-keys
2. Create a new key
3. Add it during installation or edit the script

## Compliance Rules

### Date Compliance
- Electronic signatures must be within 4-6 days of service date
- Automatically corrects to 5 days if outside range

### CPT Code Rules
- **90832**: 16-37 minutes
- **90834**: 38-52 minutes
- **90837**: 53 minutes or more
- **90791**: Initial psychiatric evaluation
- **90847**: Family therapy with patient
- **90853**: Group therapy

### Treatment Goals
- Minimum 2 goals required
- Each goal must include:
  - Goal statement (in patient's voice)
  - Objective (measurable, with frequency)
  - Tx Modality (CBT, DBT, etc.)
  - Progress notes

## Troubleshooting

### "Command not found"
Add to your PATH:
```bash
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### "API key invalid"
Edit the script and update your API key:
```bash
nano ~/therapy_compliance/therapy_compliance_processor.py
# Find and replace the API key
```

### "Permission denied"
Make the script executable:
```bash
chmod +x /usr/local/bin/check_therapy_compliance
```

## Privacy & Security

- All processing is done locally on your Mac
- Only the text content is sent to OpenAI for analysis
- No patient data is stored by OpenAI
- Original files are never modified, only copies

## Support

For issues or questions:
- Check the JSON report for detailed error messages
- Ensure all PDFs are readable (not scanned images)
- Verify your OpenAI API key is active

## License

This tool is for internal use only. Do not distribute.

---

Made with ❤️ for mental health professionals