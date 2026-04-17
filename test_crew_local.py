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

# ── Parse CrewAI output to clean JSON ──
def parse_crew_output(result) -> dict:
    """Try to extract clean JSON from CrewAI result object."""
    # CrewAI with output_json=PydanticModel returns parsed objects
    # result.raw might be a dict/string/other
    raw = result.raw if hasattr(result, 'raw') else str(result)

    # If it's already a dict (Pydantic model), convert to dict
    if isinstance(raw, dict):
        return raw
    if hasattr(result, 'pydantic') and result.pydantic:
        return result.pydantic.model_dump() if hasattr(result.pydantic, 'model_dump') else dict(result.pydantic)

    text = raw if isinstance(raw, str) else str(raw)

    # Try markdown code block
    match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try raw JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return {"raw_output": text[:5000]}

# ── Main ──
def main():
    if len(sys.argv) < 2:
        print("Usage: python test_crew_local.py <pdf_path> [company_name]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    company_name = sys.argv[2] if len(sys.argv) > 2 else "Test Company"
    output_file = "crew_output.json"
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    print(f"📄 Reading PDF: {pdf_path}")
    pitch_deck_content = extract_pdf_text(pdf_path)
    print(f"   Extracted {len(pitch_deck_content)} chars")
    
    # Import CrewAI after env is set
    sys.path.insert(0, os.path.abspath("src"))
    from safepitch.crew import SafepitchCrew
    
    excel_schema = (
        "Co Alias, Current Evaluation Stage, Company, Website, Location City, Country, "
        "Place of Incorporation, Sector, Industry cluster, Product Offering, "
        "Revenue Model, Revenue (Year), EBITDA, Unit Economics, Current Round Ask, "
        "Current Investors, Prior Funding?, Prior Round Investors, Prior Round Valuation, "
        "Cap Table, Grants received, Valuation Increase (%), EV/Revenue (current FY), "
        "TAM, SAM, Addressable Market Size, Industry - CAGR, Industry Composition, "
        "Competitor Name, Total Fund raised, Senior Team, Prior Experience, "
        "Educational Experience, Year of incorporation, Full Address"
    )
    
    inputs = {
        "company_name": company_name,
        "pitch_deck_content": pitch_deck_content,
        "email_body": f"Pitch deck for {company_name}",
        "excel_schema": excel_schema,
    }
    
    print(f"\n🚀 Running CrewAI for: {company_name}")
    crew = SafepitchCrew().crew()
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
