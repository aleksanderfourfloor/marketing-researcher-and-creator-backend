"""Analysis run API: start run, get results, status, list."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import AnalysisRun, AnalysisCompetitor, Competitor
from app.models.news import NewsMention, MarketPresence, WebContent
from app.models.insight import Feature, PricingData, Insight, DifferentiationOpportunity
from app.schemas.analysis import (
    AnalysisRunCreate,
    AnalysisRunResponse,
    AnalysisRunStatus,
    AnalysisRunListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _run_to_response(run: AnalysisRun) -> AnalysisRunResponse:
    return AnalysisRunResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        parameters=run.parameters,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_by=run.created_by,
        created_at=run.created_at,
    )


@router.post("/run", response_model=AnalysisRunResponse)
async def start_analysis(
    payload: AnalysisRunCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new analysis run and enqueue background task."""
    from app.tasks.analysis_tasks import run_full_analysis

    run = AnalysisRun(
        name=payload.name,
        status="pending",
        parameters=payload.parameters,
        created_by=payload.created_by,
    )
    db.add(run)
    await db.flush()
    for cid in payload.competitor_ids:
        link = AnalysisCompetitor(analysis_run_id=run.id, competitor_id=cid)
        db.add(link)
    await db.commit()
    await db.refresh(run)
    # Enqueue Celery task (non-blocking)
    try:
        run_full_analysis.delay(run.id)
    except Exception as e:
        logger.warning("Celery enqueue failed (Redis not running?): %s", e)
    return _run_to_response(run)


@router.get("/{analysis_id}", response_model=AnalysisRunResponse)
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get analysis run by ID."""
    result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == analysis_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _run_to_response(run)


@router.get("/{analysis_id}/status", response_model=AnalysisRunStatus)
async def get_analysis_status(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get analysis run status only."""
    result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == analysis_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisRunStatus(
        id=run.id,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get("", response_model=AnalysisRunListResponse)
async def list_analyses(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all analysis runs."""
    q = select(AnalysisRun)
    count_q = select(func.count()).select_from(AnalysisRun)
    if status:
        q = q.where(AnalysisRun.status == status)
        count_q = count_q.where(AnalysisRun.status == status)
    total = (await db.execute(count_q)).scalar() or 0
    q = q.offset(skip).limit(limit).order_by(AnalysisRun.created_at.desc())
    result = await db.execute(q)
    runs = list(result.scalars().all())
    return AnalysisRunListResponse(
        items=[_run_to_response(r) for r in runs],
        total=total,
    )
