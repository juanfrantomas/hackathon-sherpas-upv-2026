"""ORM model for internal notifications."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UtcDateTime


class Notification(Base):
    """An internal notice about a pending check-in or an overdue milestone."""

    __tablename__ = "notification"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("financial_case.id", ondelete="CASCADE"), nullable=False
    )
    milestone_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("milestone.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "type IN ('checkin_pending', 'overdue')", name="type"
        ),
        Index("ix_notification_case_read", "case_id", "read_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Notification {self.type} case={self.case_id}>"
