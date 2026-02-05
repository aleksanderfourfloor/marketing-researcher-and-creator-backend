"""Export API: PDF and CSV/ZIP."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AnalysisRun, Competitor, Insight, DifferentiationOpportunity
from app.models.analysis import AnalysisCompetitor
from app.models.news import NewsMention, MarketPresence
from app.models.insight import Feature, PricingData

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/{analysis_id}/pdf")
async def export_pdf(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Export analysis report as PDF."""
    from app.export.pdf_generator import PDFGenerator

    run_result = await db.execute(select(AnalysisRun).where(AnalysisRun.id == analysis_id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis not found")
    try:
        pdf_bytes = await PDFGenerator(db).generate(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=analysis_{analysis_id}.pdf"},
    )


@router.get("/{analysis_id}/csv")
async def export_csv(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Export analysis data as ZIP of CSVs."""
    from app.export.csv_exporter import CSVExporter

    run_result = await db.execute(select(AnalysisRun).where(AnalysisRun.id == analysis_id))
    if not run_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Analysis not found")
    try:
        zip_bytes = await CSVExporter(db).export_zip(analysis_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=analysis_{analysis_id}.zip"},
    )
