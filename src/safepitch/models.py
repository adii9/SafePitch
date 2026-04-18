# src/safepitch/models.py
# Pydantic models for CrewAI JSON output enforcement
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ClaimSummary(BaseModel):
    total: int
    verified: int
    unverified: int
    contradicted: int
    truth_score: int


class VerifiedClaim(BaseModel):
    claim_id: str
    category: str
    claim: str
    verification_result: str
    evidence: str
    confidence: str


class UnverifiedClaim(BaseModel):
    claim_id: str
    category: str
    claim: str
    verification_result: str
    evidence: str
    confidence: str


class ContradictedClaim(BaseModel):
    claim_id: str
    category: str
    claim: str
    verification_result: str
    evidence: str
    magnitude: Optional[str] = None


class CriticalRedFlag(BaseModel):
    flag_id: str
    severity: str
    description: str


class OverallRiskAssessment(BaseModel):
    investment_readiness: str
    fraud_likelihood: str
    red_flags_count: int
    critical_findings: str


class VerificationReport(BaseModel):
    summary: ClaimSummary
    verified_claims: List[VerifiedClaim]
    unverified_claims: List[UnverifiedClaim]
    contradicted_claims: List[ContradictedClaim]
    field_level_verification: Dict[str, Any]
    critical_red_flags: List[CriticalRedFlag]
    overall_risk_assessment: OverallRiskAssessment


from pydantic import BaseModel, Field, create_model

def create_dynamic_model(model_name: str, fields_list: List[Dict[str, str]]) -> type[BaseModel]:
    """
    Dynamically creates a Pydantic model for CrewAI based on a list of field definitions.
    fields_list should be a list of dictionaries with 'key' and 'label'.
    """
    fields = {}
    for f in fields_list:
        key = f.get("key")
        label = f.get("label")
        if key:
            # We make all fields optional strings by default since the deck might be missing data
            fields[key] = (Optional[str], Field(default=None, description=label))
            
    return create_model(model_name, **fields)

class ErrorOutput(BaseModel):
    """Error response when company is not found."""
    error: str
