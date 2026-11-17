"""ORM model for the high fives a couple sends to each other."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UtcDateTime


class FamilyHighFive(Base):
    """A high five between the two members of a household.

    The gamified path is gone, but the wall of high fives stays: it is the
    one piece of the couple mode that the household writes itself.
    """

    __tablename__ = "family_high_five"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("financial_case.id", ondelete="CASCADE"), nullable=False
    )
    from_member: Mapped[str] = mapped_column(String(64), nullable=False)
    to_member: Mapped[str] = mapped_column(String(64), nullable=False)
    milestone_title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_high_five_case_created", "case_id", "created_at"),)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<FamilyHighFive {self.from_member} -> {self.to_member}>"
