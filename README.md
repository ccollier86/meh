# Therapy & Medical Note Compliance Processor

Professional tool for automated psychotherapy note compliance checking and medical note MDM analysis.

## Quick Install (macOS)

```bash
curl -sSL https://raw.githubusercontent.com/ccollier86/meh/main/install.sh | bash
```

## Features

### Therapy Notes
- **Date Compliance**: Ensures signing within 4-6 days of service
- **CPT Code Accuracy**: Verifies code matches session duration
- **Treatment Goals**: Ensures proper formatting and presence
- **Supervision Hierarchy**: Validates rendered by and supervision structure
- **Automatic Corrections**: Fixes date, CPT, and supervision issues

### Medical Notes
- **MDM Analysis**: Evaluates for moderate medical decision making
- **Personalized Recommendations**: Suggests improvements for each section
- **Assessment & Plan Enhancement**: Provides improved documentation suggestions
- **Detailed Reporting**: Shows which MDM criteria are met/missing

## Manual Installation

### Prerequisites
- macOS 10.15 or later
- Python 3.11+
- OpenAI API key

### Steps

1. Clone the repository:
```bash
git clone https://github.com/ccollier86/meh.git
cd meh
```

2. Install uv package manager:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install dependencies:
```bash
uv sync
```

4. Add your OpenAI API key to `psychotherapy/therapy_compliance_processor.py`

5. Run the processor:
```bash
uv run python psychotherapy/therapy_compliance_processor.py /path/to/pdfs
```

## Usage

### Command Line
```bash
check-compliance /path/to/pdf/folder
```

### From Current Directory
```bash
check-compliance .
```

## Output Structure

```
your_folder/
├── medical_notes/       # Medical notes with MDM analysis
├── therapy_notes/       # Original therapy notes
├── processed/           # Corrected therapy notes
└── compliance_reports/  # HTML and JSON reports
    ├── therapy_compliance_YYYYMMDD_HHMMSS.html
    └── therapy_compliance_YYYYMMDD_HHMMSS.json
```

## Report Features

- **Professional Design**: Clean, minimalist interface
- **Tabbed Layout**: Separate tabs for therapy and medical notes
- **Table Format**: Easy-to-scan data presentation
- **MDM Recommendations**: Detailed suggestions for medical notes
- **Direct PDF Links**: Click to open original or corrected files

## Compliance Rules

### Therapy Notes

#### CPT Codes
- **90832**: 16-37 minutes
- **90834**: 38-52 minutes
- **90837**: 53+ minutes
- **90791**: Initial evaluation only

#### Date Compliance
- Electronic signatures must be within 4-6 days of service
- Automatically corrects to 5 days if outside range

#### Treatment Goals
- Minimum 2 goals required
- Each must include: Goal, Objective, Tx Modality, Progress

### Medical Notes

#### Moderate MDM Criteria (2 of 3 required)
1. **Problem Complexity**: Chronic illness with progression, multiple stable conditions
2. **Data Complexity**: Review of external notes, test ordering, interpretation
3. **Risk Level**: Prescription management, surgical decisions

## API Configuration

Get your OpenAI API key from: https://platform.openai.com/api-keys

Add it during installation or manually edit the processor file.

## Privacy & Security

- All processing done locally on your Mac
- Only text content sent to OpenAI for analysis
- No patient data stored by OpenAI
- Original files never modified (copies only)

## Troubleshooting

### "Command not found"
```bash
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### "API key invalid"
Update your API key in the processor file

### PDF Processing Issues
- Ensure PDFs contain extractable text (not scanned images)
- Check PDF file permissions

## Support

For issues or questions, please open a GitHub issue.

## License

Private repository - Internal use only

---

Built for mental health professionals to ensure quality documentation and compliance.