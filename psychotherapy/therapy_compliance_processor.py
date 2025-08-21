#!/usr/bin/env python3
"""
Psychotherapy Note Compliance Processor
Professional tool for ensuring therapy note compliance
"""

import os
import sys
import json
import glob
import shutil
from datetime import datetime, timedelta
import pdfplumber
import fitz  # PyMuPDF
from openai import OpenAI
from typing import Dict, List, Any, Tuple
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    print("ERROR: OpenAI API key not found!")
    print("Please set OPENAI_API_KEY environment variable or create a .env file")
    print("Example: echo 'OPENAI_API_KEY=your_key_here' > .env")
    sys.exit(1)

client = OpenAI(api_key=api_key)

class TherapyNoteProcessor:
    def __init__(self):
        self.client = client
        self.results = []
        self.therapy_credentials = ['LCSW', 'LPCC', 'LPCA', 'LPC', 'LCADC', 'LCADCA', 'LMFT', 'LMHC']
        
    def is_therapy_note(self, pdf_path: str) -> Tuple[bool, str]:
        """Determine if this is a therapy note vs medical note"""
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Check first 2 pages for indicators
                text_to_check = ""
                for i in range(min(2, len(pdf.pages))):
                    text_to_check += pdf.pages[i].extract_text() + "\n"
                
                # Check for therapy credentials in signature area
                for credential in self.therapy_credentials:
                    # Look for credentials near "signed by" area
                    if "signed by" in text_to_check.lower():
                        # Find the lines around "signed by"
                        lines = text_to_check.split('\n')
                        for i, line in enumerate(lines):
                            if "signed by" in line.lower():
                                # Check this line and next 2 lines for credentials
                                check_area = ' '.join(lines[i:min(i+3, len(lines))])
                                if credential in check_area:
                                    # Also check for CPT codes
                                    if any(code in text_to_check for code in ['90791', '90832', '90834', '90837', '90847', '90853']):
                                        return True, credential
                                    # Check for START TIME/END TIME pattern
                                    if "START TIME:" in text_to_check and "END TIME:" in text_to_check:
                                        return True, credential
                
                # Additional checks for therapy-specific content
                therapy_indicators = [
                    "Therapy Type:",
                    "Tx Modality:",
                    "Goal #",
                    "psychotherapy",
                    "mental status exam",
                    "treatment goals"
                ]
                
                indicator_count = sum(1 for indicator in therapy_indicators if indicator.lower() in text_to_check.lower())
                if indicator_count >= 3:
                    # Find credential if present
                    for credential in self.therapy_credentials:
                        if credential in text_to_check:
                            return True, credential
                    return True, "Unknown"
                
                return False, "Medical"
                
        except Exception as e:
            print(f"Error checking note type: {e}")
            return False, "Error"
    
    def setup_folders(self, base_path: str):
        """Create organized folder structure"""
        
        folders = {
            'medical': os.path.join(base_path, 'medical_notes'),
            'therapy': os.path.join(base_path, 'therapy_notes'),
            'processed': os.path.join(base_path, 'processed'),
            'reports': os.path.join(base_path, 'compliance_reports')
        }
        
        for folder in folders.values():
            os.makedirs(folder, exist_ok=True)
            
        return folders
    
    def analyze_medical_note_mdm(self, pdf_text: str, filename: str) -> Dict[str, Any]:
        """Analyze medical note for moderate medical decision making (MDM)"""
        
        prompt = f"""
        Analyze this medical note to determine if it meets MODERATE Medical Decision Making (MDM) criteria.
        
        Read the ENTIRE note carefully, paying special attention to:
        - HPI (History of Present Illness)
        - Chief Complaint
        - Assessment/Plan section (A section)
        - Risk Assessment
        - Review of Systems
        - Physical Exam findings
        
        MODERATE MDM requires meeting 2 of these 3 elements:
        
        1. NUMBER & COMPLEXITY OF PROBLEMS:
           - 1 or more chronic illnesses with progression/side effects
           - 2 or more stable chronic illnesses
           - 1 undiagnosed new problem with uncertain prognosis
           - 1 acute illness with systemic symptoms
           - 1 acute complicated injury
        
        2. AMOUNT/COMPLEXITY OF DATA:
           - Review of prior external notes
           - Ordering of tests (labs, imaging)
           - Assessment requiring independent historian
           - Independent interpretation of tests
           - Discussion of management with external provider
        
        3. RISK OF COMPLICATIONS:
           - Prescription drug management
           - Decision regarding minor surgery with risk factors
           - Decision regarding elective major surgery
           - Diagnosis/treatment significantly limited by social determinants
        
        Generate an improved "OVERALL PROGRESS" section that:
        - Synthesizes the HPI, chief complaint, assessment, and plan
        - Clearly demonstrates moderate MDM complexity
        - Shows clinical reasoning and medical decision making
        - Incorporates risk assessment findings
        - Is comprehensive yet concise (4-6 sentences)
        
        Also suggest an improved Plan section that:
        - Builds on the existing plan content
        - Better demonstrates moderate MDM
        - Shows clear clinical reasoning
        - Includes appropriate follow-up and monitoring
        
        Return JSON:
        {{
            "filename": "{filename}",
            "meets_moderate_mdm": true/false,
            "mdm_analysis": {{
                "problems_complexity": "description of problems addressed",
                "data_reviewed": "description of data/tests reviewed or ordered",
                "risk_level": "description of risk factors and management",
                "criteria_met": ["list of which MDM criteria are met"]
            }},
            "current_assessment": "the current A section text",
            "suggested_overall_progress": "OVERALL PROGRESS: [comprehensive 4-6 sentence synthesis meeting moderate MDM]",
            "current_plan": "the current plan text",
            "suggested_improved_plan": "improved plan section text",
            "key_findings": ["list of important clinical findings from the note"],
            "recommendations": ["specific suggestions for improving MDM documentation"]
        }}
        
        Document:
        {pdf_text}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert medical auditor specializing in evaluation and management (E&M) coding and medical decision making complexity. Analyze thoroughly and return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={ "type": "json_object" }
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            content = response.choices[0].message.content
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Could not parse AI response", "filename": filename}
    
    def analyze_with_ai(self, pdf_text: str, filename: str) -> Dict[str, Any]:
        """Comprehensive AI analysis of therapy note"""
        
        prompt = f"""
        Analyze this psychotherapy note for FOUR compliance issues:
        
        1. DATE COMPLIANCE:
           - Service Date (DATE field in ENCOUNTER column)
           - Signing Date ("Electronically signed by... at [date time]")
           - Check if signing is within 4-6 days after service
        
        2. CPT CODE COMPLIANCE:
           - LOOK RIGHT ABOVE THE START TIME/END TIME - it will say either "INITIAL VISIT" or "FOLLOW-UP"
           - If it says "INITIAL VISIT" AND duration is 53+ minutes: code should be 90791
           - If it says "FOLLOW-UP": 
             * 90791 is WRONG - NEVER use 90791 for follow-ups!
             * Calculate duration from START TIME to END TIME
             * 16-37 minutes = 90832
             * 38-52 minutes = 90834  
             * 53+ minutes = 90837
           - CRITICAL: A 60-minute FOLLOW-UP should be 90837, NOT 90791!
        
        3. TREATMENT GOALS:
           - Look for Goal sections (may be labeled "Goal #1", "Goal 1", "Goal", etc.)
           - Count how many distinct goals are documented
           - Each goal should have: Goal statement, Objective, Tx Modality, Progress
           - Note if goals are missing numbers or have inconsistent formatting
        
        4. SUPERVISION HIERARCHY:
           - Find who signed the note ("Electronically signed by [Name][Credentials]")
           - Look for "Rendered by:" section (usually above Plan or near Diagnoses)
           - IMPORTANT: "Rendered by:" MUST match the person who signed the note
           - If they don't match, this is an ERROR that needs fixing
           - The correct "Rendered by:" should be the signer's name and credentials
           - For "Supervised by:" lines:
             * If there are multiple "Supervised by:" lines, remove the first one (non-MD)
             * Keep ONLY "Supervised by: [Name], MD" 
           - Example: If signed by "Michelle Craig, LCSW" then "Rendered by:" should be "Michelle Craig, LCSW"
        
        Return JSON:
        {{
            "filename": "{filename}",
            "service_date": "MM/DD/YYYY",
            "signing_date": "MM/DD/YYYY HH:MM am/pm",
            
            "date_issue": {{
                "found": true/false,
                "description": "explanation",
                "days_difference": number,
                "corrected_date": "MM/DD/YYYY HH:MM am/pm",
                "original_text": "text to find",
                "replacement_text": "corrected text"
            }},
            
            "cpt_issue": {{
                "found": true/false,  # Set to true ONLY if current_code != correct_code
                "is_initial_visit": true/false,
                "start_time": "HH:MM am/pm",
                "end_time": "HH:MM am/pm",
                "duration_minutes": number,
                "current_code": "90XXX",
                "correct_code": "90XXX",
                "description": "explanation",
                "original_text": "CPT Code: 90XXX",
                "replacement_text": "CPT Code: 90XXX"
            }},
            
            "goals_issue": {{
                "found": true/false,
                "goals_count": number,
                "description": "explanation",
                "formatting_issues": ["list of issues"],
                "goals_found": ["Goal 1 text", "Goal 2 text"]
            }},
            
            "supervision_issue": {{
                "found": true/false,
                "signer_name": "Name who signed",
                "signer_credentials": "credentials",
                "rendered_by": "current rendered by text",
                "supervised_by": ["list of supervisors found"],
                "description": "explanation of issue",
                "original_text": "full original supervision block",
                "replacement_text": "corrected supervision block"
            }}
        }}
        
        Document:
        {pdf_text}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",  # Using GPT-4 for accuracy on therapy notes
            messages=[
                {"role": "system", "content": "You are a medical compliance auditor. Analyze thoroughly and return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            content = response.choices[0].message.content
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Could not parse AI response", "filename": filename}
    
    def fix_pdf(self, pdf_path: str, analysis: Dict[str, Any], note_text: str = "") -> bool:
        """Fix compliance issues in the PDF including supervision hierarchy"""
        
        if not any([
            analysis.get('date_issue', {}).get('found'),
            analysis.get('cpt_issue', {}).get('found'),
            analysis.get('goals_issue', {}).get('found'),
            analysis.get('supervision_issue', {}).get('found')
        ]):
            return False
        
        try:
            doc = fitz.open(pdf_path)
            fixed = False
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Fix date if needed
                if analysis.get('date_issue', {}).get('found'):
                    date_info = analysis['date_issue']
                    original_date = date_info.get('original_text', '')
                    
                    # Extract just the date/time
                    import re
                    date_pattern = r'\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s+[ap]m'
                    
                    original_match = re.search(date_pattern, original_date)
                    replacement_match = re.search(date_pattern, date_info.get('replacement_text', ''))
                    
                    if original_match and replacement_match:
                        old_date = original_match.group()
                        new_date = replacement_match.group()
                        
                        instances = page.search_for(old_date)
                        
                        if instances:
                            rect = instances[0]
                            expanded = fitz.Rect(rect.x0-2, rect.y0-2, rect.x1+2, rect.y1+2)
                            page.add_redact_annot(expanded)
                            page.apply_redactions()
                            
                            page.insert_text(
                                point=(rect.x0, rect.y0 + rect.height * 0.8),
                                text=new_date,
                                fontsize=9,
                                fontname="helv",
                                color=(0, 0, 0)
                            )
                            fixed = True
                            print(f"      Fixed date: {old_date} -> {new_date}")
                
                # Fix CPT code if needed
                if analysis.get('cpt_issue', {}).get('found'):
                    cpt_info = analysis['cpt_issue']
                    current_code = cpt_info.get('current_code', '')
                    correct_code = cpt_info.get('correct_code', '')
                    
                    # Only fix if codes are actually different
                    if current_code and correct_code and current_code != correct_code:
                        instances = page.search_for(current_code)
                        
                        if instances:
                            rect = instances[0]
                            expanded = fitz.Rect(rect.x0-5, rect.y0-2, rect.x1+10, rect.y1+2)
                            page.add_redact_annot(expanded)
                            page.apply_redactions()
                            
                            page.insert_text(
                                point=(rect.x0, rect.y0 + rect.height * 0.8),
                                text=correct_code,
                                fontsize=8.82,
                                fontname="helv",
                                color=(0, 0, 0)
                            )
                            fixed = True
                            print(f"      Fixed CPT: {current_code} -> {correct_code}")
                
                # Fix supervision hierarchy if needed
                if analysis.get('supervision_issue', {}).get('found'):
                    supervision_info = analysis['supervision_issue']
                    signer_name = supervision_info.get('signer_name', '')
                    signer_credentials = supervision_info.get('signer_credentials', '')
                    
                    if signer_name and signer_credentials:
                        # Look for "Rendered by:" line
                        rendered_instances = page.search_for("Rendered by:")
                        
                        if rendered_instances:
                            # Find the first two supervision lines to redact
                            rect = rendered_instances[0]
                            
                            # Redact ONLY "Rendered by:" line and first "Supervised by:" line (2 lines)
                            # Leave the second "Supervised by: MD" line untouched
                            expanded = fitz.Rect(
                                rect.x0 - 5,
                                rect.y0 - 2,
                                rect.x1 + 250,  # Extend right to catch full names
                                rect.y0 + 25    # Extend down to cover ONLY 2 lines
                            )
                            page.add_redact_annot(expanded)
                            page.apply_redactions()
                            
                            # Insert entire "Rendered by:" line in bold italic
                            # Don't add ANY "Supervised by" - the MD one is already there!
                            page.insert_text(
                                point=(rect.x0, rect.y0 + rect.height * 0.8),
                                text=f"Rendered by: {signer_name}, {signer_credentials}",
                                fontsize=8.82,
                                fontname="Helvetica-BoldOblique",  # Bold + Italic
                                color=(0, 0, 0)
                            )
                            
                            # That's it! The original "Supervised by: Neil Jariwala, MD" stays untouched
                            # The original "Diagnoses attached to this encounter:" stays untouched
                            
                            fixed = True
                            print(f"      Fixed supervision: Rendered by: {signer_name}, {signer_credentials}")
            
            if fixed:
                # Save the document
                output_path = pdf_path.replace('.pdf', '_TEMP_FIXED.pdf')
                doc.save(output_path)
                doc.close()
                
                # Replace original with fixed version
                import os
                os.remove(pdf_path)
                os.rename(output_path, pdf_path)
                
                return True
            
            doc.close()
            return False
            
        except Exception as e:
            print(f"      ERROR fixing PDF: {e}")
            return False
    
    def generate_modern_report(self, results: List[Dict[str, Any]], folders: Dict[str, str]) -> str:
        """Generate professional minimalist HTML report with tabs"""
        
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        total_files = len(results)
        
        # Separate therapy and medical notes
        therapy_results = [r for r in results if not r.get('is_medical_note')]
        medical_results = [r for r in results if r.get('is_medical_note')]
        
        # Calculate statistics
        therapy_notes = len(therapy_results)
        medical_notes = len(medical_results)
        medical_below_mdm = sum(1 for r in medical_results if not r.get('meets_moderate_mdm'))
        files_with_issues = sum(1 for r in therapy_results if (
            r.get('date_issue', {}).get('found') or 
            r.get('cpt_issue', {}).get('found') or
            r.get('goals_issue', {}).get('found') or
            r.get('supervision_issue', {}).get('found')))
        files_corrected = sum(1 for r in results if r.get('corrections_made'))
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compliance Report - {timestamp}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f8f9fa;
            color: #212529;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 24px;
            font-weight: 600;
            color: #212529;
            margin-bottom: 4px;
        }}
        
        .header .subtitle {{
            color: #6c757d;
            font-size: 14px;
        }}
        
        .stats-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        
        .stat-box {{
            background: white;
            padding: 16px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .stat-value {{
            font-size: 28px;
            font-weight: 600;
            color: #212529;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .tabs {{
            display: flex;
            gap: 4px;
            margin-bottom: 24px;
            background: white;
            padding: 4px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .tab {{
            flex: 1;
            padding: 12px;
            background: transparent;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            color: #6c757d;
            transition: all 0.2s;
        }}
        
        .tab:hover {{
            background: #f8f9fa;
        }}
        
        .tab.active {{
            background: #007bff;
            color: white;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .content-section {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            text-align: left;
            padding: 12px;
            font-size: 12px;
            font-weight: 600;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #dee2e6;
        }}
        
        td {{
            padding: 12px;
            font-size: 14px;
            border-bottom: 1px solid #f1f3f5;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .file-link {{
            color: #007bff;
            text-decoration: none;
            font-weight: 500;
        }}
        
        .file-link:hover {{
            text-decoration: underline;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-right: 4px;
        }}
        
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .badge-info {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        
        .badge-primary {{
            background: #cce5ff;
            color: #004085;
        }}
        
        .mdm-section {{
            background: #f8f9fa;
            border-radius: 4px;
            padding: 16px;
            margin-top: 12px;
        }}
        
        .mdm-section h4 {{
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #495057;
        }}
        
        .mdm-section p {{
            font-size: 13px;
            color: #6c757d;
            margin-bottom: 8px;
        }}
        
        .recommendation-box {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 12px;
            margin-top: 8px;
            border-radius: 4px;
        }}
        
        .recommendation-box h5 {{
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 4px;
            color: #856404;
        }}
        
        .recommendation-box p {{
            font-size: 12px;
            color: #856404;
            margin-bottom: 4px;
        }}
        
        .footer {{
            text-align: center;
            padding: 24px;
            color: #6c757d;
            font-size: 12px;
        }}
    </style>
    <script>
        function showTab(tabName) {{
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {{
                content.classList.remove('active');
            }});
            
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to selected tab
            document.querySelector(`[onclick="showTab('${{tabName}}')"]`).classList.add('active');
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Compliance Report</h1>
            <div class="subtitle">Generated on {timestamp}</div>
        </div>
        
        <div class="stats-container">
            <div class="stat-box">
                <div class="stat-value">{total_files}</div>
                <div class="stat-label">Total Files</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{therapy_notes}</div>
                <div class="stat-label">Therapy Notes</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{medical_notes}</div>
                <div class="stat-label">Medical Notes</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{files_with_issues}</div>
                <div class="stat-label">Issues Found</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{files_corrected}</div>
                <div class="stat-label">Auto-Fixed</div>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('therapy')">Therapy Notes ({therapy_notes})</button>
            <button class="tab" onclick="showTab('medical')">Medical Notes ({medical_notes})</button>
        </div>
        
        <!-- Therapy Notes Tab -->
        <div id="therapy" class="tab-content active">
            <div class="content-section">
"""
        
        if therapy_results:
            html += """
                <table>
                    <thead>
                        <tr>
                            <th>File Name</th>
                            <th>Provider</th>
                            <th>Issues</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
"""
            for result in therapy_results:
                filename = result.get('filename', 'Unknown')
                credential = result.get('credential', 'Unknown')
                
                # Determine issues
                issues = []
                if result.get('date_issue', {}).get('found'):
                    issues.append('<span class="badge badge-warning">Date</span>')
                if result.get('cpt_issue', {}).get('found'):
                    issues.append('<span class="badge badge-danger">CPT</span>')
                if result.get('goals_issue', {}).get('found'):
                    issues.append('<span class="badge badge-info">Goals</span>')
                if result.get('supervision_issue', {}).get('found'):
                    issues.append('<span class="badge badge-primary">Supervision</span>')
                
                issues_html = ''.join(issues) if issues else '<span class="badge badge-success">Compliant</span>'
                
                # Status
                status = '<span class="badge badge-success">Corrected</span>' if result.get('corrections_made') else '<span class="badge badge-warning">Review</span>' if issues else '<span class="badge badge-success">OK</span>'
                
                # File links - use absolute paths
                if result.get('corrections_made'):
                    processed_path = os.path.abspath(os.path.join(folders['processed'], filename.replace('.pdf', '_CORRECTED.pdf')))
                    original_path = os.path.abspath(os.path.join(folders['therapy'], filename))
                    links = f'<a href="file://{original_path}" class="file-link">Original</a> | <a href="file://{processed_path}" class="file-link">Corrected</a>'
                else:
                    therapy_path = os.path.abspath(os.path.join(folders['therapy'], filename))
                    links = f'<a href="file://{therapy_path}" class="file-link">View</a>'
                
                html += f"""
                        <tr>
                            <td>{filename}</td>
                            <td>{credential}</td>
                            <td>{issues_html}</td>
                            <td>{status}</td>
                            <td>{links}</td>
                        </tr>
"""
            
            html += """
                    </tbody>
                </table>
"""
        else:
            html += "<p>No therapy notes found.</p>"
        
        html += """
            </div>
        </div>
        
        <!-- Medical Notes Tab -->
        <div id="medical" class="tab-content">
            <div class="content-section">
"""
        
        if medical_results:
            html += """
                <table>
                    <thead>
                        <tr>
                            <th>File Name</th>
                            <th>Provider</th>
                            <th>MDM Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
"""
            for result in medical_results:
                filename = result.get('filename', 'Unknown')
                credential = result.get('credential', 'Medical')
                
                # MDM Status
                meets_mdm = result.get('meets_moderate_mdm', False)
                mdm_status = '<span class="badge badge-success">Meets MDM</span>' if meets_mdm else '<span class="badge badge-warning">Below MDM</span>'
                
                # File link - use absolute path
                medical_path = os.path.abspath(os.path.join(folders['medical'], filename))
                link = f'<a href="file://{medical_path}" class="file-link">View</a>'
                
                html += f"""
                        <tr>
                            <td>{filename}</td>
                            <td>{credential}</td>
                            <td>{mdm_status}</td>
                            <td>{link}</td>
                        </tr>
"""
                
                # Add MDM details row if below MDM
                if not meets_mdm and result.get('mdm_analysis'):
                    mdm = result.get('mdm_analysis', {})
                    recommendations = result.get('recommendations', [])
                    suggested_progress = result.get('suggested_overall_progress', '')
                    suggested_plan = result.get('suggested_improved_plan', '')
                    
                    html += f"""
                        <tr>
                            <td colspan="4">
                                <div class="mdm-section">
                                    <h4>MDM Analysis for {filename}</h4>
                                    <p><strong>Problems Complexity:</strong> {mdm.get('problems_complexity', 'N/A')}</p>
                                    <p><strong>Data Reviewed:</strong> {mdm.get('data_reviewed', 'N/A')}</p>
                                    <p><strong>Risk Level:</strong> {mdm.get('risk_level', 'N/A')}</p>
"""
                    
                    if recommendations:
                        html += """
                                    <div class="recommendation-box">
                                        <h5>Recommendations:</h5>
"""
                        for rec in recommendations:
                            html += f"                                        <p>• {rec}</p>\n"
                        html += "                                    </div>\n"
                    
                    if suggested_progress:
                        html += f"""
                                    <div class="recommendation-box">
                                        <h5>Suggested Overall Progress:</h5>
                                        <p>{suggested_progress}</p>
                                    </div>
"""
                    
                    if suggested_plan:
                        html += f"""
                                    <div class="recommendation-box">
                                        <h5>Suggested Improved Plan:</h5>
                                        <p>{suggested_plan}</p>
                                    </div>
"""
                    
                    html += """
                                </div>
                            </td>
                        </tr>
"""
            
            html += """
                    </tbody>
                </table>
"""
        else:
            html += "<p>No medical notes found.</p>"
        
        html += """
            </div>
        </div>
        
        <div class="footer">
            <p>Compliance Processor v1.0 | Professional Healthcare Documentation</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def process_folder(self, input_path: str):
        """Main processing function"""
        
        print("\n" + "="*80)
        print("THERAPY NOTE COMPLIANCE PROCESSOR")
        print("="*80)
        
        # Setup folders
        folders = self.setup_folders(input_path)
        print(f"\nOrganizing files into:")
        for name, path in folders.items():
            print(f"   - {name}: {path}")
        
        # Find all PDFs
        pdf_files = glob.glob(os.path.join(input_path, "*.pdf"))
        pdf_files = [f for f in pdf_files if '_CORRECTED' not in f]
        
        if not pdf_files:
            print("ERROR: No PDF files found!")
            return
        
        print(f"\nFound {len(pdf_files)} PDF files to process")
        
        results = []
        
        # Process each file
        for i, pdf_path in enumerate(pdf_files, 1):
            filename = os.path.basename(pdf_path)
            print(f"\n[{i}/{len(pdf_files)}] Processing: {filename}")
            
            # Check if therapy note
            is_therapy, credential = self.is_therapy_note(pdf_path)
            
            if not is_therapy:
                print(f"   Medical note detected (Provider: {credential})")
                print(f"   Assessing for Moderate MDM...")
                
                # Extract and analyze for MDM
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        full_text = ""
                        for page in pdf.pages:
                            full_text += page.extract_text() + "\n"
                    
                    print("   Analyzing MDM compliance...")
                    mdm_analysis = self.analyze_medical_note_mdm(full_text, filename)
                    mdm_analysis['is_medical_note'] = True
                    mdm_analysis['credential'] = credential
                    
                    # Move to medical folder
                    shutil.move(pdf_path, os.path.join(folders['medical'], filename))
                    
                    if not mdm_analysis.get('meets_moderate_mdm'):
                        print(f"   WARNING: Does not meet moderate MDM criteria")
                        print(f"   -> Review recommendations in report")
                    else:
                        print(f"   SUCCESS: Meets moderate MDM criteria")
                    
                    results.append(mdm_analysis)
                    
                except Exception as e:
                    print(f"   ERROR analyzing MDM: {e}")
                    results.append({
                        'filename': filename,
                        'is_medical_note': True,
                        'credential': credential,
                        'error': str(e)
                    })
                
                continue
            
            print(f"   Therapy note detected (Provider: {credential})")
            
            # Extract and analyze
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    full_text = ""
                    for page in pdf.pages:
                        full_text += page.extract_text() + "\n"
                
                print("   Analyzing compliance...")
                analysis = self.analyze_with_ai(full_text, filename)
                analysis['credential'] = credential
                
                # Check if corrections needed
                needs_fixing = (
                    analysis.get('date_issue', {}).get('found') or 
                    analysis.get('cpt_issue', {}).get('found') or
                    (analysis.get('goals_issue', {}).get('found') and 
                     analysis.get('goals_issue', {}).get('goals_count', 0) < 2) or
                    analysis.get('supervision_issue', {}).get('found')
                )
                
                if needs_fixing:
                    print("   Applying corrections...")
                    
                    # First, copy the original to therapy folder BEFORE fixing
                    original_path = os.path.join(folders['therapy'], filename)
                    shutil.copy2(pdf_path, original_path)
                    
                    # Apply fixes to the file in current location
                    if self.fix_pdf(pdf_path, analysis, full_text):
                        # Move the CORRECTED file to processed folder
                        corrected_name = filename.replace('.pdf', '_CORRECTED.pdf')
                        corrected_path = os.path.join(folders['processed'], corrected_name)
                        shutil.move(pdf_path, corrected_path)
                        
                        analysis['corrections_made'] = True
                        print(f"   SUCCESS: Saved corrected: {corrected_name}")
                    else:
                        # If fixes failed, remove the working copy
                        os.remove(pdf_path)
                        analysis['corrections_made'] = False
                        print("   WARNING: Could not apply all corrections")
                else:
                    # Move to therapy folder
                    shutil.move(pdf_path, os.path.join(folders['therapy'], filename))
                    analysis['corrections_made'] = False
                
                results.append(analysis)
                
            except Exception as e:
                print(f"   ERROR: {e}")
                results.append({
                    'filename': filename,
                    'error': str(e)
                })
            
            # Small delay to avoid rate limits
            if i % 5 == 0 and i < len(pdf_files):
                print("\nPausing for rate limits...")
                time.sleep(2)
        
        # Generate report
        print("\nGenerating compliance report...")
        report_html = self.generate_modern_report(results, folders)
        
        # Save report
        report_filename = f"therapy_compliance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path = os.path.join(folders['reports'], report_filename)
        
        with open(report_path, 'w') as f:
            f.write(report_html)
        
        print(f"\nReport saved: {report_path}")
        
        # Save JSON
        json_path = report_path.replace('.html', '.json')
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Summary
        print("\n" + "="*80)
        print("PROCESSING COMPLETE")
        print("="*80)
        print(f"Total files: {len(pdf_files)}")
        print(f"Therapy notes: {sum(1 for r in results if not r.get('is_medical_note'))}")
        print(f"Medical notes: {sum(1 for r in results if r.get('is_medical_note'))}")
        print(f"Issues found: {sum(1 for r in results if not r.get('is_medical_note') and (r.get('date_issue', {}).get('found') or r.get('cpt_issue', {}).get('found') or r.get('goals_issue', {}).get('found')))}")
        print(f"Files corrected: {sum(1 for r in results if r.get('corrections_made'))}")
        print(f"\nFiles organized in: {input_path}")
        print(f"Report available at: {report_path}")
        print("\nDone!")

def main():
    parser = argparse.ArgumentParser(description='Process therapy notes for compliance')
    parser.add_argument('path', nargs='?', default='.', help='Path to folder containing PDF files')
    args = parser.parse_args()
    
    processor = TherapyNoteProcessor()
    processor.process_folder(args.path)

if __name__ == "__main__":
    main()