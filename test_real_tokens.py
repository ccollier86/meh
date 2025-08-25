#!/usr/bin/env python3
import os
import json
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv
import tiktoken

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize tokenizer
encoding = tiktoken.encoding_for_model("gpt-4o")

# Load the PDF
pdf_path = "psychotherapy/therapynote1.pdf"
print(f"Processing: {pdf_path}")
print("=" * 60)

with pdfplumber.open(pdf_path) as pdf:
    pdf_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

print(f"PDF text length: {len(pdf_text)} characters")

# The exact prompts from the code
system_prompt = "You are an expert medical auditor specializing in evaluation and management (E&M) coding and medical decision making complexity. Analyze thoroughly and return valid JSON."

user_prompt = f"""
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
    "filename": "{os.path.basename(pdf_path)}",
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

# Calculate input tokens BEFORE making the API call
system_tokens = len(encoding.encode(system_prompt))
user_tokens = len(encoding.encode(user_prompt))
total_input_tokens = system_tokens + user_tokens

print(f"\n--- PRE-CALL TOKEN ESTIMATE ---")
print(f"System prompt tokens: {system_tokens:,}")
print(f"User prompt tokens: {user_tokens:,}")
print(f"Total input tokens (estimated): {total_input_tokens:,}")

# Make the actual API call with detailed response
print("\n--- MAKING API CALL ---")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0,
    response_format={"type": "json_object"}
)

# Get actual token usage from response
actual_input_tokens = response.usage.prompt_tokens
actual_output_tokens = response.usage.completion_tokens
actual_total_tokens = response.usage.total_tokens

print(f"\n--- ACTUAL TOKEN USAGE FROM API ---")
print(f"Input tokens (actual): {actual_input_tokens:,}")
print(f"Output tokens (actual): {actual_output_tokens:,}")
print(f"Total tokens (actual): {actual_total_tokens:,}")

# Parse the response
result = json.loads(response.choices[0].message.content)

# Show output size
output_json = json.dumps(result, indent=2)
print(f"\n--- OUTPUT DETAILS ---")
print(f"Output JSON characters: {len(output_json):,}")
print(f"Output JSON size: {len(output_json) / 1024:.2f} KB")

# Calculate costs with actual tokens
# GPT-4o pricing: $2.50 per 1M input (but you said $1.25), $10 per 1M output
input_cost_per_million = 1.25  # Using your provided rate
output_cost_per_million = 10.00

actual_input_cost = (actual_input_tokens / 1_000_000) * input_cost_per_million
actual_output_cost = (actual_output_tokens / 1_000_000) * output_cost_per_million
actual_total_cost = actual_input_cost + actual_output_cost

print(f"\n--- ACTUAL COST CALCULATION ---")
print(f"Input cost ({actual_input_tokens:,} tokens @ ${input_cost_per_million}/1M): ${actual_input_cost:.6f}")
print(f"Output cost ({actual_output_tokens:,} tokens @ ${output_cost_per_million}/1M): ${actual_output_cost:.6f}")
print(f"TOTAL COST PER NOTE: ${actual_total_cost:.6f}")

print(f"\n--- COST AT SCALE ---")
print(f"10 notes: ${actual_total_cost * 10:.4f}")
print(f"100 notes: ${actual_total_cost * 100:.2f}")
print(f"1,000 notes: ${actual_total_cost * 1000:.2f}")
print(f"10,000 notes: ${actual_total_cost * 10000:.2f}")

# Save the actual response for review
with open("actual_api_response.json", "w") as f:
    json.dump({
        "token_usage": {
            "input_tokens": actual_input_tokens,
            "output_tokens": actual_output_tokens,
            "total_tokens": actual_total_tokens
        },
        "costs": {
            "input_cost": actual_input_cost,
            "output_cost": actual_output_cost,
            "total_cost": actual_total_cost
        },
        "response": result
    }, f, indent=2)

print(f"\n--- SUMMARY ---")
print(f"✓ Actual input tokens: {actual_input_tokens:,}")
print(f"✓ Actual output tokens: {actual_output_tokens:,}")
print(f"✓ Total cost per correction: ${actual_total_cost:.6f}")
print(f"✓ Cost for 100 notes: ${actual_total_cost * 100:.2f}")