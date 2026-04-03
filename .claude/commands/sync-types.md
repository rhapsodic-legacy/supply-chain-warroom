---
description: Regenerate frontend TypeScript types from backend Pydantic schemas.
---

Synchronise frontend TypeScript types with backend Pydantic response schemas.

## Steps

1. Read all Pydantic response schemas in backend/app/schemas/
2. Read the current frontend/src/types/api.ts
3. For each Pydantic model, generate a TypeScript interface:
   - str → string
   - int/float → number
   - bool → boolean
   - datetime → string (ISO 8601)
   - list[X] → X[]
   - Optional[X] → X | null
   - UUID → string
   - Enum → union of string literals
   - dict/JSONB → Record<string, unknown>
4. Write the updated frontend/src/types/api.ts
5. If frontend is set up, run `cd frontend && npx tsc --noEmit` to verify
6. Print summary of types added/updated/removed
