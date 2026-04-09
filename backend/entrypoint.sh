#!/bin/sh
set -e

echo "==> Waiting for database..."
# Simple TCP wait — no extra dependencies
for i in $(seq 1 30); do
  if python3 -c "
import socket, os
url = os.environ.get('DATABASE_URL', '')
if 'asyncpg' in url:
    host = url.split('@')[1].split(':')[0] if '@' in url else 'localhost'
    port = int(url.split(':')[-1].split('/')[0]) if url.count(':') > 2 else 5432
    s = socket.create_connection((host, port), timeout=2)
    s.close()
    exit(0)
exit(0)
" 2>/dev/null; then
    echo "==> Database is ready."
    break
  fi
  echo "    Waiting... ($i/30)"
  sleep 1
done

echo "==> Checking if database needs seeding..."
python3 -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def check_and_seed():
    engine = create_async_engine(settings.database_url, echo=False)

    # Create tables
    from app.database import Base
    import app.models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Check if data exists
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT COUNT(*) FROM suppliers'))
        count = result.scalar()

    await engine.dispose()

    if count == 0:
        print('==> No data found. Seeding database...')
        from app.seed.generator import seed_database
        await seed_database()
    else:
        print(f'==> Database already has {count} suppliers. Skipping seed.')

asyncio.run(check_and_seed())
"

echo "==> Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
