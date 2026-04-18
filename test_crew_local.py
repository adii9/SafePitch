#!/usr/bin/env python3
"""
Local CrewAI test script.
Usage: python test_crew_local.py <path_to_pdf> [company_name]

Example:
  python test_crew_local.py "/Users/adiimathur/Downloads/mypitchdeck.pdf" "Monitra Healthcare"
"""
import sys
import os
import json
import re
import pdfplumber
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

# ── Env setup (must be before CrewAI imports) ──
os.environ["HOME"] = "/tmp"  # CrewAI writes to ~/.crewai, keep it in /tmp

# MiniMax config
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")
os.environ["SERPER_API_KEY"] = os.environ.get("SERPER_API_KEY", "")

# ── PDF extraction ──
def extract_pdf_text(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text

def parse_crew_output(result) -> dict:
    """Try to extract clean JSON from all tasks in the CrewAI result object."""
    merged_data = {}
    
    # Iterate over all tasks rather than just the final task's output
    if hasattr(result, 'tasks_output'):
        print(f"DEBUG: Found {len(result.tasks_output)} tasks in result.tasks_output")
        for i, task_out in enumerate(result.tasks_output):
            print(f"DEBUG: Task {i} has pydantic: {hasattr(task_out, 'pydantic') and task_out.pydantic is not None}")
            
            # 1. Try pulling directly from Pydantic output
            if hasattr(task_out, 'pydantic') and task_out.pydantic:
                task_data = task_out.pydantic.model_dump() if hasattr(task_out.pydantic, 'model_dump') else dict(task_out.pydantic)
                merged_data.update(task_data)
                print(f"DEBUG: Extracted {len(task_data)} keys from Task {i} pydantic")
                continue
                
            # 2. Try parsing raw text for the task
            text = task_out.raw if hasattr(task_out, 'raw') else str(task_out)
            
            # Try markdown code block first
            match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
            if match:
                try:
                    js = json.loads(match.group(1))
                    merged_data.update(js)
                    print(f"DEBUG: Extracted {len(js)} keys from Task {i} JSON codeblock")
                    continue
                except json.JSONDecodeError:
                    pass
            
            # Strip preambles like "Thought:" and find the JSON object directly
            match = re.search(r"(\{.*?\})", text, re.DOTALL)
            if match:
                try:
                    js = json.loads(match.group(1))
                    merged_data.update(js)
                    print(f"DEBUG: Extracted {len(js)} keys from Task {i} raw JSON block")
                    continue
                except json.JSONDecodeError:
                    print(f"DEBUG: Task {i} raw JSON block failed to parse (possibly truncated)")
                    pass
                    
    if merged_data:
        # Return merged outputs
        print("DEBUG: Successfully assembled merged data.")
        return merged_data

    print("DEBUG: Failing back to raw output string.")
    # Fallback to pure string dump if all fails
    raw = result.raw if hasattr(result, 'raw') else str(result)
    return {"raw_output": raw[:5000]}

# ── Main ──
def main():
    if len(sys.argv) < 2:
        print("Usage: python test_crew_local.py <pdf_path> [company_name]")
        print("Running with mock data directly...")
        pdf_path = "mock"
        company_name = "Mock Company Ltd"
    else:
        pdf_path = sys.argv[1]
        company_name = sys.argv[2] if len(sys.argv) > 2 else "Test Company"
        
    output_file = "crew_output.json"
    
    if pdf_path != "mock" and not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    if pdf_path == "mock":
        pitch_deck_content = "Mock pitch deck. Revenue in 2023 was 10 Million. Founder is Jane Doe. TAM is 50B. They use React and Node."
        print(f"📄 Using mock pitch deck content")
    else:
        print(f"📄 Reading PDF: {pdf_path}")
        pitch_deck_content = extract_pdf_text(pdf_path)
        print(f"   Extracted {len(pitch_deck_content)} chars")
    
    # Import CrewAI after env is set
    sys.path.insert(0, os.path.abspath("src"))
    from safepitch.crew import SafepitchCrew
    
    client_schema = {
        "kyc": [
            {"key": "company_name", "label": "Company*"},
            {"key": "outside_source", "label": "Name of Outside Source + (Inbound/Found)*"},
            {"key": "website", "label": "Website*"},
            {"key": "location_city", "label": "Location City*"},
            {"key": "sector", "label": "Sector* (Climate | Health | Agri | Ed Tech | FinTech | Others (specify in column O ))"},
            {"key": "industry_cluster", "label": "Industry cluster*"},
            {"key": "product_offering", "label": "Product Offering*"},
            {"key": "promoter_name", "label": "Promoter Name*"},
            {"key": "email", "label": "Email*"},
            {"key": "phone", "label": "Phone*"},
            {"key": "promoter_linkedin", "label": "Promoter LinkedIn"},
            {"key": "senior_team", "label": "Senior Team"},
            {"key": "prior_experience", "label": "Prior Experience"},
            {"key": "educational_experience", "label": "Educational Experience"},
            {"key": "year_of_incorporation", "label": "Year of incorporation"},
            {"key": "place_of_incorporation", "label": "Place of Incorporation (City | State)"},
            {"key": "full_address", "label": "Full Address"},
            {"key": "country", "label": "Country"},
            {"key": "social_impact", "label": "Social and Developmental Impact*, if any"}
        ],
        "financial": [
            {"key": "revenue_model", "label": "Revenue Model?* B2B, B2C, B2B2C, B2G?"},
            {"key": "revenue_year", "label": "Revenue (Year)* (In Rs.) Exchange Rate ($1 = 80)"},
            {"key": "ebitda", "label": "EBITDA (If other profit level - specify)"},
            {"key": "unit_economics", "label": "Unit Economics"},
            {"key": "current_round_ask", "label": "Current Round Ask* (in USD) {Year of Ask}{Mn}"},
            {"key": "current_investors", "label": "Current Investors (Names)"},
            {"key": "current_round_exp_valuation", "label": "Current Round Exp Valuation"},
            {"key": "ev_revenue_multiple_current", "label": "EV / Revenue (current FY) Multiple (current ask round )"},
            {"key": "ev_revenue_multiple_next", "label": "EV / Revenue (Next FY) Multiple (current ask round )"},
            {"key": "prior_funding", "label": "Prior Funding* (Yes/No)? Total Amount ($ m / Rs Cr. - specify)"},
            {"key": "prior_round_investors", "label": "Prior Round Investors* from whom funds raised"},
            {"key": "prior_round_valuation", "label": "Prior Round Valuation*"},
            {"key": "cap_table", "label": "Cap Table"},
            {"key": "grants_received", "label": "Grants received/ Challenge Won, if any"},
            {"key": "valuation_increase", "label": "Valuation Increase from Prior round (%)"},
            {"key": "total_fund_raised", "label": "Total Fund raised (Amount in INR million)"},
            {"key": "last_post_money_valuation", "label": "Last post-money valuation (Amount in INR Million)"},
            {"key": "revenue_amount_inr", "label": "Revenue (Amount INR Million)"}
        ],
        "market": [
            {"key": "total_market_size", "label": "Total Market Size* ($million / INR Million) [Specify currency & in millions]"},
            {"key": "addressable_market_size", "label": "Addressable Market Size* ($ million/ INR Million)"},
            {"key": "industry_cagr", "label": "Industry *- CAGR /Time period (from - To)"},
            {"key": "industry_composition", "label": "Industry Composition* (Fragmented or Consolidated)"},
            {"key": "competitor_name", "label": "Competitor Name* (Country) / Cluster members"}
        ]
    }
    
    def format_fields(fields: list) -> str:
        return "\n".join([f"- {f['label']} (JSON key: {f['key']})" for f in fields])
    
    inputs = {
        "company_name": company_name,
        "pitch_deck_content": pitch_deck_content,
        "email_body": f"Pitch deck for {company_name}",
        "dynamic_kyc_fields": format_fields(client_schema["kyc"]),
        "dynamic_financial_fields": format_fields(client_schema["financial"]),
        "dynamic_market_fields": format_fields(client_schema["market"]),
    }
    
    print(f"\n🚀 Running CrewAI for: {company_name}")
    crew = SafepitchCrew(client_schema=client_schema).crew()
    result = crew.kickoff(inputs=inputs)

    print(f"\n📋 Parsing output...")
    parsed = parse_crew_output(result)
    
    # Save to file
    with open(output_file, "w") as f:
        json.dump(parsed, f, indent=2)
    print(f"   Saved to: {output_file}")
    
    # Print summary
    if isinstance(parsed, dict):
        if "audit_data" in parsed or "claim_verification" in parsed:
            print(f"\n✅ Structured output detected!")
            if "audit_data" in parsed:
                print(f"   audit_data keys: {list(parsed['audit_data'].keys())}")
            if "claim_verification" in parsed:
                cv = parsed["claim_verification"]
                print(f"   claim_verification: {cv.get('summary', cv) if isinstance(cv, dict) else 'raw'}")
        elif "error" in parsed:
            print(f"\n⚠️  CrewAI returned error: {parsed['error']}")
        elif "raw_output" in parsed:
            print(f"\n⚠️  No clean JSON — raw output saved (first 500 chars):")
            print(parsed["raw_output"][:500])
    
    print(f"\n✅ Done. Full output in: {output_file}")

if __name__ == "__main__":
    main()
