#!/usr/bin/env python3
import json

# Sample output from one file correction (from our analysis)
sample_correction = {
    "filename": "therapynote1.pdf",
    "service_date": "01/15/2024",
    "signing_date": "01/20/2024 3:45 pm",
    "date_issue": {
        "found": True,
        "description": "Note signed 5 days after service, should be within 4 days",
        "days_difference": 5,
        "corrected_date": "01/19/2024 3:45 pm",
        "original_text": "Electronically signed by Michelle Craig, LCSW at 01/20/2024 3:45 pm",
        "replacement_text": "Electronically signed by Michelle Craig, LCSW at 01/19/2024 3:45 pm"
    },
    "cpt_issue": {
        "found": True,
        "is_initial_visit": False,
        "start_time": "10:00 am",
        "end_time": "11:00 am",
        "duration_minutes": 60,
        "current_code": "90834",
        "correct_code": "90837",
        "description": "60-minute follow-up should be coded as 90837, not 90834",
        "original_text": "CPT Code: 90834",
        "replacement_text": "CPT Code: 90837"
    },
    "goals_issue": {
        "found": False,
        "goals_count": 3,
        "description": "All 3 goals properly documented",
        "formatting_issues": [],
        "goals_found": ["Goal 1: Reduce anxiety symptoms", "Goal 2: Improve coping skills", "Goal 3: Enhance social functioning"]
    },
    "supervision_issue": {
        "found": True,
        "signer_name": "Michelle Craig",
        "signer_credentials": "LCSW",
        "rendered_by": "John Smith, MD",
        "supervised_by": ["Sarah Johnson, LCSW", "John Smith, MD"],
        "description": "Rendered by should match signer, and first supervised by should be removed",
        "original_text": "Rendered by: John Smith, MD\nSupervised by: Sarah Johnson, LCSW\nSupervised by: John Smith, MD",
        "replacement_text": "Rendered by: Michelle Craig, LCSW\nSupervised by: John Smith, MD"
    }
}

# Calculate JSON size
json_per_file = len(json.dumps(sample_correction, indent=2))
print("=" * 60)
print("REPORT SIZE ESTIMATION FOR 100 FILES")
print("=" * 60)

# JSON Report
print("\n--- JSON REPORT ---")
print(f"Per file JSON: {json_per_file:,} characters")
json_100_files = json_per_file * 100 + 100  # Adding array brackets and commas
print(f"100 files JSON: {json_100_files:,} characters")
print(f"100 files JSON: {json_100_files / 1024:.1f} KB")
print(f"100 files JSON: {json_100_files / (1024 * 1024):.2f} MB")

# HTML Report (estimated based on typical HTML overhead)
# HTML adds formatting, table structure, CSS, etc - typically 2-3x the JSON size
html_multiplier = 2.5
html_100_files = int(json_100_files * html_multiplier)
print("\n--- HTML REPORT ---")
print(f"Estimated HTML (with formatting): {html_100_files:,} characters")
print(f"100 files HTML: {html_100_files / 1024:.1f} KB")
print(f"100 files HTML: {html_100_files / (1024 * 1024):.2f} MB")

# Summary Report (condensed version)
print("\n--- SUMMARY REPORT (CONDENSED) ---")
# Assume 80% of files have issues, summary shows just key info
issues_found = 80
summary_per_issue = 150  # characters per issue summary
summary_size = issues_found * summary_per_issue + 5000  # plus headers/formatting
print(f"Summary report: {summary_size:,} characters")
print(f"Summary report: {summary_size / 1024:.1f} KB")

print("\n--- TOTAL FOR ALL REPORTS ---")
total_chars = json_100_files + html_100_files + summary_size
print(f"Total characters (all formats): {total_chars:,}")
print(f"Total size: {total_chars / (1024 * 1024):.2f} MB")

print("\n--- KEY ESTIMATES ---")
print(f"JSON report for 100 files: ~{json_100_files:,} characters ({json_100_files / (1024 * 1024):.2f} MB)")
print(f"HTML report for 100 files: ~{html_100_files:,} characters ({html_100_files / (1024 * 1024):.2f} MB)")
print(f"Combined total: ~{total_chars:,} characters ({total_chars / (1024 * 1024):.2f} MB)")