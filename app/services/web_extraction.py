"""Web content extraction and AI-powered pricing/feature parsing."""
import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import WebContent
from app.models.insight import Feature, PricingData
from app.services.asknews_service import AskNewsService

logger = logging.getLogger(__name__)

PAGE_TYPES = ("homepage", "pricing", "about", "features")


class WebExtractionService:
    """Extract website content and use AI to parse pricing and features."""

    def __init__(
        self,
        db: AsyncSession,
        asknews: AskNewsService | None = None,
    ):
        self.db = db
        self.asknews = asknews or AskNewsService()

    async def extract_website_content(
        self,
        competitor_id: int,
        analysis_run_id: int,
        website_url: str,
    ) -> list[WebContent]:
        """Extract content from main page types (homepage, pricing, about, features) and store."""
        results = []
        for page_type in PAGE_TYPES:
            url = website_url.rstrip("/") + ("/" if page_type == "homepage" else f"/{page_type}")
            data = self.asknews.get_web_content(url)
            content = data.get("content") or data.get("raw")
            if isinstance(content, (dict, list)):
                payload = content
            else:
                payload = {"text": str(content) if content else "", "url": url}
            wc = WebContent(
                competitor_id=competitor_id,
                analysis_run_id=analysis_run_id,
                page_type=page_type,
                content=payload if isinstance(payload, dict) else {"data": payload},
            )
            self.db.add(wc)
            results.append(wc)
        await self.db.flush()
        return results

    async def extract_pricing_with_ai(
        self,
        competitor_id: int,
        analysis_run_id: int,
        content: dict[str, Any] | list[Any],
    ) -> list[PricingData]:
        """Parse content with AI to extract pricing plans and store."""
        from app.ai.news_analyzer import NewsAnalyzer

        analyzer = NewsAnalyzer()
        text = json.dumps(content)[:30000]
        plans = analyzer.extract_pricing(text)
        for plan in plans:
            pd = PricingData(
                competitor_id=competitor_id,
                analysis_run_id=analysis_run_id,
                plan_name=plan.get("plan_name"),
                price=plan.get("price"),
                currency=plan.get("currency", "USD"),
                billing_period=plan.get("billing_period"),
                features=plan.get("features"),
                source="ai_extraction",
            )
            self.db.add(pd)
        await self.db.flush()
        return []

    async def extract_features_with_ai(
        self,
        competitor_id: int,
        analysis_run_id: int,
        content: dict[str, Any] | list[Any],
    ) -> list[Feature]:
        """Parse content with AI to extract features and store."""
        from app.ai.news_analyzer import NewsAnalyzer

        analyzer = NewsAnalyzer()
        text = json.dumps(content)[:30000]
        features = analyzer.extract_features(text)
        for f in features:
            feat = Feature(
                competitor_id=competitor_id,
                analysis_run_id=analysis_run_id,
                feature_name=f.get("name") or f.get("feature_name", "Unknown"),
                category=f.get("category"),
                description=f.get("description"),
                is_available=1 if f.get("is_available", True) else 0,
                source="ai_extraction",
            )
            self.db.add(feat)
        await self.db.flush()
        return []
