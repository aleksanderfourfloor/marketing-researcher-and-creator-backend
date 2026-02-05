"""Insight and differentiation opportunity schemas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class InsightResponse(BaseModel):
    id: int
    analysis_run_id: int
    insight_type: str
    category: Optional[str] = None
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    actionable_recommendation: Optional[str] = None
    supporting_data: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InsightListResponse(BaseModel):
    items: list[InsightResponse]
    total: int


class DifferentiationOpportunityResponse(BaseModel):
    id: int
    analysis_run_id: int
    opportunity_type: Optional[str] = None
    title: str
    description: Optional[str] = None
    competitors_affected: Optional[list[Any]] = None
    impact_score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}
