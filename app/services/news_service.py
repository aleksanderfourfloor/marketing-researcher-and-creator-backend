"""News collection and market presence calculation."""
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news import NewsMention, MarketPresence
from app.services.asknews_service import AskNewsService

logger = logging.getLogger(__name__)


class NewsService:
    """Collect competitor news and compute market presence metrics."""

    def __init__(self, db: AsyncSession, asknews: AskNewsService | None = None):
        self.db = db
        self.asknews = asknews or AskNewsService()

    async def collect_competitor_news(
        self,
        competitor_id: int,
        analysis_run_id: int,
        company_name: str,
        days_back: int = 30,
    ) -> int:
        """Fetch news for company from AskNews and store in news_mentions. Returns count stored."""
        articles = self.asknews.search_competitor_news(company_name, days_back=days_back)
        count = 0
        for art in articles:
            if isinstance(art, dict):
                title = art.get("title") or art.get("headline") or company_name
                url = art.get("url") or art.get("link")
                source = art.get("source") or art.get("publisher", {}).get("name") if isinstance(art.get("publisher"), dict) else None
                pub = art.get("published_date") or art.get("date") or art.get("publishedAt")
                content = art.get("content") or art.get("description") or art.get("summary")
                sentiment = art.get("sentiment_score")
                if isinstance(pub, str):
                    try:
                        pub = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pub = None
            else:
                title = getattr(art, "title", company_name)
                url = getattr(art, "url", None)
                source = getattr(art, "source", None)
                pub = getattr(art, "published_date", None)
                content = getattr(art, "content", None)
                sentiment = getattr(art, "sentiment_score", None)

            mention = NewsMention(
                competitor_id=competitor_id,
                analysis_run_id=analysis_run_id,
                title=title or company_name,
                url=url,
                source=source,
                published_date=pub,
                content=content,
                sentiment_score=float(sentiment) if sentiment is not None else None,
            )
            self.db.add(mention)
            count += 1
        await self.db.flush()
        return count

    async def calculate_market_presence(
        self,
        competitor_id: int,
        analysis_run_id: int,
        days_back: int = 30,
    ) -> MarketPresence | None:
        """Compute mention count, avg sentiment, visibility, trend and store in market_presence."""
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days_back)
        result = await self.db.execute(
            select(NewsMention)
            .where(
                NewsMention.competitor_id == competitor_id,
                NewsMention.analysis_run_id == analysis_run_id,
                NewsMention.published_date >= period_start,
                NewsMention.published_date <= period_end,
            )
        )
        mentions = list(result.scalars().all())
        if not mentions:
            return None
        sentiment_sum = sum(m.sentiment_score for m in mentions if m.sentiment_score is not None)
        sentiment_count = sum(1 for m in mentions if m.sentiment_score is not None)
        sentiment_avg = sentiment_sum / sentiment_count if sentiment_count else None
        mention_count = len(mentions)
        visibility_score = min(100.0, mention_count * 2.0) if mention_count else 0.0
        trend_direction = "rising" if mention_count >= 5 else "stable" if mention_count >= 2 else "declining"
        mp = MarketPresence(
            competitor_id=competitor_id,
            analysis_run_id=analysis_run_id,
            mention_count=mention_count,
            sentiment_average=sentiment_avg,
            visibility_score=visibility_score,
            trend_direction=trend_direction,
            period_start=period_start,
            period_end=period_end,
        )
        self.db.add(mp)
        await self.db.flush()
        return mp
