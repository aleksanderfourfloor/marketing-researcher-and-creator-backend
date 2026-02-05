"""AI-powered differentiation insights from analysis data."""
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import (
    AnalysisRun,
    Competitor,
    NewsMention,
    MarketPresence,
    WebContent,
    Feature,
    PricingData,
    Insight,
    DifferentiationOpportunity,
)
from app.models.analysis import AnalysisCompetitor

logger = logging.getLogger(__name__)


class InsightsGenerator:
    """Generate differentiation insights using Claude/GPT-4 from collected data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _call_llm(self, system: str, user: str) -> str:
        """Call OpenAI or Anthropic; return assistant text."""
        if (settings.AI_PROVIDER or "openai").lower() == "anthropic" and settings.ANTHROPIC_API_KEY:
            try:
                import anthropic
                c = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                m = c.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return m.content[0].text if m.content else ""
            except Exception as e:
                logger.warning("Anthropic call failed: %s", e)
        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                r = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=4096,
                )
                return (r.choices[0].message.content or "") if r.choices else ""
            except Exception as e:
                logger.warning("OpenAI call failed: %s", e)
        return "{}"

    async def _load_analysis_context(self, analysis_run_id: int) -> dict[str, Any]:
        """Load all competitors, news, market presence, web content, features, pricing for the run."""
        run_result = await self.db.execute(
            select(AnalysisRun)
            .where(AnalysisRun.id == analysis_run_id)
            .options(
                selectinload(AnalysisRun.competitor_links).selectinload(AnalysisCompetitor.competitor),
            )
        )
        run = run_result.scalar_one_or_none()
        if not run:
            return {}
        comp_ids = [link.competitor_id for link in run.competitor_links]
        competitors = [link.competitor for link in run.competitor_links]
        comp_map = {c.id: {"id": c.id, "name": c.name, "industry": c.industry, "description": c.description} for c in competitors}

        news_result = await self.db.execute(
            select(NewsMention).where(
                NewsMention.analysis_run_id == analysis_run_id,
            )
        )
        news = [{"competitor_id": n.competitor_id, "title": n.title, "source": n.source, "sentiment_score": n.sentiment_score, "content": (n.content or "")[:500]} for n in news_result.scalars().all()]

        mp_result = await self.db.execute(
            select(MarketPresence).where(MarketPresence.analysis_run_id == analysis_run_id)
        )
        market = [{"competitor_id": m.competitor_id, "mention_count": m.mention_count, "sentiment_average": m.sentiment_average, "visibility_score": m.visibility_score, "trend_direction": m.trend_direction} for m in mp_result.scalars().all()]

        wc_result = await self.db.execute(
            select(WebContent).where(WebContent.analysis_run_id == analysis_run_id)
        )
        web = [{"competitor_id": w.competitor_id, "page_type": w.page_type, "content_preview": str(w.content)[:800] if w.content else ""} for w in wc_result.scalars().all()]

        feat_result = await self.db.execute(
            select(Feature).where(Feature.analysis_run_id == analysis_run_id)
        )
        features = [{"competitor_id": f.competitor_id, "feature_name": f.feature_name, "category": f.category, "description": f.description} for f in feat_result.scalars().all()]

        price_result = await self.db.execute(
            select(PricingData).where(PricingData.analysis_run_id == analysis_run_id)
        )
        pricing = [{"competitor_id": p.competitor_id, "plan_name": p.plan_name, "price": p.price, "currency": p.currency, "billing_period": p.billing_period, "features": p.features} for p in price_result.scalars().all()]

        return {
            "analysis_run_id": analysis_run_id,
            "competitors": list(comp_map.values()),
            "competitor_map": comp_map,
            "news_mentions": news,
            "market_presence": market,
            "web_content": web,
            "features": features,
            "pricing": pricing,
        }

    async def generate_differentiation_insights(self, analysis_run_id: int) -> dict[str, Any]:
        """Generate insights and opportunities, store in DB, return summary."""
        context = await self._load_analysis_context(analysis_run_id)
        if not context or not context.get("competitors"):
            return {"error": "No analysis context or competitors found", "stored_insights": 0, "stored_opportunities": 0}

        system = """You are a competitive intelligence analyst. Given data about competitors (news, market presence, web content, features, pricing), produce:
1) insights: array of objects with insight_type (one of: feature_gap, messaging_angle, market_timing, sentiment_opportunity), category, title, description, priority (high/medium/low), actionable_recommendation, supporting_data (object).
2) differentiation_opportunities: array of objects with opportunity_type, title, description, competitors_affected (array of competitor names or ids), impact_score (0-10).
Be specific and actionable. Output only valid JSON in this shape: {"insights": [...], "differentiation_opportunities": [...]}"""

        user = "Context:\n" + json.dumps(context, default=str)[:25000] + "\n\nJSON:"
        raw = self._call_llm(system, user)
        try:
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.strip().startswith("json"):
                    raw = raw.strip()[4:]
            data = json.loads(raw.strip())
        except json.JSONDecodeError as e:
            logger.exception("Insights JSON parse failed: %s", e)
            return {"error": "Failed to parse AI response", "stored_insights": 0, "stored_opportunities": 0}

        insights = data.get("insights") or []
        opportunities = data.get("differentiation_opportunities") or []
        stored_insights = 0
        for i in insights:
            obj = Insight(
                analysis_run_id=analysis_run_id,
                insight_type=i.get("insight_type", "market_timing"),
                category=i.get("category"),
                title=i.get("title", "Insight"),
                description=i.get("description"),
                priority=i.get("priority"),
                actionable_recommendation=i.get("actionable_recommendation"),
                supporting_data=i.get("supporting_data"),
            )
            self.db.add(obj)
            stored_insights += 1
        for o in opportunities:
            obj = DifferentiationOpportunity(
                analysis_run_id=analysis_run_id,
                opportunity_type=o.get("opportunity_type"),
                title=o.get("title", "Opportunity"),
                description=o.get("description"),
                competitors_affected=o.get("competitors_affected"),
                impact_score=o.get("impact_score"),
            )
            self.db.add(obj)
        await self.db.flush()
        return {"stored_insights": stored_insights, "stored_opportunities": len(opportunities)}
