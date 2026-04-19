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

class FinalConsolidatedReport(BaseModel):
    extracted_deck_data: Dict[str, Any] = Field(..., description="The initial claims extracted purely from the deck")
    internet_verified_data: Dict[str, VerifiedDataPoint] = Field(..., description="The factual data verified online, with source URLs attached to each point")
    risk_analysis: DiscrepancyAnalysis = Field(..., description="Red and Green flags comparative analysis")
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
