"""The FastAPI application.

This is the Financial Milestones backend: it turns a Sherpas financial plan
into personalised milestones, keeps them in step with the plan and lets the
household work through them.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.routers import (
    cases,
    checkins,
    couple,
    dev,
    insights,
    meta,
    milestones,
    notifications,
    observations,
    simulator,
    story,
    sync,
    tasks,
    voice,
)
from app.config import BASE_DIR, get_settings
from app.db.session import get_session_factory
from app.logging_config import setup_logging
from app.notifications.scheduler import build_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop the background notification scheduler."""
    settings = get_settings()
    scheduler = build_scheduler(
        get_session_factory(),
        interval_seconds=settings.notification_interval_seconds,
    )
    app.state.scheduler = scheduler
    await scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


def create_app() -> FastAPI:
    """Build the application."""
    settings = get_settings()
    setup_logging(
        settings.log_level,
        secrets=[settings.mcp_token, settings.ai_api_key],
    )

    app = FastAPI(
        title="Sherpas Financial Milestones",
        description=(
            "Personalised financial milestones generated from a Sherpas financial plan."
        ),
        version=__version__,
        lifespan=lifespan,
    )

    origins = settings.cors_origin_list
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "Authorization"],
        )

    register_exception_handlers(app)

    # The audio of the mentor, served from the cache of the speech synthesis.
    cache_dir = Path(settings.tts_cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = (BASE_DIR / cache_dir).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    app.mount(settings.audio_url_prefix, StaticFiles(directory=cache_dir), name="audio")

    app.include_router(meta.router)
    app.include_router(cases.router)
    app.include_router(milestones.router)
    app.include_router(tasks.router)
    app.include_router(observations.router)
    app.include_router(checkins.router)
    app.include_router(notifications.router)
    app.include_router(sync.router)
    app.include_router(voice.router)
    app.include_router(simulator.router)
    app.include_router(insights.router)
    app.include_router(couple.router)
    app.include_router(story.router)

    # The console of the pillars only exists while developing.
    if settings.environment != "production":
        app.include_router(dev.router)

    return app


app = create_app()
