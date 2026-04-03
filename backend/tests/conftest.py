"""Shared fixtures for the Supply Chain War Room test suite."""

import asyncio
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# In-memory SQLite engine (shared across all tests in a session)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite://"

_engine = create_async_engine(TEST_DB_URL, echo=False)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def engine():
    return _engine


@pytest_asyncio.fixture(scope="session")
async def _create_tables():
    """Create all tables once per session."""
    from app.database import Base
    import app.models  # noqa: F401 — ensure models register with metadata

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session(_create_tables):
    """Provide a transactional session that rolls back after each test."""
    async with _session_factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------


def _get_test_app():
    """Import and configure the FastAPI app with the test DB override."""
    from app.database import get_db
    from app.main import create_app

    app = create_app()

    async def _override_get_db():
        async with _session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest_asyncio.fixture
async def client(_create_tables):
    """httpx AsyncClient wired to the FastAPI app with the test DB."""
    app = _get_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Seeded database — insert seed data once then reuse
# ---------------------------------------------------------------------------

_seeded = False


async def _seed_once():
    """Insert seed data into the test database (idempotent)."""
    global _seeded
    if _seeded:
        return
    _seeded = True

    import random as _random

    from app.seed.constants import PRODUCT_CATALOG
    from app.seed.demand import generate_demand
    from app.seed.orders import generate_orders
    from app.seed.risk_events import generate_risk_events
    from app.seed.routes import generate_routes
    from app.seed.suppliers import generate_supplier_products, generate_suppliers

    rng = _random.Random(42)
    products = []
    for p in PRODUCT_CATALOG:
        products.append({"id": str(uuid.UUID(int=rng.getrandbits(128))), **p})

    suppliers = generate_suppliers(seed=42)
    supplier_products = generate_supplier_products(suppliers, products, seed=42)
    routes = generate_routes(seed=42)
    demand_signals = generate_demand(products, seed=42)
    orders = generate_orders(suppliers, products, supplier_products, routes, seed=42)
    risk_events, risk_impacts = generate_risk_events(suppliers, routes, seed=42)

    now = datetime.now().isoformat()

    def _ts(rows, fields=None):
        fields = fields or ["created_at"]
        for row in rows:
            for f in fields:
                if f not in row:
                    row[f] = now
        return rows

    _ts(products, ["created_at"])
    _ts(suppliers, ["created_at", "updated_at"])
    _ts(routes, ["created_at"])
    _ts(demand_signals, ["created_at"])
    _ts(orders, ["created_at", "updated_at"])
    _ts(risk_events, ["created_at"])
    _ts(risk_impacts, ["created_at"])

    async def _insert(session, table_name, rows):
        if not rows:
            return
        columns = list(rows[0].keys())
        placeholders = ", ".join(f":{col}" for col in columns)
        col_names = ", ".join(columns)
        stmt = text(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})")
        for i in range(0, len(rows), 500):
            await session.execute(stmt, rows[i : i + 500])

    async with _session_factory() as session:
        await _insert(session, "products", products)
        await _insert(session, "suppliers", suppliers)
        await _insert(session, "supplier_products", supplier_products)
        await _insert(session, "shipping_routes", routes)
        await _insert(session, "demand_signals", demand_signals)
        await _insert(session, "orders", orders)
        await _insert(session, "risk_events", risk_events)
        await _insert(session, "risk_event_impacts", risk_impacts)
        await session.commit()


@pytest_asyncio.fixture
async def seeded_db(_create_tables):
    """A session with seed data already inserted."""
    await _seed_once()
    async with _session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_client(_create_tables):
    """httpx AsyncClient with seed data in the database."""
    await _seed_once()
    app = _get_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
