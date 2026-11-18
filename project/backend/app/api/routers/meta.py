"""Catalogue and health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import settings_dependency
from app.db.session import get_engine
from app.domain.enums import CATEGORY_DEFAULT_SECTION, Category, PlanSection
from app.schemas.milestone import PriorityInfo

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
async def health() -> dict:
    """Is the service up and is the database reachable?"""
    database = "ok"
    try:
        with get_engine().connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    except Exception:  # pragma: no cover - only on a broken database
        database = "error"
    return {"status": "ok" if database == "ok" else "degraded", "database": database}


@router.get("/categories")
async def categories() -> dict:
    """The closed catalogue of milestone categories."""
    return {
        "categories": [
            PriorityInfo(
                id=category.slug,
                label=category.value,
                default_section=CATEGORY_DEFAULT_SECTION[category].value,
            )
            for category in Category
        ]
    }


@router.get("/sections")
async def sections() -> dict:
    """The sections of a Sherpas plan."""
    return {
        "sections": [
            {"id": section.value, "label": section.label} for section in PlanSection
        ]
    }


@router.get("/environment")
async def environment(settings=Depends(settings_dependency)) -> dict:
    """A small summary of how this instance is configured."""
    return {
        "environment": settings.environment,
        "case_source": settings.case_source,
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "allowed_cases": len(settings.allowed_case_id_set),
        "auto_generate": settings.auto_generate_on_first_access,
    }
