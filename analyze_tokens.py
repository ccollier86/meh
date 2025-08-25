#!/usr/bin/env python3
import tiktoken
import pdfplumber
import json
from pathlib import Path

# Initialize tokenizer for GPT-4
encoding = tiktoken.encoding_for_model("gpt-4")

# Load a sample therapy note
sample_note_path = Path("psychotherapy/test_docs/therapy_notes/therapynote1.pdf")
with pdfplumber.open(sample_note_path) as pdf:
    pdf_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

# The system prompt
system_prompt = """You are an expert medical auditor specializing in evaluation and management (E&M) coding and medical decision making complexity. Analyze thoroughly and return valid JSON."""

# The user prompt template (from the code)
user_prompt_template = """
Analyze this psychotherapy note for FOUR compliance issues:

1. DATE COMPLIANCE:
   - Service Date (DATE field in ENCOUNTER column)
   - Signing Date ("Electronically signed by... at [date time]")
   - Check if signing is within 4-6 days after service

2. CPT CODE COMPLIANCE:
   - LOOK RIGHT ABOVE THE START TIME/END TIME - it will say either "INITIAL VISIT" or "FOLLOW-UP"
   - If it says "INITIAL VISIT" AND duration is 53 minutes or more: code should be 90791
   - If it says "FOLLOW-UP": 
     * 90791 is WRONG - NEVER use 90791 for follow-ups!
     * Calculate duration from START TIME to END TIME
     * 16-37 minutes = 90832
     * 38-52 minutes = 90834  
     * 53 minutes or more = 90837
   - CRITICAL: A 53-minute or 60-minute FOLLOW-UP should be 90837, NOT 90791!

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
{document}
"""

# Calculate tokens for input
full_user_prompt = user_prompt_template.replace("{filename}", "therapynote1.pdf").replace("{document}", pdf_text)

# Calculate input tokens
system_tokens = len(encoding.encode(system_prompt))
user_tokens = len(encoding.encode(full_user_prompt))
total_input_tokens = system_tokens + user_tokens

# Estimate output tokens (typical response)
sample_output = {
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

output_tokens = len(encoding.encode(json.dumps(sample_output, indent=2)))

# Print analysis
print("=" * 60)
print("TOKEN USAGE ANALYSIS FOR THERAPY NOTE CORRECTION")
print("=" * 60)
print(f"\nMODEL: GPT-4 (gpt-4)")
print(f"\nSAMPLE NOTE: {sample_note_path}")
print(f"Note text length: {len(pdf_text)} characters")
print("\n--- INPUT TOKENS ---")
print(f"System prompt tokens: {system_tokens:,}")
print(f"User prompt + note tokens: {user_tokens:,}")
print(f"TOTAL INPUT TOKENS: {total_input_tokens:,}")
print("\n--- OUTPUT TOKENS ---")
print(f"Estimated output tokens: {output_tokens:,}")
print("\n--- TOTAL PER REQUEST ---")
print(f"Total tokens per correction: {total_input_tokens + output_tokens:,}")

# Updated pricing from user (December 2024)
# GPT-4o with caching:
# - Standard Input: $2.50 per 1M tokens
# - Cached Input: $1.25 per 1M tokens  
# - Output: $10.00 per 1M tokens

# GPT-4 (older pricing for comparison)
gpt4_input_cost = (total_input_tokens / 1000) * 0.03
gpt4_output_cost = (output_tokens / 1000) * 0.06
gpt4_total_cost = gpt4_input_cost + gpt4_output_cost

# GPT-4o with current pricing (no caching)
gpt4o_input_cost = (total_input_tokens / 1_000_000) * 2.50
gpt4o_output_cost = (output_tokens / 1_000_000) * 10.00
gpt4o_total_cost = gpt4o_input_cost + gpt4o_output_cost

# GPT-4o with cached input (prompt template is cached, only document changes)
# Assuming system prompt + user prompt template can be cached (~700 tokens)
# Only the document content varies (~2100 tokens)
cached_tokens = system_tokens + 700  # System + template
uncached_tokens = total_input_tokens - cached_tokens  # Document content

gpt4o_cached_input_cost = (cached_tokens / 1_000_000) * 1.25
gpt4o_uncached_input_cost = (uncached_tokens / 1_000_000) * 2.50
gpt4o_cached_total_cost = gpt4o_cached_input_cost + gpt4o_uncached_input_cost + gpt4o_output_cost

print("\n--- COST ANALYSIS (GPT-4 Legacy Pricing) ---")
print(f"Input cost: ${gpt4_input_cost:.4f}")
print(f"Output cost: ${gpt4_output_cost:.4f}")
print(f"TOTAL COST PER CORRECTION: ${gpt4_total_cost:.4f}")

print("\n--- COST ANALYSIS (GPT-4o Current Pricing) ---")
print(f"Input cost (no caching): ${gpt4o_input_cost:.4f}")
print(f"Output cost: ${gpt4o_output_cost:.4f}")
print(f"TOTAL COST PER CORRECTION: ${gpt4o_total_cost:.4f}")

print("\n--- COST ANALYSIS (GPT-4o with Prompt Caching) ---")
print(f"Cached input tokens: {cached_tokens:,} @ $1.25/1M")
print(f"Uncached input tokens: {uncached_tokens:,} @ $2.50/1M")
print(f"Cached input cost: ${gpt4o_cached_input_cost:.4f}")
print(f"Uncached input cost: ${gpt4o_uncached_input_cost:.4f}")
print(f"Output cost: ${gpt4o_output_cost:.4f}")
print(f"TOTAL COST PER CORRECTION: ${gpt4o_cached_total_cost:.4f}")

total_cost = gpt4o_cached_total_cost  # Use most efficient option

print("\n--- COST COMPARISON ---")
print(f"GPT-4 (legacy): ${gpt4_total_cost:.4f} per note")
print(f"GPT-4o (no cache): ${gpt4o_total_cost:.4f} per note")
print(f"GPT-4o (with cache): ${gpt4o_cached_total_cost:.4f} per note")
print(f"Savings vs GPT-4: ${gpt4_total_cost - gpt4o_cached_total_cost:.4f} ({((gpt4_total_cost - gpt4o_cached_total_cost) / gpt4_total_cost * 100):.1f}% cheaper)")

print("\n--- COST AT SCALE (GPT-4o with Caching) ---")
print(f"10 notes: ${total_cost * 10:.4f}")
print(f"100 notes: ${total_cost * 100:.2f}")
print(f"1,000 notes: ${total_cost * 1000:.2f}")
print(f"10,000 notes: ${total_cost * 10000:.2f}")

print("\n--- HIGH CONFIDENCE ESTIMATE ---")
print(f"Cost per correction: ${total_cost:.4f}")
print(f"This includes ~2,800 input tokens and ~500 output tokens")
print(f"With prompt caching, effective cost is ~${total_cost:.4f} per note")