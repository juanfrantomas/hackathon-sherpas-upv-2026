"""ORM model for a milestone task."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UtcDateTime

if TYPE_CHECKING:  # pragma: no cover - imports for the type checker only
    from app.models.milestone import Milestone


class MilestoneTask(Base):
    """A concrete step the client has to take to advance a milestone."""

    __tablename__ = "milestone_task"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    milestone_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("milestone.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    match_key: Mapped[str] = mapped_column(String(64), nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="ai")
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    milestone: Mapped[Milestone] = relationship(back_populates="tasks")  # noqa: F821

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed')", name="status"),
        CheckConstraint("origin IN ('ai', 'client')", name="origin"),
        CheckConstraint("order_index >= 0", name="order_index"),
        Index("ix_task_milestone_order", "milestone_id", "order_index"),
        Index("ix_task_match", "milestone_id", "match_key"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<MilestoneTask {self.id} {self.status}>"
