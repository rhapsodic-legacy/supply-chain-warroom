from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class NormalizePathMiddleware(BaseHTTPMiddleware):
    """Normalize paths so /path and /path/ both resolve without 307 redirects.

    Strips trailing slashes from incoming requests (except root "/"), then
    lets FastAPI match against routes defined without trailing slashes.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.scope["path"]
        if path != "/" and path.endswith("/"):
            request.scope["path"] = path.rstrip("/")
        return await call_next(request)

from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Start live data ingestion in the background
    from app.ingestion.scheduler import start_scheduler, stop_scheduler

    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Supply Chain War Room",
        version="1.0.0",
        lifespan=lifespan,
        redirect_slashes=False,
    )

    application.add_middleware(NormalizePathMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_url,
            "http://localhost:3000",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.routers import (
        agents,
        alert_rules,
        dashboard,
        demo,
        demand,
        orders,
        risks,
        routes,
        simulations,
        stream,
        suppliers,
    )

    application.include_router(dashboard.router)
    application.include_router(demo.router)
    application.include_router(suppliers.router)
    application.include_router(orders.router)
    application.include_router(risks.router)
    application.include_router(routes.router)
    application.include_router(demand.router)
    application.include_router(simulations.router)
    application.include_router(agents.router)
    application.include_router(alert_rules.router)
    application.include_router(stream.router)

    @application.get("/health")
    async def health_check():
        return {"status": "ok"}

    @application.post("/api/v1/ingest/trigger")
    async def trigger_ingestion():
        """Manually trigger a live data ingestion cycle with risk analysis."""
        from app.database import async_session_factory
        from app.ingestion.gdelt import ingest_gdelt_news
        from app.ingestion.weather import ingest_weather_alerts
        from app.services.risk_analysis import run_triage

        weather_count = await ingest_weather_alerts()
        news_count = await ingest_gdelt_news()

        triage_summary = {}
        total_new = weather_count + news_count
        if total_new > 0:
            async with async_session_factory() as session:
                triage_summary = await run_triage(session, total_new)

        return {
            "weather_events_created": weather_count,
            "news_events_created": news_count,
            "triage": triage_summary,
        }

    return application


app = create_app()
