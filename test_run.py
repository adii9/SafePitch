import os
import json
import pdfplumber
from safepitch.crew import SafepitchCrew

def extract_text_from_pdf(pdf_path):
    text = ""
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return text
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text

def main():
    pdf_path = "/Users/adiimathur/Downloads/Project Titan_IM_2025Dec12 (1).pdf"
    print(f"Parsing PDF: {pdf_path}")
    pitch_deck_content = extract_text_from_pdf(pdf_path)
    
    inputs = {
        'company_name': 'Project Titan',
        'pitch_deck_content': pitch_deck_content,
        'email_body': "Hi, please review this pitch deck for Project Titan.",
        'excel_schema': "{}"
    }
    
    print("Kicking off crew...")
    crew_instance = SafepitchCrew().crew()
    result = crew_instance.kickoff(inputs=inputs)
    
    print("Crew finished. Saving output...")
    with open("test_audit_result.json", "w") as f:
        try:
            # Depending on crewai version, handle result correctly
            json_str = result.raw if hasattr(result, "raw") else str(result)
            # Try to output formatted JSON
            try:
                parsed = json.loads(json_str)
                json.dump(parsed, f, indent=2)
            except json.JSONDecodeError:
                f.write(json_str)
        except Exception as e:
            f.write(str(result))
            print(f"Saved result with exception: {e}")

if __name__ == "__main__":
    main()
