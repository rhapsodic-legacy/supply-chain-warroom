"""GDELT DOC 2.0 API integration for live supply chain news.

Fetches recent news articles matching supply chain disruption keywords,
deduplicates against existing risk events, and creates new events for
genuinely new threats.

API: https://api.gdeltproject.org/api/v2/doc/doc
Rate limit: 1 request per 5 seconds, no API key needed.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import RiskEvent

logger = logging.getLogger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# Keywords that signal supply chain disruptions
SEARCH_QUERIES = [
    "port closure shipping",
    "supply chain disruption",
    "shipping container shortage delay",
    "trade sanctions export controls",
    "dock workers strike port",
    "factory shutdown supplier",
]

# Map GDELT article themes to our event types
KEYWORD_TO_EVENT_TYPE = {
    "port": "port_closure",
    "shipping": "logistics",
    "supplier": "supplier_delay",
    "factory": "supplier_delay",
    "sanction": "geopolitical",
    "tariff": "geopolitical",
    "export control": "geopolitical",
    "strike": "labor_strike",
    "weather": "weather",
    "typhoon": "weather",
    "hurricane": "weather",
    "storm": "weather",
    "flood": "weather",
    "earthquake": "weather",
}

# Region detection from article title/domain
REGION_KEYWORDS = {
    "china": "East Asia",
    "shanghai": "East Asia",
    "shenzhen": "East Asia",
    "beijing": "East Asia",
    "japan": "East Asia",
    "korea": "East Asia",
    "taiwan": "East Asia",
    "vietnam": "East Asia",
    "india": "South Asia",
    "mumbai": "South Asia",
    "rotterdam": "Europe",
    "hamburg": "Europe",
    "europe": "Europe",
    "suez": "Middle East",
    "panama": "Americas",
    "los angeles": "North America",
    "new york": "North America",
    "united states": "North America",
    "brazil": "South America",
}


def _detect_event_type(title: str) -> str:
    """Guess the event type from the article title."""
    title_lower = title.lower()
    for keyword, event_type in KEYWORD_TO_EVENT_TYPE.items():
        if keyword in title_lower:
            return event_type
    return "geopolitical"


def _detect_region(title: str, source_country: str) -> str | None:
    """Guess the affected region from title and source country."""
    combined = f"{title} {source_country}".lower()
    for keyword, region in REGION_KEYWORDS.items():
        if keyword in combined:
            return region
    return None


def _severity_from_title(title: str) -> tuple[str, float]:
    """Estimate severity from title keywords."""
    title_lower = title.lower()
    if any(w in title_lower for w in [
        "crisis", "shutdown", "collapse", "emergency", "critical",
        "blocked", "grounded", "attack", "war", "explosion",
    ]):
        return "critical", 0.85
    if any(w in title_lower for w in [
        "disruption", "severe", "major", "sanctions", "strike",
        "closure", "blockade", "shortage", "shut", "embargo",
    ]):
        return "high", 0.70
    if any(w in title_lower for w in [
        "delay", "congestion", "warning", "risk", "alert",
        "rising", "surge", "pressure", "tension",
    ]):
        return "medium", 0.50
    return "low", 0.30


def _is_supply_chain_relevant(title: str) -> bool:
    """Return True only if the article is plausibly about supply chain operations.

    Filters out noise like fashion articles, travel tips, local news,
    and non-English content that slips past GDELT's language filter.
    """
    title_lower = title.lower()

    # Reject non-ASCII-dominant titles (Chinese, Arabic, etc. that bypass lang filter)
    ascii_chars = sum(1 for c in title if c.isascii())
    if len(title) > 0 and ascii_chars / len(title) < 0.7:
        return False

    # Multi-word phrases — simple substring match is safe (low false-positive risk)
    PHRASE_TERMS = [
        "supply chain", "supply-chain", "trade route", "bulk carrier",
        "production line", "assembly plant", "raw material",
        "trade war", "export ban", "import ban", "export control",
        "strait of hormuz", "suez canal", "panama canal", "south china sea",
        "oil price", "crude oil", "natural gas", "rare earth",
    ]

    # Single / short words — use word-boundary regex to avoid matching inside
    # other words (e.g. "export" inside "report", "port" inside "oportunitie")
    WORD_TERMS = [
        "port", "shipping", "freight", "cargo", "container", "vessel", "maritime",
        "logistics", "warehouse", "customs", "shipment", "tanker",
        "shortage", "disruption", "bottleneck", "backlog", "congestion",
        "closure", "shutdown", "blockade", "embargo", "strike", "walkout",
        "pipeline", "refinery", "semiconductor", "factory", "manufacturing",
        "sanctions", "tariff", "commodity",
        "import", "export",
    ]

    # Reject terms — articles about these topics even if they match a keyword
    REJECT_TERMS = [
        "denim", "fashion", "best time to book", "flight deal", "airfare",
        "recipe", "restaurant", "movie", "album", "concert",
        "football", "basketball", "baseball", "soccer",
        "celebrity", "entertainment", "wedding", "dating",
        "annual financial report", "company announcement",
        "breakfast cereal", "fluoride",
    ]

    if any(term in title_lower for term in REJECT_TERMS):
        return False

    if any(phrase in title_lower for phrase in PHRASE_TERMS):
        return True

    return any(re.search(rf"\b{term}\b", title_lower) for term in WORD_TERMS)


def _article_fingerprint(title: str) -> str:
    """Create a short hash of the title for deduplication."""
    return hashlib.md5(title.lower().strip().encode()).hexdigest()[:12]


async def fetch_gdelt_articles(query: str, max_records: int = 15) -> list[dict]:
    """Fetch articles from GDELT DOC 2.0 API."""
    params = {
        "query": query,
        "mode": "ArtList",
        "maxrecords": max_records,
        "format": "json",
        "timespan": "24h",
        "sourcelang": "english",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(GDELT_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("articles", [])


async def ingest_gdelt_news() -> int:
    """Fetch GDELT news and create risk events for new supply chain threats.

    Returns the number of new risk events created.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = 0

    # Fetch existing event titles for dedup (last 7 days)
    async with session_factory() as session:
        cutoff = datetime.utcnow() - timedelta(days=7)
        result = await session.execute(
            select(RiskEvent.title).where(RiskEvent.created_at >= cutoff)
        )
        existing_titles = {row[0].lower().strip() for row in result.all()}

    # Query GDELT for each keyword set (with rate limit spacing)
    all_articles: list[dict] = []
    import asyncio

    for query in SEARCH_QUERIES:
        try:
            articles = await fetch_gdelt_articles(query, max_records=10)
            all_articles.extend(articles)
        except Exception:
            logger.warning("GDELT query failed for: %s", query[:50])
        await asyncio.sleep(6)  # Respect 1 req / 5 sec rate limit

    if not all_articles:
        logger.info("GDELT: no articles found")
        await engine.dispose()
        return 0

    # Filter to English articles only (GDELT sourcelang filter isn't perfect)
    english_articles = [a for a in all_articles if a.get("language", "").lower() == "english"]

    # Deduplicate by fingerprint
    seen_fps: set[str] = set()
    unique_articles: list[dict] = []
    for article in english_articles:
        fp = _article_fingerprint(article.get("title", ""))
        if fp not in seen_fps:
            seen_fps.add(fp)
            unique_articles.append(article)

    # Create risk events for new articles
    new_events: list[dict] = []
    async with session_factory() as session:
        for article in unique_articles:
            title = article.get("title", "").strip()
            if not title:
                continue

            # Skip if we already have a similar event
            if title.lower().strip() in existing_titles:
                continue

            # Skip articles that aren't about supply chain operations
            if not _is_supply_chain_relevant(title):
                logger.debug("GDELT: skipping irrelevant article — %s", title[:80])
                continue

            severity, severity_score = _severity_from_title(title)
            event_type = _detect_event_type(title)
            region = _detect_region(title, article.get("sourcecountry", ""))

            event = RiskEvent(
                id=str(uuid.uuid4()),
                event_type=event_type,
                title=title[:300],
                description=(
                    f"Detected via GDELT news monitoring. "
                    f"Source: {article.get('domain', 'unknown')}. "
                    f"Published: {article.get('seendate', 'unknown')}. "
                    f"URL: {article.get('url', 'N/A')}"
                ),
                severity=severity,
                severity_score=severity_score,
                affected_region=region,
                started_at=datetime.utcnow(),
                expected_end=datetime.utcnow() + timedelta(days=7),
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(event)
            created += 1
            new_events.append({
                "id": event.id,
                "title": event.title,
                "severity": severity,
                "severity_score": severity_score,
                "event_type": event_type,
                "affected_region": region,
            })
            logger.info("GDELT: created risk event — %s [%s]", title[:80], severity)

        if created > 0:
            await session.commit()

    await engine.dispose()

    # Broadcast new risk events to SSE consumers
    if new_events:
        from app.routers.stream import publish_event

        for evt in new_events:
            await publish_event("risk_update", evt)

    logger.info("GDELT ingestion complete: %d new events", created)
    return created
