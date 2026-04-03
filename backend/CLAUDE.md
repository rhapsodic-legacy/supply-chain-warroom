# Backend — FastAPI Supply Chain API

Python 3.12 FastAPI backend with SQLAlchemy async ORM, Pydantic v2, and Claude Agent SDK.

## Structure

```
backend/
  app/
    main.py              FastAPI app factory, CORS, router registration
    config.py            Settings via pydantic-settings
    database.py          SQLAlchemy async engine, session factory, Base
    models/              SQLAlchemy ORM models (10 tables)
    schemas/             Pydantic request/response schemas
    routers/             API route modules
    services/            Business logic layer
    agents/              Claude Agent SDK integration
      orchestrator.py    Hub agent, routes to specialists
      risk_monitor.py    Risk detection + scoring
      simulation_agent.py Triggers Monte Carlo sims
      strategy_agent.py  Mitigation recommendations
      execution_agent.py Reroutes, safety stock, webhooks
      tools/             Tool implementations per agent
    simulation/          Monte Carlo engine (pure Python/NumPy)
      engine.py          Core simulation loop
      network.py         Supply chain graph model
      scenarios.py       Scenario definitions and presets
    seed/                Synthetic data generation
      generator.py       Master orchestrator
      constants.py       Ports, regions, product catalogs
  tests/
    conftest.py          Fixtures (test DB, test client, sample data)
```

## Patterns

### Router Pattern
```python
router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])

@router.get("/", response_model=list[SupplierResponse])
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    return await supplier_service.list_all(db)
```
- Routers handle HTTP concerns only (parsing, status codes, response models)
- Business logic lives in services/
- Never import FastAPI in service modules

### Service Pattern
Services accept an AsyncSession and return domain objects or Pydantic models.

### Schema Pattern
- Request: ThingCreate, ThingUpdate
- Response: ThingResponse
- All schemas use `model_config = ConfigDict(from_attributes=True)`

### Testing
- pytest with pytest-asyncio
- Test database: in-memory SQLite via aiosqlite
- Fixtures in conftest.py: `db_session`, `client`, `sample_supplier`, `sample_risk_event`

### Database
- Table names: snake_case plural
- All models: id (UUID), created_at, updated_at
- Foreign keys: ON DELETE CASCADE for child entities
- JSONB for flexible structured data (agent reasoning, scenario params)

## Running

```bash
python3 -m uvicorn app.main:app --reload --port 8000
python3 -m pytest
python3 -m app.seed.generator
```
