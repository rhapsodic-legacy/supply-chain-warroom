from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Supply Chain War Room",
        version="1.0.0",
        lifespan=lifespan,
    )

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
        dashboard,
        demand,
        orders,
        risks,
        routes,
        simulations,
        stream,
        suppliers,
    )

    application.include_router(dashboard.router)
    application.include_router(suppliers.router)
    application.include_router(orders.router)
    application.include_router(risks.router)
    application.include_router(routes.router)
    application.include_router(demand.router)
    application.include_router(simulations.router)
    application.include_router(agents.router)
    application.include_router(stream.router)

    @application.get("/health")
    async def health_check():
        return {"status": "ok"}

    return application


app = create_app()
