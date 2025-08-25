#!/usr/bin/env python3
import tiktoken

# Initialize tokenizer for GPT-4o
encoding = tiktoken.encoding_for_model("gpt-4")

print("=" * 60)
print("TOTAL COST ANALYSIS FOR 100 CORRECTED NOTES")
print("=" * 60)

# From our previous analysis
input_tokens_per_note = 2803
output_tokens_per_note = 519
files_to_process = 100

# GPT-4o pricing with caching (per million tokens)
cached_price = 1.25  # per 1M tokens
uncached_price = 2.50  # per 1M tokens  
output_price = 10.00  # per 1M tokens

# Cached vs uncached breakdown
cached_tokens_per_note = 730  # System prompt + template
uncached_tokens_per_note = 2073  # Document content

print("\n--- PER NOTE BREAKDOWN ---")
print(f"Input tokens: {input_tokens_per_note:,} (730 cached + 2,073 document)")
print(f"Output tokens: {output_tokens_per_note:,}")
print(f"Total tokens per note: {input_tokens_per_note + output_tokens_per_note:,}")

# Cost per note
cached_cost_per_note = (cached_tokens_per_note / 1_000_000) * cached_price
uncached_cost_per_note = (uncached_tokens_per_note / 1_000_000) * uncached_price
output_cost_per_note = (output_tokens_per_note / 1_000_000) * output_price
total_cost_per_note = cached_cost_per_note + uncached_cost_per_note + output_cost_per_note

print(f"\nCost per note:")
print(f"  Cached input: ${cached_cost_per_note:.5f}")
print(f"  Document input: ${uncached_cost_per_note:.5f}")
print(f"  Output: ${output_cost_per_note:.5f}")
print(f"  TOTAL: ${total_cost_per_note:.4f}")

# 100 notes processing
total_input_tokens = input_tokens_per_note * files_to_process
total_output_tokens = output_tokens_per_note * files_to_process
total_cached_tokens = cached_tokens_per_note * files_to_process
total_uncached_tokens = uncached_tokens_per_note * files_to_process

print("\n--- 100 NOTES PROCESSING ---")
print(f"Total input tokens: {total_input_tokens:,}")
print(f"  - Cached: {total_cached_tokens:,}")
print(f"  - Uncached: {total_uncached_tokens:,}")
print(f"Total output tokens: {total_output_tokens:,}")
print(f"Total tokens: {total_input_tokens + total_output_tokens:,}")

# Cost for 100 notes
total_cached_cost = (total_cached_tokens / 1_000_000) * cached_price
total_uncached_cost = (total_uncached_tokens / 1_000_000) * uncached_price
total_output_cost = (total_output_tokens / 1_000_000) * output_price
total_api_cost = total_cached_cost + total_uncached_cost + total_output_cost

print(f"\nAPI Costs for 100 notes:")
print(f"  Cached input: ${total_cached_cost:.4f}")
print(f"  Document input: ${total_uncached_cost:.4f}")
print(f"  Output: ${total_output_cost:.4f}")
print(f"  TOTAL API COST: ${total_api_cost:.2f}")

# Report generation (if using AI to generate summary)
# Assuming we might use AI to create an executive summary
report_prompt = """
Analyze these 100 therapy note corrections and create an executive summary highlighting:
1. Most common issues found
2. Compliance statistics
3. Recommendations for improvement
Plus the JSON data from all corrections...
"""

# Estimate tokens for report generation
report_input_chars = 170_800  # JSON data from our estimate
report_input_tokens = len(encoding.encode(report_prompt)) + (report_input_chars // 4)  # rough estimate
report_output_tokens = 1500  # Executive summary output

report_input_cost = (report_input_tokens / 1_000_000) * uncached_price
report_output_cost = (report_output_tokens / 1_000_000) * output_price
report_total_cost = report_input_cost + report_output_cost

print("\n--- REPORT GENERATION (Optional AI Summary) ---")
print(f"Report input tokens: ~{report_input_tokens:,}")
print(f"Report output tokens: ~{report_output_tokens:,}")
print(f"Report generation cost: ${report_total_cost:.2f}")

# GRAND TOTAL
grand_total_with_report = total_api_cost + report_total_cost
grand_total_without_report = total_api_cost

print("\n" + "=" * 60)
print("GRAND TOTAL FOR 100 CORRECTED NOTES")
print("=" * 60)
print(f"\nCorrecting 100 notes: ${total_api_cost:.2f}")
print(f"With AI report generation: ${grand_total_with_report:.2f}")
print(f"\nPer-note cost: ${total_api_cost/100:.4f}")
print(f"Per-note with report: ${grand_total_with_report/100:.4f}")

# Storage/output breakdown
print("\n--- OUTPUT FILES ---")
print(f"• 100 corrected PDFs (originals modified)")
print(f"• JSON report: ~167 KB")
print(f"• HTML report: ~417 KB")
print(f"• Total storage: ~0.6 MB (excluding PDFs)")

print("\n--- COST EFFICIENCY ---")
print(f"Manual review time saved: ~{100 * 15} minutes ({100 * 15 / 60:.1f} hours)")
print(f"Cost per hour saved: ${grand_total_with_report / (100 * 15 / 60):.2f}")
print(f"Cost per correction: ${total_api_cost/100:.4f}")