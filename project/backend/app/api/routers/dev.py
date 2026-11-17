"""The development console.

It is the interactive interface of the five pillars: the decision laboratory,
the proactive mentor, the couple mode and the financial story.  It is served
only when the instance is not in production.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import BASE_DIR
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["development"])

CONSOLE_PATH = BASE_DIR / "app" / "static" / "dev-console.html"


@router.get("/dev/console", include_in_schema=False)
async def dev_console() -> FileResponse:
    """The interactive console of the pillars."""
    if not CONSOLE_PATH.is_file():
        raise HTTPException(status_code=404, detail="The console is not available")
    return FileResponse(CONSOLE_PATH, media_type="text/html")
