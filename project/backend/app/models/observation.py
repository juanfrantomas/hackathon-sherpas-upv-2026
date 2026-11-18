"""ORM model for a financial observation."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UtcDateTime

if TYPE_CHECKING:  # pragma: no cover - imports for the type checker only
    from app.models.milestone import Milestone


class FinancialObservation(Base):
    """A measured financial value for a milestone.

    Observations from the MCP and from the client are stored independently:
    neither source ever overwrites the other.
    """

    __tablename__ = "financial_observation"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    milestone_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("milestone.id", ondelete="CASCADE"), nullable=False
    )
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    observed_at: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    is_conflicted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, server_default=func.now()
    )

    milestone: Mapped[Milestone] = relationship(back_populates="observations")  # noqa: F821

    __table_args__ = (
        CheckConstraint("source IN ('mcp', 'client')", name="source"),
        CheckConstraint("value >= 0", name="value_non_negative"),
        Index("ix_obs_milestone_metric", "milestone_id", "metric_key", "observed_at"),
        Index("ix_obs_metric_source", "metric_key", "source", "observed_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<FinancialObservation {self.metric_key}={self.value} src={self.source}>"
