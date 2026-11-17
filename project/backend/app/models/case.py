"""ORM model for a Sherpas financial case."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UtcDateTime

if TYPE_CHECKING:  # pragma: no cover - imports for the type checker only
    from app.models.generation import AIGeneration
    from app.models.milestone import Milestone
    from app.models.sync_state import SyncState


class FinancialCase(Base):
    """A household's financial case as served by the MCP."""

    __tablename__ = "financial_case"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    household_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    data_source: Mapped[str] = mapped_column(String(16), nullable=False, default="mcp")
    plan_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, server_default=func.now()
    )

    milestones: Mapped[list[Milestone]] = relationship(  # noqa: F821
        back_populates="case", cascade="all, delete-orphan"
    )
    sync_state: Mapped[SyncState | None] = relationship(  # noqa: F821
        back_populates="case", cascade="all, delete-orphan", uselist=False
    )
    generations: Mapped[list[AIGeneration]] = relationship(  # noqa: F821
        back_populates="case", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<FinancialCase {self.id} source={self.data_source}>"
