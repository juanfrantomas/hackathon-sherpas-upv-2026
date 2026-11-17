"""API schemas for financial observations and progress."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ObservationCreateRequest(BaseModel):
    """A value the client declares for a milestone."""

    metric_key: str = Field(min_length=3, max_length=64)
    metric_type: str = Field(min_length=2, max_length=32)
    value: Decimal = Field(description="The declared value")
    unit: str = Field(min_length=1, max_length=32)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    observed_at: date | None = Field(default=None)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("value")
    @classmethod
    def _non_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("a financial observation cannot be negative")
        return value

    @field_validator("currency")
    @classmethod
    def _usd_implies_currency(cls, value: str | None, info) -> str | None:
        unit = info.data.get("unit") or ""
        if "USD" in unit and value is None:
            return "USD"
        return value


class ObservationResponse(BaseModel):
    """A stored observation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    milestone_id: str
    metric_key: str
    metric_type: str
    value: Decimal
    unit: str
    currency: str | None = None
    observed_at: date
    source: str
    is_conflicted: bool = False
    note: str | None = None
    recorded_at: datetime


class ObservationListResponse(BaseModel):
    """The observations of a milestone, grouped by source."""

    observations: list[ObservationResponse]
    conflict: dict | None = None


class FinancialProgressResponse(BaseModel):
    """The financial progress of a milestone."""

    milestone_id: str
    progress: float | None = None
    state: str
    direction: str | None = None
    start_value: Decimal | None = None
    target_value: Decimal | None = None
    used_source: str | None = None
    sources: list[ObservationResponse] = Field(default_factory=list)
    conflict: dict | None = None
    metric_key: str | None = None
    unit: str | None = None
    currency: str | None = None
