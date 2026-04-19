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
        # --- Hardcoded fallback schema ---
        _fallback_schema = {
            "kyc": [
                {"key": "promoter_name", "label": "Promoter / Founder Name"},
                {"key": "promoter_linkedin", "label": "Founder LinkedIn URL"},
                {"key": "founder_background", "label": "Founder Background"},
                {"key": "founder_education", "label": "Founder Education"},
                {"key": "product_stage", "label": "Product Stage"},
                {"key": "product_differentiation", "label": "Product Differentiation"},
                {"key": "tech_stack", "label": "Tech Stack"}
            ],
            "financial": [
                {"key": "revenue", "label": "Revenue"},
                {"key": "revenue_growth_rate", "label": "Revenue Growth Rate"},
                {"key": "burn_rate", "label": "Burn Rate"},
                {"key": "runway", "label": "Runway (months)"},
                {"key": "current_round", "label": "Current Fundraising Round"},
                {"key": "funding_stage", "label": "Funding Stage"},
                {"key": "amount_raising", "label": "Amount Raising"},
                {"key": "pre_money_valuation", "label": "Pre-money Valuation"}
            ],
            "market": [
                {"key": "tam", "label": "TAM (Total Addressable Market)"},
                {"key": "sam", "label": "SAM (Serviceable Addressable Market)"},
                {"key": "som", "label": "SOM (Serviceable Obtainable Market)"},
                {"key": "competitors_listed", "label": "Competitors Listed"},
                {"key": "competitive_landscape", "label": "Competitive Landscape"}
            ]
        }

        # --- Build client_schema dynamically from tenant evaluation_criteria ---
        # The Lambda handler injects evaluation_criteria into flow.state['inputs']
        # during onboarding. If it's present and has must_have fields, we use those
        # for the kyc section; financial and market sections stay as the fallback.
        provided_inputs = self.state.get('inputs', {})
        evaluation_criteria = provided_inputs.get('evaluation_criteria')

        if evaluation_criteria and evaluation_criteria.get('must_have'):
            dynamic_kyc = [
                {"key": field["key"], "label": field["label"]}
                for field in evaluation_criteria["must_have"]
                if "key" in field and "label" in field
            ]
            client_schema = {
                "kyc": dynamic_kyc,
                "financial": _fallback_schema["financial"],
                "market": _fallback_schema["market"],
            }
            print(f"Using dynamic evaluation_criteria: {len(dynamic_kyc)} must-have fields loaded.")
        else:
            client_schema = _fallback_schema
            print("No evaluation_criteria in state — using hardcoded fallback schema.")

        def format_fields(fields: list) -> str:
            return "\n".join([f"- {f['label']} (JSON key: {f['key']})" for f in fields])
        
        mock_pitch_deck_content = """
        # Financial Overview
        The company is seeking $2M at a $10M pre-money valuation.
        Current FY Revenue is $500k with an EBITDA margin of 15%.

        # Market & Team
        TAM is $1.2B in the EdTech sector.
        Founders: Jane Doe (Ex-Google) and John Smith (IIT Alumni).
        Company incorporated in 2022 in Bangalore, India.
        """
        
        # 'provided_inputs' already resolved above when building client_schema.
        inputs = {
            'company_name': provided_inputs.get('company_name', 'Edutech Global'),
            'pitch_deck_content': provided_inputs.get('pitch_deck_content', mock_pitch_deck_content),
            'email_body': provided_inputs.get('email_body',
                "Subject: Pitch Deck - Edutech Global. "
                "Hi, I'm Jane. We are building an AI-led learning platform. "
                "LinkedIn: linkedin.com/in/janedoe-example"
            ),
            'dynamic_kyc_fields': format_fields(client_schema['kyc']),
            'dynamic_financial_fields': format_fields(client_schema['financial']),
            'dynamic_market_fields': format_fields(client_schema['market']),
        }

        # Pass rating_criteria through to the crew if the tenant provided one
        rating_criteria = provided_inputs.get('rating_criteria')
        if rating_criteria:
            inputs['rating_criteria'] = rating_criteria
            print("rating_criteria injected into crew inputs.")

        print(f"--- Starting Verified Audit for {inputs['company_name']} ---")

        # Initialize and kickoff the crew
        result = SafepitchCrew(client_schema=client_schema).crew().kickoff(inputs=inputs)
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