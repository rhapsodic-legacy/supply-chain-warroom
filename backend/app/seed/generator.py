"""Master orchestrator for seeding the Supply Chain War Room database.

Usage:
    python3 -m app.seed.generator
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.seed.constants import PRODUCT_CATALOG
from app.seed.suppliers import generate_suppliers, generate_supplier_products
from app.seed.routes import generate_routes
from app.seed.demand import generate_demand
from app.seed.orders import generate_orders
from app.seed.risk_events import generate_risk_events
from app.seed.agent_decisions import generate_agent_decisions


# Table names in deletion order (respects foreign keys)
_TABLES_DELETE_ORDER = [
    "risk_event_impacts",
    "risk_events",
    "order_events",
    "orders",
    "demand_signals",
    "supplier_products",
    "agent_decisions",
    "simulations",
    "shipping_routes",
    "products",
    "suppliers",
]


def _add_timestamps(rows: list[dict], fields: list[str] | None = None) -> list[dict]:
    """Add missing timestamp fields to seed data rows."""
    if fields is None:
        fields = ["created_at"]
    now = datetime.now().isoformat()
    for row in rows:
        for field in fields:
            if field not in row:
                row[field] = now
    return rows


async def seed_database(db_url: str | None = None) -> None:
    """Generate and insert all synthetic data."""
    # Lazy-import rich so the module can be imported without it
    from rich.console import Console
    from rich.table import Table as RichTable

    console = Console()

    # Resolve database URL
    if db_url is None:
        from app.config import settings

        db_url = settings.database_url

    console.print("\n[bold cyan]Supply Chain War Room — Database Seeder[/bold cyan]")
    console.print(f"[dim]Database: {db_url}[/dim]\n")

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables if they don't exist
    console.print("[yellow]Creating tables if needed...[/yellow]")
    from app.database import Base

    # Ensure all models are imported so metadata knows about them
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    console.print("[green]  Tables ready.[/green]")

    # Clear existing data
    console.print("[yellow]Clearing existing data...[/yellow]")
    async with session_factory() as session:
        for table_name in _TABLES_DELETE_ORDER:
            await session.execute(text(f"DELETE FROM {table_name}"))
        await session.commit()
    console.print("[green]  Cleared.[/green]\n")

    # -----------------------------------------------------------------------
    # Generate data
    # -----------------------------------------------------------------------
    console.print("[bold]Generating synthetic data...[/bold]")

    # Products (from catalog)
    import random as _random

    rng = _random.Random(42)
    products = []
    for p in PRODUCT_CATALOG:
        products.append(
            {
                "id": str(uuid.UUID(int=rng.getrandbits(128))),
                **p,
            }
        )

    console.print(f"  Products:          [cyan]{len(products)}[/cyan]")

    # Suppliers
    suppliers = generate_suppliers(seed=42)
    console.print(f"  Suppliers:         [cyan]{len(suppliers)}[/cyan]")

    # Supplier-product links
    supplier_products = generate_supplier_products(suppliers, products, seed=42)
    console.print(f"  Supplier-products: [cyan]{len(supplier_products)}[/cyan]")

    # Routes
    routes = generate_routes(seed=42)
    console.print(f"  Shipping routes:   [cyan]{len(routes)}[/cyan]")

    # Demand signals
    demand_signals = generate_demand(products, seed=42)
    console.print(f"  Demand signals:    [cyan]{len(demand_signals)}[/cyan]")

    # Orders
    orders = generate_orders(suppliers, products, supplier_products, routes, seed=42)
    console.print(f"  Orders:            [cyan]{len(orders)}[/cyan]")

    # Risk events
    risk_events, risk_impacts = generate_risk_events(suppliers, routes, seed=42)
    active_count = sum(1 for e in risk_events if e["is_active"])
    console.print(f"  Risk events:       [cyan]{len(risk_events)}[/cyan] ({active_count} active)")
    console.print(f"  Risk impacts:      [cyan]{len(risk_impacts)}[/cyan]")

    # Agent decisions
    agent_decisions = generate_agent_decisions(risk_events, orders, suppliers, seed=42)
    console.print(f"  Agent decisions:   [cyan]{len(agent_decisions)}[/cyan]")

    # -----------------------------------------------------------------------
    # Insert data
    # -----------------------------------------------------------------------
    console.print("\n[bold]Inserting into database...[/bold]")

    # Add timestamps to all entities that need them
    _add_timestamps(products, ["created_at"])
    _add_timestamps(suppliers, ["created_at", "updated_at"])
    # supplier_products has no timestamp columns
    _add_timestamps(routes, ["created_at"])
    _add_timestamps(demand_signals, ["created_at"])
    _add_timestamps(orders, ["created_at", "updated_at"])
    _add_timestamps(risk_events, ["created_at"])
    _add_timestamps(risk_impacts, ["created_at"])
    _add_timestamps(agent_decisions, ["created_at"])

    async with session_factory() as session:
        await _bulk_insert(session, "products", products, console)
        await _bulk_insert(session, "suppliers", suppliers, console)
        await _bulk_insert(session, "supplier_products", supplier_products, console)
        await _bulk_insert(session, "shipping_routes", routes, console)
        await _bulk_insert(session, "demand_signals", demand_signals, console)
        await _bulk_insert(session, "orders", orders, console)
        await _bulk_insert(session, "risk_events", risk_events, console)
        await _bulk_insert(session, "risk_event_impacts", risk_impacts, console)
        await _bulk_insert(session, "agent_decisions", agent_decisions, console)
        await session.commit()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    summary = RichTable(title="Seed Summary", show_lines=True)
    summary.add_column("Entity", style="bold")
    summary.add_column("Count", justify="right", style="cyan")
    summary.add_row("Products", str(len(products)))
    summary.add_row("Suppliers", str(len(suppliers)))
    summary.add_row("Supplier-Product Links", str(len(supplier_products)))
    summary.add_row("Shipping Routes", str(len(routes)))
    summary.add_row("Demand Signals", str(len(demand_signals)))
    summary.add_row("Orders", str(len(orders)))
    summary.add_row("Risk Events", str(len(risk_events)))
    summary.add_row("Risk Event Impacts", str(len(risk_impacts)))
    summary.add_row("Agent Decisions", str(len(agent_decisions)))

    console.print()
    console.print(summary)

    # Show active risk events
    console.print("\n[bold red]Active Risk Events:[/bold red]")
    for evt in risk_events:
        if evt["is_active"]:
            sev = evt["severity"].upper()
            color = "red" if sev == "CRITICAL" else "yellow"
            console.print(f"  [{color}][{sev}][/{color}] {evt['title']}")

    console.print("\n[bold green]Database seeded successfully.[/bold green]\n")

    await engine.dispose()


async def _bulk_insert(session: AsyncSession, table_name: str, rows: list[dict], console) -> None:
    """Insert rows using raw SQL for maximum compatibility with SQLite/Postgres."""
    if not rows:
        return

    from sqlalchemy import text as sql_text

    columns = list(rows[0].keys())
    placeholders = ", ".join(f":{col}" for col in columns)
    col_names = ", ".join(columns)

    stmt = sql_text(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})")

    # Insert in batches of 500 for memory efficiency
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        await session.execute(stmt, batch)

    console.print(f"  [green]Inserted {len(rows):>6} rows into {table_name}[/green]")


# -----------------------------------------------------------------------
# CLI entry point
# -----------------------------------------------------------------------
def main() -> None:
    asyncio.run(seed_database())


if __name__ == "__main__":
    main()
