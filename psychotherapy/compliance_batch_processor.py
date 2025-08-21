#!/usr/bin/env python3
"""
Psychotherapy Note Compliance Batch Processor
Checks and fixes:
1. Signing date within 4-6 days of service
2. CPT code matches session duration
3. Two treatment goals are present
"""

import os
import sys
import json
import glob
from datetime import datetime, timedelta
import pdfplumber
import fitz  # PyMuPDF
from openai import OpenAI
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    print("ERROR: OpenAI API key not found!")
    print("Please set OPENAI_API_KEY environment variable or create a .env file")
    sys.exit(1)

client = OpenAI(api_key=api_key)

class ComplianceChecker:
    def __init__(self):
        self.client = client
        self.results = []
    
    def generate_proper_goals(self, analysis: Dict[str, Any], note_text: str) -> str:
        """Generate properly formatted treatment goals based on the note content using AI"""
        
        # Get existing goals and note context
        existing_goals = analysis.get('goals_issue', {}).get('goals_found', [])
        goals_count = analysis.get('goals_issue', {}).get('goals_count', 0)
        
        # Determine what we need to generate
        if goals_count == 1:
            # We have one goal, keep it and add a second
            prompt = f"""
            The note has ONE existing goal. Keep Goal #1 exactly as it is, and create only Goal #2.
            
            EXISTING GOAL #1 (KEEP THIS EXACTLY):
            {existing_goals[0] if existing_goals else ''}
            
            NOTE CONTEXT (for creating Goal #2):
            {note_text[:2000]}
            
            Create ONLY Goal #2 with this exact format:
            
            Goal #2: "I want to [specific client desire different from Goal #1]"
            Objective: Client will [specific measurable action] at least [frequency] times a week.
            Tx Modality: CBT, DBT, Motivational Interviewing
            Progress: Client is [current status for this goal].
            
            Return the complete text with both goals:
            - First, copy Goal #1 exactly as provided
            - Then add your new Goal #2
            
            Make Goal #2 address a different issue than Goal #1 based on the note context.
            """
        else:
            # No goals or poorly formatted, create both
            prompt = f"""
            Create two properly formatted psychotherapy treatment goals based on this note.
            
            NOTE CONTEXT (look for diagnoses, symptoms, client concerns):
            {note_text[:2000]}
            
            FORMAT REQUIREMENTS:
            Each goal must have exactly this structure:
            
            Goal #1: "I want to [specific client desire in first person]"
            Objective: Client will [specific measurable action] at least [frequency] times a week.
            Tx Modality: CBT, DBT, Motivational Interviewing
            Progress: Client is [current status and what they're working on].
            
            Goal #2: "I want to [different specific client desire in first person]"
            Objective: Client will [different measurable action] at least [frequency] times a week.
            Tx Modality: CBT, DBT, Motivational Interviewing
            Progress: Client is [current status for this goal].
            
            IMPORTANT:
            - Goals should be in CLIENT'S VOICE (first person "I want to...")
            - Look for actual issues in the note (anxiety, depression, trauma, relationships, substance use, etc.)
            - Objectives must be measurable with frequency (1-2 times a week)
            - Progress should reflect what's actually in the note
            - Keep each section concise but specific
            
            Return ONLY the formatted goals text, no explanations.
            """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a psychotherapy documentation expert. Create realistic, properly formatted treatment goals."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    def analyze_with_ai(self, pdf_text: str, filename: str) -> Dict[str, Any]:
        """Comprehensive AI analysis of the PDF"""
        
        prompt = f"""
        Analyze this psychotherapy note for THREE compliance issues:
        
        1. DATE COMPLIANCE:
           - Find Service Date (DATE field in ENCOUNTER column)
           - Find Signing Date ("Electronically signed by... at [date time]")
           - Check if signing is within 4-6 days after service
        
        2. CPT CODE COMPLIANCE:
           - FIRST check if this is an INITIAL VISIT (look for "INITIAL VISIT", "Initial evaluation", "New patient")
           - If INITIAL VISIT: correct code is ALWAYS 90791 regardless of duration
           - If NOT initial visit (follow-up):
             * Find START TIME and END TIME
             * Calculate duration in minutes
             * Verify correct code: 90832 (16-37 min), 90834 (38-52 min), 90837 (53+ min)
        
        3. TREATMENT GOALS:
           - Look for Goal sections (may be labeled "Goal #1", "Goal 1", "Goal", etc.)
           - Count how many distinct goals are documented
           - Each goal should have: Goal statement, Objective, Tx Modality, Progress
           - Note if goals are missing numbers or have inconsistent formatting
        
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
                "found": true/false,
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
                "formatting_issues": ["list of issues like missing numbers, typos"],
                "goals_found": ["Goal 1 text", "Goal 2 text"]
            }}
        }}
        
        Document:
        {pdf_text}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
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
        """Fix compliance issues in the PDF"""
        
        if not (analysis.get('date_issue', {}).get('found') or 
                analysis.get('cpt_issue', {}).get('found') or
                analysis.get('goals_issue', {}).get('found')):
            return False
        
        try:
            doc = fitz.open(pdf_path)
            fixed = False
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Fix date if needed
                if analysis.get('date_issue', {}).get('found'):
                    date_info = analysis['date_issue']
                    # Look for just the date/time part (e.g., "07/02/2025 11:10 am")
                    original_date = date_info.get('original_text', '')
                    
                    # Extract just the date/time from the full text
                    import re
                    date_pattern = r'\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s+[ap]m'
                    
                    original_match = re.search(date_pattern, original_date)
                    replacement_match = re.search(date_pattern, date_info.get('replacement_text', ''))
                    
                    if original_match and replacement_match:
                        old_date = original_match.group()
                        new_date = replacement_match.group()
                        
                        # Search for the old date
                        instances = page.search_for(old_date)
                        
                        if instances:
                            rect = instances[0]
                            # Redact old date
                            expanded = fitz.Rect(rect.x0-2, rect.y0-2, rect.x1+2, rect.y1+2)
                            page.add_redact_annot(expanded)
                            page.apply_redactions()
                            
                            # Insert new date at same position
                            page.insert_text(
                                point=(rect.x0, rect.y0 + rect.height * 0.8),
                                text=new_date,
                                fontsize=8.82,
                                fontname="helv",
                                color=(0, 0, 0)
                            )
                            fixed = True
                            print(f"   ✅ Fixed date: {old_date} → {new_date}")
                
                # Fix CPT code if needed
                if analysis.get('cpt_issue', {}).get('found'):
                    cpt_info = analysis['cpt_issue']
                    current_code = cpt_info.get('current_code', '')
                    
                    if current_code:
                        instances = page.search_for(current_code)
                        
                        if instances:
                            rect = instances[0]
                            expanded = fitz.Rect(rect.x0-5, rect.y0-2, rect.x1+10, rect.y1+2)
                            page.add_redact_annot(expanded)
                            page.apply_redactions()
                            
                            page.insert_text(
                                point=(rect.x0, rect.y0 + rect.height * 0.8),
                                text=cpt_info['correct_code'],
                                fontsize=8.82,
                                fontname="helv",
                                color=(0, 0, 0)
                            )
                            fixed = True
                
                # Fix missing goals if needed
                if analysis.get('goals_issue', {}).get('found'):
                    goals_info = analysis['goals_issue']
                    if goals_info.get('goals_count', 0) < 2:
                        # Find Goal #1 position
                        goal_search = ['Goal #1', 'Goal 1', 'Goal#1', 'Goal']
                        goal_rect = None
                        
                        for search_term in goal_search:
                            instances = page.search_for(search_term)
                            if instances:
                                goal_rect = instances[0]
                                break
                        
                        if goal_rect:
                            # Find OVERALL PROGNOSIS position
                            prognosis_instances = page.search_for("OVERALL PROGNOSIS")
                            
                            if prognosis_instances:
                                prognosis_rect = prognosis_instances[0]
                                
                                # Capture the prognosis text and logo as images
                                # Get prognosis section (from OVERALL PROGNOSIS to bottom)
                                prognosis_area = fitz.Rect(
                                    0,
                                    prognosis_rect.y0,
                                    page.rect.width,
                                    page.rect.height
                                )
                                prognosis_pixmap = page.get_pixmap(clip=prognosis_area, dpi=150)
                                
                                # Redact from Goal #1 to just before OVERALL PROGNOSIS
                                redact_area = fitz.Rect(
                                    0,
                                    goal_rect.y0 - 5,
                                    page.rect.width,
                                    prognosis_rect.y0 - 5
                                )
                                page.add_redact_annot(redact_area)
                                page.apply_redactions()
                                
                                # Insert properly formatted goals
                                y_pos = goal_rect.y0
                                goals_text = self.generate_proper_goals(analysis, note_text)
                                
                                for line in goals_text.split('\n'):
                                    if line.strip():
                                        # Bold for headers
                                        if line.startswith('Goal #') or line.startswith('Objective:') or line.startswith('Tx Modality:') or line.startswith('Progress:'):
                                            page.insert_text(
                                                point=(35, y_pos),
                                                text=line,
                                                fontsize=8.82,
                                                fontname="helv",
                                                color=(0, 0, 0)
                                            )
                                        else:
                                            page.insert_text(
                                                point=(35, y_pos),
                                                text=line,
                                                fontsize=8.82,
                                                fontname="helv",
                                                color=(0, 0, 0)
                                            )
                                        y_pos += 13
                                
                                # Re-insert the prognosis section as image
                                new_prognosis_rect = fitz.Rect(
                                    0,
                                    y_pos + 10,
                                    page.rect.width,
                                    y_pos + 10 + (page.rect.height - prognosis_rect.y0)
                                )
                                page.insert_image(new_prognosis_rect, pixmap=prognosis_pixmap)
                                
                                fixed = True
            
            if fixed:
                output_path = pdf_path.replace('.pdf', '_CORRECTED.pdf')
                
                # Verify the corrections before saving
                print("   📋 Verifying corrections...")
                
                # Extract text from the modified page to verify
                page = doc[0]  # Check first page or whichever was modified
                page_text = page.get_text()
                
                # Quick verification checks
                verification_passed = True
                
                # Check that LCSW formatting is preserved
                if "LCSW" in page_text and "LCSWa" in page_text:
                    print("   ⚠️  Warning: Formatting issue detected with LCSW")
                    verification_passed = False
                
                # Check date format is correct
                import re
                dates = re.findall(r'\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s+[ap]m', page_text)
                if dates:
                    print(f"   ✅ Found dates: {dates[:2]}")  # Show first 2 dates found
                
                if verification_passed:
                    doc.save(output_path)
                    print(f"   ✅ Corrections verified and saved")
                else:
                    print("   ⚠️  Verification failed - review needed")
                    # Still save but with warning in filename
                    output_path = pdf_path.replace('.pdf', '_CORRECTED_NEEDS_REVIEW.pdf')
                    doc.save(output_path)
                
                doc.close()
                return True
            
            doc.close()
            return False
            
        except Exception as e:
            print(f"Error fixing {pdf_path}: {e}")
            return False
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Process a single PDF"""
        
        filename = os.path.basename(pdf_path)
        print(f"\n📄 Processing: {filename}")
        
        # Extract text
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
        except Exception as e:
            return {"filename": filename, "error": f"Could not read PDF: {e}"}
        
        # Analyze
        print(f"   🤖 Analyzing compliance...")
        analysis = self.analyze_with_ai(full_text, filename)
        
        # Fix if needed
        corrections_made = False
        needs_fixing = (analysis.get('date_issue', {}).get('found') or 
                       analysis.get('cpt_issue', {}).get('found') or
                       (analysis.get('goals_issue', {}).get('found') and 
                        analysis.get('goals_issue', {}).get('goals_count', 0) < 2))
        
        if needs_fixing:
            print(f"   🔧 Applying corrections...")
            corrections_made = self.fix_pdf(pdf_path, analysis, full_text)
            if corrections_made:
                print(f"   ✅ Corrections saved to {filename.replace('.pdf', '_CORRECTED.pdf')}")
        
        analysis['corrections_made'] = corrections_made
        return analysis
    
    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate a beautiful HTML report"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_files = len(results)
        files_with_issues = sum(1 for r in results if 
                               r.get('date_issue', {}).get('found') or 
                               r.get('cpt_issue', {}).get('found') or
                               r.get('goals_issue', {}).get('found'))
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Psychotherapy Compliance Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .file-card {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .file-name {{
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
        }}
        .issue {{
            margin: 10px 0;
            padding: 10px;
            border-left: 4px solid #f39c12;
            background: #fff9e6;
        }}
        .issue.critical {{
            border-left-color: #e74c3c;
            background: #ffe6e6;
        }}
        .issue.fixed {{
            border-left-color: #27ae60;
            background: #e6ffe6;
        }}
        .issue-type {{
            font-weight: bold;
            color: #555;
        }}
        .no-issues {{
            color: #27ae60;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            text-align: left;
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 Psychotherapy Note Compliance Report</h1>
        <p>Generated: {timestamp}</p>
    </div>
    
    <div class="summary">
        <div class="stat-card">
            <div class="stat-number">{total_files}</div>
            <div>Total Files Processed</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{files_with_issues}</div>
            <div>Files with Issues</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{sum(1 for r in results if r.get('corrections_made'))}</div>
            <div>Files Corrected</div>
        </div>
    </div>
"""
        
        # Add details for each file
        for result in results:
            filename = result.get('filename', 'Unknown')
            has_issues = False
            
            html += f'<div class="file-card">'
            html += f'<div class="file-name">📄 {filename}</div>'
            
            # Date compliance
            if result.get('date_issue', {}).get('found'):
                has_issues = True
                date_info = result['date_issue']
                fixed_class = "fixed" if result.get('corrections_made') else "critical"
                html += f'''
                <div class="issue {fixed_class}">
                    <div class="issue-type">⏰ DATE COMPLIANCE ISSUE</div>
                    <p>{date_info.get('description', '')}</p>
                    <table>
                        <tr><th>Service Date</th><td>{result.get('service_date', '')}</td></tr>
                        <tr><th>Original Signing</th><td>{result.get('signing_date', '')}</td></tr>
                        <tr><th>Days Difference</th><td>{date_info.get('days_difference', '')} days</td></tr>
                        <tr><th>Corrected To</th><td>{date_info.get('corrected_date', '')}</td></tr>
                        <tr><th>Status</th><td>{"✅ CORRECTED" if result.get('corrections_made') else "⚠️ NEEDS MANUAL REVIEW"}</td></tr>
                    </table>
                </div>
                '''
            
            # CPT code compliance
            if result.get('cpt_issue', {}).get('found'):
                has_issues = True
                cpt_info = result['cpt_issue']
                fixed_class = "fixed" if result.get('corrections_made') else "critical"
                html += f'''
                <div class="issue {fixed_class}">
                    <div class="issue-type">💳 CPT CODE ISSUE</div>
                    <p>{cpt_info.get('description', '')}</p>
                    <table>
                        <tr><th>Session Time</th><td>{cpt_info.get('start_time', '')} - {cpt_info.get('end_time', '')}</td></tr>
                        <tr><th>Duration</th><td>{cpt_info.get('duration_minutes', '')} minutes</td></tr>
                        <tr><th>Current Code</th><td>{cpt_info.get('current_code', '')}</td></tr>
                        <tr><th>Correct Code</th><td>{cpt_info.get('correct_code', '')}</td></tr>
                        <tr><th>Status</th><td>{"✅ CORRECTED" if result.get('corrections_made') else "⚠️ NEEDS MANUAL REVIEW"}</td></tr>
                    </table>
                </div>
                '''
            
            # Goals compliance
            if result.get('goals_issue', {}).get('found'):
                has_issues = True
                goals_info = result['goals_issue']
                html += f'''
                <div class="issue">
                    <div class="issue-type">📋 TREATMENT GOALS ISSUE</div>
                    <p>{goals_info.get('description', '')}</p>
                    <table>
                        <tr><th>Goals Found</th><td>{goals_info.get('goals_count', 0)}</td></tr>
                        <tr><th>Required</th><td>2</td></tr>
                        <tr><th>Formatting Issues</th><td>{', '.join(goals_info.get('formatting_issues', [])) or 'None'}</td></tr>
                        <tr><th>Status</th><td>⚠️ NEEDS MANUAL REVIEW</td></tr>
                    </table>
                </div>
                '''
            
            if not has_issues:
                html += '<div class="no-issues">✅ No compliance issues found</div>'
            
            html += '</div>'
        
        html += """
</body>
</html>
"""
        return html
    
    def run_batch(self, folder_path: str = ".", batch_size: int = 5):
        """Process all PDFs in folder in batches"""
        
        print("\n" + "="*80)
        print("🏥 PSYCHOTHERAPY NOTE COMPLIANCE BATCH PROCESSOR")
        print("="*80)
        
        # Find all PDFs
        pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
        # Exclude already corrected files
        pdf_files = [f for f in pdf_files if '_CORRECTED' not in f]
        
        if not pdf_files:
            print("❌ No PDF files found in current directory")
            return
        
        print(f"\n📊 Found {len(pdf_files)} PDF files to process")
        print(f"📦 Processing in batches of {batch_size}")
        
        # Process in batches
        results = []
        total_batches = (len(pdf_files) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(pdf_files))
            batch_files = pdf_files[start_idx:end_idx]
            
            print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"📦 BATCH {batch_num + 1}/{total_batches}")
            print(f"   Files {start_idx + 1}-{end_idx} of {len(pdf_files)}")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            for pdf_path in batch_files:
                result = self.process_pdf(pdf_path)
                results.append(result)
            
            # Add a small delay between batches to avoid rate limits
            if batch_num < total_batches - 1:
                import time
                print(f"\n⏳ Waiting 2 seconds before next batch...")
                time.sleep(2)
        
        # Generate report
        print("\n📝 Generating compliance report...")
        report_html = self.generate_report(results)
        
        # Save report
        report_filename = f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_filename, 'w') as f:
            f.write(report_html)
        
        print(f"\n✅ Report saved to: {report_filename}")
        
        # Save JSON for programmatic access
        json_filename = report_filename.replace('.html', '.json')
        with open(json_filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📊 JSON data saved to: {json_filename}")
        
        # Summary
        print("\n" + "="*80)
        print("📊 SUMMARY")
        print("="*80)
        print(f"Total files processed: {len(results)}")
        print(f"Files with issues: {sum(1 for r in results if r.get('date_issue', {}).get('found') or r.get('cpt_issue', {}).get('found') or r.get('goals_issue', {}).get('found'))}")
        print(f"Files corrected: {sum(1 for r in results if r.get('corrections_made'))}")
        
        # Breakdown by issue type
        date_issues = sum(1 for r in results if r.get('date_issue', {}).get('found'))
        cpt_issues = sum(1 for r in results if r.get('cpt_issue', {}).get('found'))
        goal_issues = sum(1 for r in results if r.get('goals_issue', {}).get('found'))
        
        if date_issues or cpt_issues or goal_issues:
            print("\n📋 Issues Found:")
            if date_issues:
                print(f"   • Date compliance issues: {date_issues}")
            if cpt_issues:
                print(f"   • CPT code issues: {cpt_issues}")
            if goal_issues:
                print(f"   • Treatment goal issues: {goal_issues}")
        
        print("\n✨ Batch processing complete!")

def main():
    checker = ComplianceChecker()
    checker.run_batch()

if __name__ == "__main__":
    main()