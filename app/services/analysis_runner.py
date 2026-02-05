"""Synchronous analysis runner (no Celery). Used by API and can be triggered by n8n/AI agent."""
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import get_sync_session
from app.models import Competitor, AnalysisRun, AnalysisCompetitor
from app.models.news import NewsMention, MarketPresence, WebContent
from app.models.insight import Feature, PricingData, Insight, DifferentiationOpportunity

logger = logging.getLogger(__name__)


def run_full_analysis_sync(analysis_run_id: int) -> dict:
    """Run full analysis in-process: news, web extraction, market metrics, AI insights. No worker required."""
    session = get_sync_session()
    try:
        run = session.get(AnalysisRun, analysis_run_id)
        if not run:
            return {"error": "Analysis run not found", "analysis_run_id": analysis_run_id}
        run.status = "in_progress"
        run.started_at = datetime.utcnow()
        session.commit()
        days_back = (run.parameters or {}).get("days_back", 30)
        links = session.query(AnalysisCompetitor).filter(
            AnalysisCompetitor.analysis_run_id == analysis_run_id
        ).all()
        comp_ids = [link.competitor_id for link in links]
        for cid in comp_ids:
            try:
                _collect_news_and_presence(session, cid, analysis_run_id, days_back)
                session.commit()
            except Exception as e:
                logger.exception("collect_competitor_news failed: %s", e)
                session.rollback()
            try:
                _extract_website(session, cid, analysis_run_id)
                session.commit()
            except Exception as e:
                logger.exception("extract_competitor_website failed: %s", e)
                session.rollback()
            try:
                _calculate_market_presence(session, cid, analysis_run_id, days_back)
                session.commit()
            except Exception as e:
                logger.exception("calculate_market_metrics failed: %s", e)
                session.rollback()
        try:
            _generate_insights(session, analysis_run_id)
            session.commit()
        except Exception as e:
            logger.exception("generate_insights failed: %s", e)
            session.rollback()
        run = session.get(AnalysisRun, analysis_run_id)
        if run:
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            session.commit()
        return {"analysis_run_id": analysis_run_id, "status": "completed"}
    except Exception as e:
        logger.exception("run_full_analysis_sync failed: %s", e)
        session.rollback()
        run = session.get(AnalysisRun, analysis_run_id)
        if run:
            run.status = "failed"
            session.commit()
        return {"analysis_run_id": analysis_run_id, "status": "failed", "error": str(e)}
    finally:
        session.close()


def _get_company_name(session: Session, competitor_id: int) -> str:
    c = session.get(Competitor, competitor_id)
    return c.name if c else "Unknown"


def _collect_news_and_presence(
    session: Session, competitor_id: int, analysis_run_id: int, days_back: int
) -> None:
    from app.services.asknews_service import AskNewsService
    asknews = AskNewsService()
    svc = _SyncNewsService(session, asknews)
    name = _get_company_name(session, competitor_id)
    svc.collect_competitor_news(competitor_id, analysis_run_id, name, days_back)
    svc.calculate_market_presence(competitor_id, analysis_run_id, days_back)


def _extract_website(session: Session, competitor_id: int, analysis_run_id: int) -> None:
    comp = session.get(Competitor, competitor_id)
    if not comp or not comp.website_url:
        return
    from app.services.asknews_service import AskNewsService
    asknews = AskNewsService()
    svc = _SyncWebExtraction(session, asknews)
    svc.extract_website_content(competitor_id, analysis_run_id, comp.website_url)


def _calculate_market_presence(
    session: Session, competitor_id: int, analysis_run_id: int, days_back: int
) -> None:
    from app.services.asknews_service import AskNewsService
    asknews = AskNewsService()
    svc = _SyncNewsService(session, asknews)
    svc.calculate_market_presence(competitor_id, analysis_run_id, days_back)


def _generate_insights(session: Session, analysis_run_id: int) -> None:
    gen = _SyncInsightsGenerator(session)
    gen.generate_differentiation_insights(analysis_run_id)


class _SyncNewsService:
    def __init__(self, session: Session, asknews):
        self.session = session
        self.asknews = asknews

    def collect_competitor_news(
        self, competitor_id: int, analysis_run_id: int, company_name: str, days_back: int = 30
    ) -> None:
        articles = self.asknews.search_competitor_news(company_name, days_back=days_back)
        for art in articles:
            if isinstance(art, dict):
                title = art.get("title") or art.get("headline") or company_name
                url = art.get("url") or art.get("link")
                source = art.get("source")
                pub = art.get("published_date") or art.get("date") or art.get("publishedAt")
                content = art.get("content") or art.get("description") or art.get("summary")
                sentiment = art.get("sentiment_score")
            else:
                title = getattr(art, "title", company_name)
                url = getattr(art, "url", None)
                source = getattr(art, "source", None)
                pub = getattr(art, "published_date", None)
                content = getattr(art, "content", None)
                sentiment = getattr(art, "sentiment_score", None)
            if isinstance(pub, str):
                try:
                    from dateutil import parser as date_parser
                    pub = date_parser.parse(pub)
                except Exception:
                    pub = None
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
            self.session.add(mention)
        self.session.flush()

    def calculate_market_presence(
        self, competitor_id: int, analysis_run_id: int, days_back: int = 30
    ) -> None:
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days_back)
        mentions = list(
            self.session.query(NewsMention).filter(
                NewsMention.competitor_id == competitor_id,
                NewsMention.analysis_run_id == analysis_run_id,
                NewsMention.published_date >= period_start,
                NewsMention.published_date <= period_end,
            ).all()
        )
        if not mentions:
            return
        sentiment_sum = sum(m.sentiment_score for m in mentions if m.sentiment_score is not None)
        sentiment_count = sum(1 for m in mentions if m.sentiment_score is not None)
        sentiment_avg = sentiment_sum / sentiment_count if sentiment_count else None
        mention_count = len(mentions)
        visibility_score = min(100.0, mention_count * 2.0)
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
        self.session.add(mp)
        self.session.flush()


class _SyncWebExtraction:
    PAGE_TYPES = ("homepage", "pricing", "about", "features")

    def __init__(self, session: Session, asknews):
        self.session = session
        self.asknews = asknews

    def extract_website_content(
        self, competitor_id: int, analysis_run_id: int, website_url: str
    ) -> None:
        for page_type in self.PAGE_TYPES:
            url = website_url.rstrip("/") + ("/" if page_type == "homepage" else f"/{page_type}")
            data = self.asknews.get_web_content(url)
            content = data.get("content") or data.get("raw")
            payload = (
                content
                if isinstance(content, (dict, list))
                else {"text": str(content) if content else "", "url": url}
            )
            if not isinstance(payload, dict):
                payload = {"data": payload}
            wc = WebContent(
                competitor_id=competitor_id,
                analysis_run_id=analysis_run_id,
                page_type=page_type,
                content=payload,
            )
            self.session.add(wc)
        self.session.flush()


class _SyncInsightsGenerator:
    def __init__(self, session: Session):
        self.session = session

    def generate_differentiation_insights(self, analysis_run_id: int) -> None:
        session = self.session
        run = session.get(AnalysisRun, analysis_run_id)
        if not run:
            return
        links = session.query(AnalysisCompetitor).filter(
            AnalysisCompetitor.analysis_run_id == analysis_run_id
        ).all()
        competitors = [session.get(Competitor, link.competitor_id) for link in links]
        competitors = [c for c in competitors if c]
        if not competitors:
            return
        comp_map = {
            c.id: {"id": c.id, "name": c.name, "industry": c.industry, "description": c.description}
            for c in competitors
        }
        news = session.query(NewsMention).filter(NewsMention.analysis_run_id == analysis_run_id).all()
        market = session.query(MarketPresence).filter(MarketPresence.analysis_run_id == analysis_run_id).all()
        web = session.query(WebContent).filter(WebContent.analysis_run_id == analysis_run_id).all()
        features = session.query(Feature).filter(Feature.analysis_run_id == analysis_run_id).all()
        pricing = session.query(PricingData).filter(PricingData.analysis_run_id == analysis_run_id).all()
        context = {
            "analysis_run_id": analysis_run_id,
            "competitors": list(comp_map.values()),
            "news_mentions": [
                {"competitor_id": n.competitor_id, "title": n.title, "source": n.source, "sentiment_score": n.sentiment_score}
                for n in news
            ],
            "market_presence": [
                {
                    "competitor_id": m.competitor_id,
                    "mention_count": m.mention_count,
                    "sentiment_average": m.sentiment_average,
                    "visibility_score": m.visibility_score,
                    "trend_direction": m.trend_direction,
                }
                for m in market
            ],
            "web_content": [{"competitor_id": w.competitor_id, "page_type": w.page_type} for w in web],
            "features": [
                {"competitor_id": f.competitor_id, "feature_name": f.feature_name, "category": f.category}
                for f in features
            ],
            "pricing": [
                {"competitor_id": p.competitor_id, "plan_name": p.plan_name, "price": p.price, "currency": p.currency}
                for p in pricing
            ],
        }
        system = """You are a competitive intelligence analyst. Given data about competitors, produce:
1) insights: array of objects with insight_type (feature_gap, messaging_angle, market_timing, sentiment_opportunity), category, title, description, priority (high/medium/low), actionable_recommendation, supporting_data (object).
2) differentiation_opportunities: array of objects with opportunity_type, title, description, competitors_affected (array), impact_score (0-10).
Output only valid JSON: {"insights": [...], "differentiation_opportunities": [...]}"""
        user = "Context:\n" + json.dumps(context, default=str)[:25000] + "\n\nJSON:"
        raw = _call_llm_sync(system, user)
        try:
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.strip().startswith("json"):
                    raw = raw.strip()[4:]
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            return
        for i in data.get("insights") or []:
            session.add(
                Insight(
                    analysis_run_id=analysis_run_id,
                    insight_type=i.get("insight_type", "market_timing"),
                    category=i.get("category"),
                    title=i.get("title", "Insight"),
                    description=i.get("description"),
                    priority=i.get("priority"),
                    actionable_recommendation=i.get("actionable_recommendation"),
                    supporting_data=i.get("supporting_data"),
                )
            )
        for o in data.get("differentiation_opportunities") or []:
            session.add(
                DifferentiationOpportunity(
                    analysis_run_id=analysis_run_id,
                    opportunity_type=o.get("opportunity_type"),
                    title=o.get("title", "Opportunity"),
                    description=o.get("description"),
                    competitors_affected=o.get("competitors_affected"),
                    impact_score=o.get("impact_score"),
                )
            )
        session.flush()


def _call_llm_sync(system: str, user: str) -> str:
    from app.config import settings
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
            return m.content[0].text if m.content else "{}"
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
            return (r.choices[0].message.content or "{}") if r.choices else "{}"
        except Exception as e:
            logger.warning("OpenAI call failed: %s", e)
    return "{}"
