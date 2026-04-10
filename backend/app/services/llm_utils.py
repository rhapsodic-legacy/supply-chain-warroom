"""Shared LLM utilities — three-tier fallback: Claude → Gemma (Ollama) → template.

Used by demo_service, executive_summary_service, and any future service
that needs LLM generation with graceful degradation.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
GEMMA_MODEL = os.environ.get("GEMMA_DEMO_MODEL", "gemma4:e2b")


async def ollama_available() -> bool:
    """Check whether Ollama is running and has a Gemma model pulled."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code != 200:
                return False
            models = resp.json().get("models", [])
            return any(m.get("name", "").startswith(GEMMA_MODEL.split(":")[0]) for m in models)
    except Exception:
        return False


async def ollama_generate(prompt: str, max_tokens: int = 400) -> str:
    """Generate text from the local Ollama model."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": GEMMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.7},
            },
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()


async def resolve_llm_tier() -> str:
    """Determine which LLM backend to use: claude → gemma → template."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    if await ollama_available():
        return "gemma"
    return "template"
