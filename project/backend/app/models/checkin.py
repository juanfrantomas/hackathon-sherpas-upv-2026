"""ORM model for a scheduled milestone review (check-in)."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UtcDateTime

if TYPE_CHECKING:  # pragma: no cover - imports for the type checker only
    from app.models.milestone import Milestone


class MilestoneCheckin(Base):
    """A review scheduled for a milestone.

    ``scheduled_date`` is the date the review was *planned* for and is kept
    even after the review happens; ``effective_date`` is when it actually
    took place.
    """

    __tablename__ = "milestone_checkin"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    milestone_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("milestone.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="scheduled")
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, server_default=func.now()
    )

    milestone: Mapped[Milestone] = relationship(back_populates="checkins")  # noqa: F821

    __table_args__ = (
        CheckConstraint("status IN ('scheduled', 'completed', 'missed')", name="status"),
        Index("ix_checkin_milestone_date", "milestone_id", "scheduled_date"),
        Index("uq_checkin_milestone_date", "milestone_id", "scheduled_date", unique=True),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<MilestoneCheckin {self.milestone_id} {self.scheduled_date} {self.status}>"
