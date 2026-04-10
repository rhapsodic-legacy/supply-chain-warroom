"""Demo mode endpoints — start, cancel, and reset the guided walkthrough."""

from fastapi import APIRouter, BackgroundTasks

from app.database import async_session_factory
from app.services import demo_service

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


async def _run_demo_background() -> None:
    """Run the demo with its own DB session (background task)."""
    async with async_session_factory() as session:
        try:
            await demo_service.run_demo(session)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Background demo failed")


@router.post("/run")
async def start_demo(background_tasks: BackgroundTasks):
    """Start the guided demo sequence as a background task."""
    background_tasks.add_task(_run_demo_background)
    return {"status": "started"}


@router.post("/cancel")
async def cancel_demo():
    """Cancel the currently running demo."""
    result = await demo_service.cancel_demo()
    return result
