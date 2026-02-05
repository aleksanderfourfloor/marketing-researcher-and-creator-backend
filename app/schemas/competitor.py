"""Competitor Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CompetitorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    website_url: Optional[str] = Field(None, max_length=512)
    industry: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=512)
    status: str = Field(default="active", pattern="^(active|inactive)$")


class CompetitorCreate(CompetitorBase):
    pass


class CompetitorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    website_url: Optional[str] = Field(None, max_length=512)
    industry: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=512)
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class CompetitorResponse(CompetitorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompetitorListResponse(BaseModel):
    items: list[CompetitorResponse]
    total: int


class CompetitorBulkCreate(BaseModel):
    competitors: list[CompetitorCreate]
