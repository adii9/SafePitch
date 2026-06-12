from pydantic import BaseModel, Field, create_model
from typing import Optional, List, Dict, Any

class FlagSummary(BaseModel):
    flag: str
    description: str

class DiscrepancyAnalysis(BaseModel):
    red_flags: List[FlagSummary] = Field(default_factory=list, description="List of contradictions or missing critical data")
    green_flags: List[FlagSummary] = Field(default_factory=list, description="List of verified strengths or positive findings")

class StartupRating(BaseModel):
    score: float = Field(..., description="The numerical score calculated based on the VC's rating criteria")
    reasoning: str = Field(..., description="A paragraph explaining the scoring relative to the criteria")

class VerifiedDataPoint(BaseModel):
    value: str = Field(..., description="The verified or updated data value")
    source_url: str = Field(default="Not found", description="The specific URL where this data was verified or found")

class VerificationReport(BaseModel):
    """Output of the claim_truth_scoring_task. The LLM fills summary + tier; truth_score
    is computed deterministically in Python from upstream task outputs to keep scores
    reproducible across runs."""
    truth_score: Optional[int] = Field(default=None, ge=0, le=100, description="Composite credibility score, 0-100. Computed deterministically in Python; the LLM does not set this directly.")
    tier: str = Field(..., description="One of 'high' (>=85), 'medium' (>=60), 'low' (<60).")
    summary: str = Field(..., description="One sentence (max 25 words) stating the strongest concern or what was not verified.")


def _tier_from_score(score: int) -> str:
    """Pure function: tier label from numeric truth score."""
    if score >= 85:
        return "high"
    if score >= 60:
        return "medium"
    return "low"


def compute_truth_score(
    red_flags: list,
    green_flags: list,
    internet_verified_data: dict,
) -> int:
    """
    Apply the verification rubric deterministically.

    Rubric (locked — do not change without updating SPEC + spec.md):
        Start at 100.
        -12 per red_flag, +4 per green_flag.
        -1 per internet_verified_data field with source_url == "pitch_deck" (not externally verified).
        -3 per internet_verified_data field with source_url is null (could not be found).
        Clamp to [0, 100].

    Accepts the raw upstream values (Pydantic models or dicts). Returns int 0-100.
    """
    score = 100
    score -= 12 * len(red_flags or [])
    score += 4 * len(green_flags or [])

    for value in (internet_verified_data or {}).values():
        # Pydantic VerifiedDataPoint or dict — both supported.
        if isinstance(value, dict):
            src = value.get("source_url")
        else:
            src = getattr(value, "source_url", None)
        if src == "pitch_deck":
            score -= 1
        elif src is None:
            score -= 3
        # Real external URL: no deduction.

    return max(0, min(100, score))


def make_verification_report(
    red_flags: list,
    green_flags: list,
    internet_verified_data: dict,
    summary: str,
) -> VerificationReport:
    """Build a complete VerificationReport with the score computed deterministically."""
    score = compute_truth_score(red_flags, green_flags, internet_verified_data)
    return VerificationReport(
        truth_score=score,
        tier=_tier_from_score(score),
        summary=summary,
    )

class FinalConsolidatedReport(BaseModel):
    extracted_deck_data: Dict[str, Any] = Field(..., description="The initial claims extracted purely from the deck")
    internet_verified_data: Dict[str, VerifiedDataPoint] = Field(..., description="The factual data verified online, with source URLs attached to each point")
    risk_analysis: DiscrepancyAnalysis = Field(..., description="Red and Green flags comparative analysis")
    verification: Optional[VerificationReport] = Field(default=None, description="Truth score and credibility summary from the claim truth scoring task")
    scoring: StartupRating = Field(..., description="The final VC-weighted startup score")

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
            fields[key] = (Optional[str], Field(default=None, description=label))
            
    return create_model(model_name, **fields)

class ErrorOutput(BaseModel):
    """Error response when company is not found."""
    error: str
