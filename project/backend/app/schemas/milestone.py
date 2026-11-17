"""API schemas for milestones and tasks.

``MilestoneResponse`` keeps the legacy contract of the React client intact
(``id``, ``title``, ``why``, ``action``, ``section``, ``status``, ``checkin``)
and adds the new fields after it.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.domain.enums import MilestoneStatus
from app.schemas.common import MilestoneListMeta


class SourceRefOut(BaseModel):
    """A pointer back to the plan data."""

    model_config = ConfigDict(from_attributes=True)

    part: str
    section: str | None = None
    json_path: str | None = None
    quote: str | None = None


class TaskResponse(BaseModel):
    """A task of a milestone."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    title: str
    description: str | None = None
    order: int = Field(default=0, validation_alias=AliasChoices("order", "order_index"))
    is_required: bool
    status: str
    origin: str = "ai"
    completed_at: datetime | None = None


class MilestoneResponse(BaseModel):
    """A milestone, in the shape the frontend consumes."""

    model_config = ConfigDict(from_attributes=True)

    # --- legacy contract -------------------------------------------------
    id: str
    title: str
    why: str
    action: str
    section: str
    status: str
    checkin: str | None = None

    # --- new fields ------------------------------------------------------
    case_id: str
    category: str
    type: str
    priority: str
    tasks: list[TaskResponse] = Field(default_factory=list)
    task_progress: int | None = None
    financial_progress: float | None = None
    financial_progress_state: str = "not_quantifiable"
    financial_metric_key: str | None = None
    financial_direction: str | None = None
    financial_start_value: Decimal | None = None
    financial_target_value: Decimal | None = None
    financial_unit: str | None = None
    financial_currency: str | None = None
    due_date: date | None = None
    checkin_pending: bool = False
    checkin_date: date | None = None
    overdue: bool = False
    source: list[SourceRefOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    last_reviewed_at: datetime | None = None


class MilestoneListResponse(BaseModel):
    """The listing, compatible with the current frontend contract."""

    milestones: list[MilestoneResponse]
    meta: MilestoneListMeta | None = None
    grouped_by_category: dict[str, list[MilestoneResponse]] | None = None


class StatusUpdateRequest(BaseModel):
    """A client request to move a milestone to another status."""

    status: MilestoneStatus


class CompleteMilestoneRequest(BaseModel):
    """The explicit confirmation that closes a milestone."""

    confirmed: bool = Field(
        description="Must be true: completing a milestone is a client statement"
    )
    note: str | None = Field(default=None, max_length=1000)


class TaskCreateRequest(BaseModel):
    """A task added by the client."""

    title: str = Field(min_length=3, max_length=240)
    description: str | None = Field(default=None, max_length=1000)
    is_required: bool = True
    order: int | None = Field(default=None, ge=0, le=50)


class TaskUpdateRequest(BaseModel):
    """A change to a task (completing it, uncompleting it or editing it)."""

    status: str | None = Field(default=None, pattern=r"^(pending|completed)$")
    title: str | None = Field(default=None, min_length=3, max_length=240)
    description: str | None = Field(default=None, max_length=1000)
    is_required: bool | None = None


class TaskProgressResponse(BaseModel):
    """The operational progress of a milestone."""

    milestone_id: str
    task_progress: int | None = None
    required_tasks: int = 0
    completed_required_tasks: int = 0
    optional_tasks: int = 0
    completed_optional_tasks: int = 0
    auto_completable: bool = False


class PriorityInfo(BaseModel):
    """One entry of the category catalogue."""

    id: str
    label: str
    default_section: str
