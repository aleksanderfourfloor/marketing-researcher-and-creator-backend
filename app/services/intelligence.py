"""Orchestration and high-level intelligence services."""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Competitor, AnalysisRun, AnalysisCompetitor
from app.services.asknews_service import AskNewsService
from app.services.news_service import NewsService
from app.services.web_extraction import WebExtractionService

logger = logging.getLogger(__name__)


class IntelligenceService:
    """Orchestrates data collection and delegates to specialized services."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.asknews = AskNewsService()
        self.news_service = NewsService(db, self.asknews)
        self.web_extraction = WebExtractionService(db, self.asknews)

    async def run_competitor_news_and_presence(
        self,
        competitor_id: int,
        analysis_run_id: int,
        days_back: int = 30,
    ) -> dict[str, Any]:
        """Collect news and compute market presence for one competitor."""
        result = await self.db.execute(select(Competitor).where(Competitor.id == competitor_id))
        comp = result.scalar_one_or_none()
        if not comp:
            return {"error": "Competitor not found", "competitor_id": competitor_id}
        name = comp.name
        try:
            count = await self.news_service.collect_competitor_news(
                competitor_id, analysis_run_id, name, days_back
            )
            mp = await self.news_service.calculate_market_presence(
                competitor_id, analysis_run_id, days_back
            )
            return {"news_count": count, "market_presence": mp.id if mp else None}
        except Exception as e:
            logger.exception("run_competitor_news_and_presence failed: %s", e)
            return {"error": str(e), "competitor_id": competitor_id}

    async def run_competitor_web_extraction(
        self,
        competitor_id: int,
        analysis_run_id: int,
        website_url: str | None = None,
    ) -> dict[str, Any]:
        """Extract web content (and optionally pricing/features with AI) for one competitor."""
        url = website_url
        if not url:
            result = await self.db.execute(select(Competitor).where(Competitor.id == competitor_id))
            comp = result.scalar_one_or_none()
            if not comp:
                return {"error": "Competitor not found", "competitor_id": competitor_id}
            url = comp.website_url
        if not url:
            return {"error": "No website_url", "competitor_id": competitor_id}
        try:
            pages = await self.web_extraction.extract_website_content(
                competitor_id, analysis_run_id, url
            )
            return {"pages": len(pages), "competitor_id": competitor_id}
        except Exception as e:
            logger.exception("run_competitor_web_extraction failed: %s", e)
            return {"error": str(e), "competitor_id": competitor_id}
