"""Export analysis data as ZIP of CSVs."""
import csv
import io
from zipfile import ZipFile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AnalysisRun, Competitor, Insight, DifferentiationOpportunity
from app.models.analysis import AnalysisCompetitor
from app.models.news import NewsMention, MarketPresence, WebContent
from app.models.insight import Feature, PricingData


class CSVExporter:
    """Export competitors_overview, news_mentions, sentiment_analysis, insights as CSVs in a ZIP."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_zip(self, analysis_id: int) -> bytes:
        """Build ZIP with CSV files."""
        run_result = await self.db.execute(
            select(AnalysisRun).where(AnalysisRun.id == analysis_id).options(
                selectinload(AnalysisRun.competitor_links).selectinload(AnalysisCompetitor.competitor),
            )
        )
        run = run_result.scalar_one_or_none()
        if not run:
            raise ValueError("Analysis not found")
        competitors = [link.competitor for link in run.competitor_links]
        news_result = await self.db.execute(select(NewsMention).where(NewsMention.analysis_run_id == analysis_id))
        news = list(news_result.scalars().all())
        mp_result = await self.db.execute(select(MarketPresence).where(MarketPresence.analysis_run_id == analysis_id))
        market = list(mp_result.scalars().all())
        insights_result = await self.db.execute(select(Insight).where(Insight.analysis_run_id == analysis_id))
        insights = list(insights_result.scalars().all())
        opp_result = await self.db.execute(select(DifferentiationOpportunity).where(DifferentiationOpportunity.analysis_run_id == analysis_id))
        opportunities = list(opp_result.scalars().all())

        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as zf:
            # competitors_overview.csv
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["id", "name", "website_url", "industry", "description", "status"])
            for c in competitors:
                w.writerow([c.id, c.name, c.website_url or "", c.industry or "", (c.description or "")[:500], c.status])
            zf.writestr("competitors_overview.csv", buf.getvalue())

            # news_mentions.csv
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["id", "competitor_id", "title", "url", "source", "published_date", "sentiment_score", "extracted_at"])
            for n in news:
                w.writerow([n.id, n.competitor_id, (n.title or "")[:200], n.url or "", n.source or "", n.published_date, n.sentiment_score, n.extracted_at])
            zf.writestr("news_mentions.csv", buf.getvalue())

            # sentiment_analysis.csv (market presence)
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["competitor_id", "mention_count", "sentiment_average", "visibility_score", "trend_direction", "period_start", "period_end"])
            for m in market:
                w.writerow([m.competitor_id, m.mention_count, m.sentiment_average, m.visibility_score, m.trend_direction, m.period_start, m.period_end])
            zf.writestr("sentiment_analysis.csv", buf.getvalue())

            # insights.csv
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["id", "insight_type", "category", "title", "description", "priority", "actionable_recommendation", "created_at"])
            for i in insights:
                w.writerow([i.id, i.insight_type, i.category or "", (i.title or "")[:200], (i.description or "")[:500], i.priority or "", (i.actionable_recommendation or "")[:300], i.created_at])
            zf.writestr("insights.csv", buf.getvalue())

            # differentiation_opportunities.csv
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["id", "opportunity_type", "title", "description", "competitors_affected", "impact_score", "created_at"])
            for o in opportunities:
                import json
                aff = json.dumps(o.competitors_affected) if o.competitors_affected else ""
                w.writerow([o.id, o.opportunity_type or "", (o.title or "")[:200], (o.description or "")[:500], aff, o.impact_score, o.created_at])
            zf.writestr("differentiation_opportunities.csv", buf.getvalue())

        return buffer.getvalue()
