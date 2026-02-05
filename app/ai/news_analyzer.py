"""AI-powered extraction of pricing and features from text (OpenAI/Anthropic)."""
import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class NewsAnalyzer:
    """Uses GPT-4 or Claude to extract structured pricing and features from content."""

    def _call_llm(self, system: str, user: str) -> str:
        """Call OpenAI or Anthropic; return assistant text."""
        if (settings.AI_PROVIDER or "openai").lower() == "anthropic" and settings.ANTHROPIC_API_KEY:
            try:
                import anthropic
                c = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                m = c.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2048,
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
                    max_tokens=2048,
                )
                return (r.choices[0].message.content or "") if r.choices else ""
            except Exception as e:
                logger.warning("OpenAI call failed: %s", e)
        return "[]"

    def extract_pricing(self, text: str) -> list[dict[str, Any]]:
        """Extract pricing plans from text. Returns list of {plan_name, price, currency, billing_period, features}."""
        system = """You are a data extractor. From the given text, extract pricing information.
Return a JSON array of objects. Each object must have: plan_name (string), price (number or null), currency (e.g. USD), billing_period (monthly/yearly/one-time or null), features (array of strings).
If no pricing found, return []."""
        user = f"Text:\n{text[:15000]}\n\nJSON array:"
        raw = self._call_llm(system, user)
        try:
            # Strip markdown code block if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            return []

    def extract_features(self, text: str) -> list[dict[str, Any]]:
        """Extract product features from text. Returns list of {name, category, description, is_available}."""
        system = """You are a data extractor. From the given text, extract product or service features.
Return a JSON array of objects. Each object: name (or feature_name), category (string or null), description (string or null), is_available (boolean, default true).
If no features found, return []."""
        user = f"Text:\n{text[:15000]}\n\nJSON array:"
        raw = self._call_llm(system, user)
        try:
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            return []
