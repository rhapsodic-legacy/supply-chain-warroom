"""Background scheduler for live data ingestion.

Periodically fetches supply chain news from GDELT and weather data from
Open-Meteo, creating risk events in the database when thresholds are met.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# Global handle so we can cancel on shutdown
_task: asyncio.Task | None = None


async def _run_loop() -> None:
    """Main ingestion loop — runs GDELT and weather checks on a schedule."""
    from app.ingestion.gdelt import ingest_gdelt_news
    from app.ingestion.weather import ingest_weather_alerts

    logger.info("Ingestion scheduler started")

    while True:
        try:
            await ingest_weather_alerts()
        except Exception:
            logger.exception("Weather ingestion failed")

        # GDELT rate limit: 1 req per 5 seconds — add buffer
        await asyncio.sleep(6)

        try:
            await ingest_gdelt_news()
        except Exception:
            logger.exception("GDELT ingestion failed")

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
