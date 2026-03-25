#!/usr/bin/env python
# src/safepitch/main.py

import sys
import os
from safepitch.crew import SafepitchCrew

def run():
    """
    Local test runner for the Safepitch 40-Column Verified Audit.
    """

    # 1. Define the exact columns from your CSV to guide the agents
    excel_schema = (
        "Co Alias, Current Evaluation Stage, Company, Name of Outside Source, "
        "AWE Member, Date Received, Website, Location City, Sector, Industry cluster, "
        "Product Offering, Any IP - Patent Details?, Unique Differentiator?, "
        "Business pitch, Problem / Solution, Promoter Name, Email, Phone, "
        "Promoter LinkedIn, Revenue Model?, B2B/B2C/B2B2C/B2G?, Revenue (Year), "
        "EBITDA, Unit Economics, Current Round Ask, Current Investors, "
        "Current Round Exp Valuation, EV/Revenue (current FY), EV/Revenue (Next FY), "
        "Prior Funding?, Total Prior Amount, Prior Round Investors, Prior Round Valuation, "
        "Cap Table, Grants received, Valuation Increase (%), Total Market Size, "
        "Addressable Market Size, Industry - CAGR, Industry Composition, "
        "Co. Revenue CAGR, Sales Channels, Competitor Name, Country, Total Fund raised, "
        "Last post-money valuation, Revenue (Amount), Senior Team, Prior Experience, "
        "Educational Experience, Year of incorporation, Place of Incorporation, Full Address"
    )

    # 2. Simulated Markdown from LlamaParse for testing
    # In production, this variable comes from the bridge's LlamaParse call.
    mock_pitch_deck_content = """
    # Financial Overview
    The company is seeking $2M at a $10M pre-money valuation.
    Current FY Revenue is $500k with an EBITDA margin of 15%.

    # Market & Team
    TAM is $1.2B in the EdTech sector.
    Founders: Jane Doe (Ex-Google) and John Smith (IIT Alumni).
    Company incorporated in 2022 in Bangalore, India.
    """

    # 3. Inputs for the Crew
    inputs = {
        'company_name': 'Edutech Global',
        'pitch_deck_content': mock_pitch_deck_content,
        'email_body': (
            "Subject: Pitch Deck - Edutech Global. "
            "Hi, I'm Jane. We are building an AI-led learning platform. "
            "LinkedIn: linkedin.com/in/janedoe-example"
        ),
        'excel_schema': excel_schema
    }

    print(f"--- Starting Verified Audit for {inputs['company_name']} ---")

    try:
        # Initialize and kickoff the crew
        result = SafepitchCrew().crew().kickoff(inputs=inputs)

        print("\n\n=== FINAL AUDIT REPORT (JSON) ===")
        # result.raw contains the unified JSON mapped to your schema
        print(result.raw)

        # Save locally for review
        with open("test_audit_result.json", "w") as f:
            f.write(str(result.raw))

    except Exception as e:
        print(f"Error during local test: {e}")

if __name__ == "__main__":
    run()