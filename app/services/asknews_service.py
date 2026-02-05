"""AskNews API integration for news search and web content."""
import logging
from datetime import datetime, timedelta
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class AskNewsService:
    """Service for AskNews API: news search, web content, sentiment, industry trends."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.client_id = client_id or settings.ASKNEWS_CLIENT_ID
        self.client_secret = client_secret or settings.ASKNEWS_CLIENT_SECRET
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-init AskNews SDK client."""
        if self._client is not None:
            return self._client
        if not self.client_id or not self.client_secret:
            raise ValueError("ASKNEWS_CLIENT_ID and ASKNEWS_CLIENT_SECRET must be set")
        try:
            from asknews_sdk import AskNewsSDK

            self._client = AskNewsSDK(
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=["news", "chat", "stories", "analytics"],
            )
            return self._client
        except ImportError:
            try:
                from asknews import AskNewsSDK

                self._client = AskNewsSDK(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    scopes=["news", "chat", "stories", "analytics"],
                )
                return self._client
            except ImportError as e:
                logger.warning("AskNews SDK not available: %s", e)
                raise ValueError(
                    "Install asknews or asknews-sdk for AskNews integration"
                ) from e

    def search_competitor_news(
        self,
        company_name: str,
        days_back: int = 30,
    ) -> list[dict[str, Any]]:
        """Search news articles mentioning the company."""
        try:
            client = self._get_client()
            since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            # Prefer news.search_news(query, filter_params={...})
            result = client.news.search_news(
                company_name,
                filter_params={"from_date": since} if hasattr(client.news, "search_news") else None,
            )
            # Normalize: SDK may return .as_string or list of articles
            if hasattr(result, "as_string"):
                return [{"content": result.as_string, "title": company_name, "source": "asknews"}]
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "articles" in result:
                return result["articles"]
            if isinstance(result, dict):
                return [result]
            return []
        except Exception as e:
            logger.exception("AskNews search_competitor_news failed: %s", e)
            return []

    def get_web_content(self, url: str) -> dict[str, Any]:
        """Extract website content via AskNews chat/web endpoint."""
        try:
            client = self._get_client()
            if hasattr(client, "chat") and hasattr(client.chat, "get_chat"):
                response = client.chat.get_chat(
                    messages=[{"role": "user", "content": f"Summarize and extract key information from: {url}"}],
                )
                return {"url": url, "content": getattr(response, "content", str(response)), "raw": response}
            # Fallback: return URL for later fetching
            return {"url": url, "content": "", "raw": None}
        except Exception as e:
            logger.exception("AskNews get_web_content failed: %s", e)
            return {"url": url, "content": "", "error": str(e)}

    def analyze_sentiment_batch(self, articles: list[dict[str, Any]]) -> float | None:
        """Calculate average sentiment across articles. Returns -1 to 1 or None."""
        if not articles:
            return None
        scores = []
        for a in articles:
            s = a.get("sentiment_score") if isinstance(a, dict) else getattr(a, "sentiment_score", None)
            if s is not None:
                try:
                    scores.append(float(s))
                except (TypeError, ValueError):
                    pass
        if not scores:
            return None
        return sum(scores) / len(scores)

    def get_industry_trends(
        self,
        industry: str,
        keywords: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get industry trends; optional keywords."""
        try:
            client = self._get_client()
            query = f"{industry} industry trends"
            if keywords:
                query += " " + " ".join(keywords[:5])
            result = client.news.search_news(query) if hasattr(client, "news") else []
            if isinstance(result, list):
                return result
            if hasattr(result, "as_string"):
                return [{"content": result.as_string, "industry": industry}]
            return []
        except Exception as e:
            logger.exception("AskNews get_industry_trends failed: %s", e)
            return []
