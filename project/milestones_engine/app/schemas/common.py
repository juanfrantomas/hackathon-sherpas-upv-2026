"""Shared API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    """The body of an error response."""

    code: str = Field(description="Machine readable error code")
    message: str = Field(description="Human readable explanation")
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """The envelope every error uses."""

    error: ErrorBody


class MilestoneListMeta(BaseModel):
    """Context about the listing itself."""

    case_id: str
    count: int
    stale: bool = False
    stale_reason: str | None = None
    data_source: str | None = None
    last_successful_sync_at: datetime | None = None


class ProgressSummary(BaseModel):
    """Aggregated progress for a case."""

    milestones_total: int
    completed: int
    in_progress: int
    not_started: int
    on_hold: int
    cancelled: int
    overdue: int
    checkins_pending: int
    task_progress_average: int | None = None
    financial_progress_average: float | None = None
