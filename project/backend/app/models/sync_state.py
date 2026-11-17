"""ORM model for the synchronisation state of a case."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UtcDateTime

if TYPE_CHECKING:  # pragma: no cover - imports for the type checker only
    from app.models.case import FinancialCase


class SyncState(Base):
    """Tracks the last synchronisation attempt for a case."""

    __tablename__ = "sync_state"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("financial_case.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="idle")
    trigger: Mapped[str | None] = mapped_column(String(16), nullable=True)
    plan_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    milestones_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    milestones_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    milestones_kept: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_model: Mapped[str | None] = mapped_column(String(64), nullable=True)

    case: Mapped[FinancialCase] = relationship(back_populates="sync_state")  # noqa: F821

    __table_args__ = (
        CheckConstraint(
            "status IN ('idle', 'running', 'success', 'error')", name="status"
        ),
        CheckConstraint(
            "trigger IS NULL OR trigger IN ('first_access', 'interval', 'manual')",
            name="trigger",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<SyncState {self.case_id} {self.status}>"
