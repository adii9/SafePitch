#!/usr/bin/env python
# src/safepitch/main.py

import sys
import os
from safepitch.crew import SafepitchCrew
from crewai.flow.flow import Flow, listen, start
from crewai.flow.persistence import persist

class SafepitchFlow(Flow):
    @start()
    def run_crew(self):
        """
        Local test runner for the Safepitch 40-Column Verified Audit.
        """
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

        mock_pitch_deck_content = """
        # Financial Overview
        The company is seeking $2M at a $10M pre-money valuation.
        Current FY Revenue is $500k with an EBITDA margin of 15%.

        # Market & Team
        TAM is $1.2B in the EdTech sector.
        Founders: Jane Doe (Ex-Google) and John Smith (IIT Alumni).
        Company incorporated in 2022 in Bangalore, India.
        """

        # Fetch inputs passed via state if any (for AWS Lambda). Otherwise mock.
        provided_inputs = self.state.get('inputs', {})
        
        inputs = {
            'company_name': provided_inputs.get('company_name', 'Edutech Global'),
            'pitch_deck_content': provided_inputs.get('pitch_deck_content', mock_pitch_deck_content),
            'email_body': provided_inputs.get('email_body', 
                "Subject: Pitch Deck - Edutech Global. "
                "Hi, I'm Jane. We are building an AI-led learning platform. "
                "LinkedIn: linkedin.com/in/janedoe-example"
            ),
            'excel_schema': excel_schema
        }

        print(f"--- Starting Verified Audit for {inputs['company_name']} ---")

        # Initialize and kickoff the crew
        result = SafepitchCrew().crew().kickoff(inputs=inputs)
        return result.raw

    @listen(run_crew)
    @persist()
    def save_final_step(self, audit_report):
        print("\n\n=== FINAL AUDIT REPORT (JSON) ===")
        print(audit_report)

        # Store in state so Lambda handler can easily retrieve it
        self.state['audit_report'] = audit_report

        # Save locally for review (fails silently in read-only lambda env if not /tmp)
        try:
            with open("test_audit_result.json", "w") as f:
                f.write(str(audit_report))
        except IOError:
            pass
            
        print("\n--- Final step data successfully persisted! ---")
        return {"audit_report": audit_report}

def run():
    try:
        flow = SafepitchFlow()
        flow.kickoff()
    except Exception as e:
        print(f"Error during local test: {e}")

if __name__ == "__main__":
    run()