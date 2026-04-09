"""Background scheduler for live data ingestion and risk analysis.

Periodically fetches supply chain news from GDELT and weather data from
Open-Meteo, creating risk events in the database when thresholds are met.
After each ingestion cycle, runs automated risk triage (rule-based) and
optionally invokes the Risk Monitor agent for deep analysis.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# Global handle so we can cancel on shutdown
_task: asyncio.Task | None = None


async def _run_loop() -> None:
    """Main ingestion + analysis loop."""
    from app.database import async_session_factory
    from app.ingestion.gdelt import ingest_gdelt_news
    from app.ingestion.weather import ingest_weather_alerts
    from app.services.risk_analysis import run_agent_analysis, run_triage

    logger.info("Ingestion scheduler started")

    while True:
        weather_count = 0
        news_count = 0

        try:
            weather_count = await ingest_weather_alerts()
        except Exception:
            logger.exception("Weather ingestion failed")

        # GDELT rate limit: 1 req per 5 seconds — add buffer
        await asyncio.sleep(6)

        try:
            news_count = await ingest_gdelt_news()
        except Exception:
            logger.exception("GDELT ingestion failed")

        # --- Risk analysis pipeline ---
        total_new = weather_count + news_count
        try:
            async with async_session_factory() as session:
                triage = await run_triage(session, total_new)

                # Deep analysis only when triage finds concerning signals
                if triage.get("suppliers_at_risk") or triage.get("regional_escalations"):
                    await run_agent_analysis(session, triage)
        except Exception:
            logger.exception("Risk analysis pipeline failed")

        # Wait 30 minutes before next cycle
        await asyncio.sleep(30 * 60)


def start_scheduler() -> None:
    """Start the background ingestion loop (call from FastAPI lifespan)."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_run_loop())
        logger.info("Ingestion scheduler task created")


def stop_scheduler() -> None:
    """Cancel the ingestion loop (call on shutdown)."""
    global _task
    if _task and not _task.done():
        _task.cancel()
        logger.info("Ingestion scheduler cancelled")
