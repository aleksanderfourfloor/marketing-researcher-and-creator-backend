"""Competitors CRUD and bulk upload API."""
import io
import csv
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Competitor
from app.schemas.competitor import (
    CompetitorCreate,
    CompetitorUpdate,
    CompetitorResponse,
    CompetitorListResponse,
    CompetitorBulkCreate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.post("", response_model=CompetitorResponse)
async def create_competitor(
    payload: CompetitorCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a single competitor."""
    competitor = Competitor(**payload.model_dump())
    db.add(competitor)
    await db.flush()
    await db.refresh(competitor)
    return competitor


@router.get("", response_model=CompetitorListResponse)
async def list_competitors(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    industry: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all competitors with optional filters."""
    q = select(Competitor)
    count_q = select(func.count()).select_from(Competitor)
    if status:
        q = q.where(Competitor.status == status)
        count_q = count_q.where(Competitor.status == status)
    if industry:
        q = q.where(Competitor.industry == industry)
        count_q = count_q.where(Competitor.industry == industry)
    total = (await db.execute(count_q)).scalar() or 0
    q = q.offset(skip).limit(limit).order_by(Competitor.created_at.desc())
    result = await db.execute(q)
    items = list(result.scalars().all())
    return CompetitorListResponse(items=items, total=total)


@router.get("/{competitor_id}", response_model=CompetitorResponse)
async def get_competitor(
    competitor_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get one competitor by ID."""
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return competitor


@router.put("/{competitor_id}", response_model=CompetitorResponse)
async def update_competitor(
    competitor_id: int,
    payload: CompetitorUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a competitor."""
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(competitor, k, v)
    await db.flush()
    await db.refresh(competitor)
    return competitor


@router.delete("/{competitor_id}", status_code=204)
async def delete_competitor(
    competitor_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a competitor."""
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    await db.delete(competitor)
    await db.flush()
    return None


@router.post("/bulk", response_model=CompetitorListResponse)
async def bulk_create_competitors(
    payload: CompetitorBulkCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple competitors from JSON body."""
    created = []
    for c in payload.competitors:
        comp = Competitor(**c.model_dump())
        db.add(comp)
        await db.flush()
        await db.refresh(comp)
        created.append(comp)
    return CompetitorListResponse(items=created, total=len(created))


@router.post("/bulk/csv", response_model=CompetitorListResponse)
async def bulk_upload_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Bulk create competitors from CSV. Expected columns: name, website_url, industry, description, logo_url, status."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file")
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded")
    reader = csv.DictReader(io.StringIO(text))
    created = []
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        comp = Competitor(
            name=name,
            website_url=(row.get("website_url") or "").strip() or None,
            industry=(row.get("industry") or "").strip() or None,
            description=(row.get("description") or "").strip() or None,
            logo_url=(row.get("logo_url") or "").strip() or None,
            status=(row.get("status") or "active").strip() or "active",
        )
        db.add(comp)
        await db.flush()
        await db.refresh(comp)
        created.append(comp)
    return CompetitorListResponse(items=created, total=len(created))
