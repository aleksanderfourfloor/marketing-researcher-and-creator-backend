"""Analysis run Pydantic schemas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AnalysisCompetitorLink(BaseModel):
    competitor_id: int


class AnalysisRunCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    competitor_ids: list[int] = Field(..., min_length=1)
    parameters: Optional[dict[str, Any]] = None
    created_by: Optional[str] = None


class AnalysisRunResponse(BaseModel):
    id: int
    name: str
    status: str
    parameters: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisRunStatus(BaseModel):
    id: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AnalysisRunListResponse(BaseModel):
    items: list[AnalysisRunResponse]
    total: int
