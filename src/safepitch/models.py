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


class AuditData(BaseModel):
    """Flat 50-column schema — all fields optional since deck data may be missing."""
    # Identity / Admin
    co_alias: Optional[str] = None
    current_evaluation_stage: Optional[str] = None
    company: Optional[str] = None
    name_of_outside_source: Optional[str] = None
    awe_member: Optional[str] = None
    date_received: Optional[str] = None
    website: Optional[str] = None
    location_city: Optional[str] = None
    country: Optional[str] = None
    place_of_incorporation: Optional[str] = None
    sector: Optional[str] = None
    industry_cluster: Optional[str] = None
    product_offering: Optional[str] = None
    any_ip_patent_details: Optional[str] = None
    unique_differentiator: Optional[str] = None
    business_pitch: Optional[str] = None
    problem_solution: Optional[str] = None
    promoter_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    promoter_linkedin: Optional[str] = None
    year_of_incorporation: Optional[str] = None
    full_address: Optional[str] = None
    social_developmental_impact: Optional[str] = None

    # Financial
    revenue_model: Optional[str] = None
    revenue_year: Optional[str] = None
    ebitda: Optional[str] = None
    unit_economics: Optional[str] = None
    current_round_ask: Optional[str] = None
    current_investors: Optional[str] = None
    ev_revenue_current_fy: Optional[str] = None
    ev_revenue_next_fy: Optional[str] = None
    prior_funding: Optional[str] = None
    total_prior_amount: Optional[str] = None
    prior_round_investors: Optional[str] = None
    prior_round_valuation: Optional[str] = None
    cap_table: Optional[str] = None
    grants_received: Optional[str] = None
    valuation_increase_pct: Optional[str] = None

    # Market
    total_market_size: Optional[str] = None
    addressable_market_size: Optional[str] = None
    industry_cagr: Optional[str] = None
    industry_composition: Optional[str] = None
    co_revenue_cagr: Optional[str] = None
    sales_channels: Optional[str] = None
    competitor_name: Optional[str] = None
    total_fund_raised: Optional[str] = None
    last_post_money_valuation: Optional[str] = None
    revenue_amount: Optional[str] = None

    # Team
    senior_team: Optional[str] = None
    prior_experience: Optional[str] = None
    educational_experience: Optional[str] = None


class FinalAuditOutput(BaseModel):
    """Two-part output: audit_data (Excel schema) + claim_verification (fraud report)."""
    audit_data: AuditData
    claim_verification: VerificationReport


class ErrorOutput(BaseModel):
    """Error response when company is not found."""
    error: str
