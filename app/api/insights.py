"""Insights and differentiation opportunities API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AnalysisRun, Insight, DifferentiationOpportunity
from app.schemas.insight import (
    InsightResponse,
    InsightListResponse,
    DifferentiationOpportunityResponse,
)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/{analysis_id}", response_model=InsightListResponse)
async def get_insights(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all insights for an analysis run."""
    run_result = await db.execute(select(AnalysisRun).where(AnalysisRun.id == analysis_id))
    if not run_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Analysis not found")
    result = await db.execute(
        select(Insight).where(Insight.analysis_run_id == analysis_id).order_by(Insight.created_at.desc())
    )
    items = list(result.scalars().all())
    return InsightListResponse(items=items, total=len(items))


@router.get("/{analysis_id}/opportunities")
async def get_opportunities(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get differentiation opportunities for an analysis run."""
    run_result = await db.execute(select(AnalysisRun).where(AnalysisRun.id == analysis_id))
    if not run_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Analysis not found")
    result = await db.execute(
        select(DifferentiationOpportunity)
        .where(DifferentiationOpportunity.analysis_run_id == analysis_id)
        .order_by(DifferentiationOpportunity.created_at.desc())
    )
    items = list(result.scalars().all())
    return {"items": items, "total": len(items)}


@router.post("/generate/{analysis_id}")
async def trigger_generate_insights(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI insight generation for an analysis (can be async in production)."""
    from app.ai.insights_generator import InsightsGenerator

    run_result = await db.execute(select(AnalysisRun).where(AnalysisRun.id == analysis_id))
    if not run_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Analysis not found")
    gen = InsightsGenerator(db)
    summary = await gen.generate_differentiation_insights(analysis_id)
    return summary
