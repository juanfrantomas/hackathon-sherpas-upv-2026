"""ORM model for a milestone."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import (
    Category,
    FinancialDirection,
    FinancialProgressState,
    MilestoneStatus,
    MilestoneType,
    PlanSection,
    Priority,
)
from app.models.base import Base, UtcDateTime

if TYPE_CHECKING:  # pragma: no cover - imports for the type checker only
    from app.models.case import FinancialCase
    from app.models.checkin import MilestoneCheckin
    from app.models.observation import FinancialObservation
    from app.models.task import MilestoneTask

CATEGORY_VALUES = ", ".join(f"'{c.value}'" for c in Category)
SECTION_VALUES = ", ".join(f"'{s.value}'" for s in PlanSection)
STATUS_VALUES = ", ".join(f"'{s.value}'" for s in MilestoneStatus)
TYPE_VALUES = ", ".join(f"'{t.value}'" for t in MilestoneType)
PRIORITY_VALUES = ", ".join(f"'{p.value}'" for p in Priority)
DIRECTION_VALUES = ", ".join(f"'{d.value}'" for d in FinancialDirection)
PROGRESS_STATE_VALUES = ", ".join(f"'{s.value}'" for s in FinancialProgressState)


class Milestone(Base):
    """A personalised step derived from the client's financial plan."""

    __tablename__ = "milestone"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("financial_case.id", ondelete="CASCADE"), nullable=False
    )
    stable_key: Mapped[str] = mapped_column(String(128), nullable=False)

    # --- content (legacy contract: title / why / action / section) ---------
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    why: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    section: Mapped[str] = mapped_column(String(16), nullable=False)

    # --- classification ---------------------------------------------------
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[str] = mapped_column(String(8), nullable=False)
    priority_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # --- lifecycle --------------------------------------------------------
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="not_started")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    checkin_next_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    checkin_pending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checkin_interval_months: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    overdue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- progress ---------------------------------------------------------
    task_progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    financial_progress: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    financial_progress_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default="not_quantifiable"
    )

    # --- financial target -------------------------------------------------
    financial_metric_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    financial_direction: Mapped[str | None] = mapped_column(String(8), nullable=True)
    financial_start_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    financial_target_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    financial_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    financial_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # --- provenance -------------------------------------------------------
    source_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    anchor_kind: Mapped[str | None] = mapped_column(String(24), nullable=True)
    anchor_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- audit timestamps (only what the agreed features need) -----------
    last_reviewed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    ai_generation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_generation.id", ondelete="SET NULL"), nullable=True
    )

    case: Mapped[FinancialCase] = relationship(back_populates="milestones")  # noqa: F821
    tasks: Mapped[list[MilestoneTask]] = relationship(  # noqa: F821
        back_populates="milestone",
        cascade="all, delete-orphan",
        order_by="MilestoneTask.order_index",
    )
    observations: Mapped[list[FinancialObservation]] = relationship(  # noqa: F821
        back_populates="milestone", cascade="all, delete-orphan"
    )
    checkins: Mapped[list[MilestoneCheckin]] = relationship(  # noqa: F821
        back_populates="milestone", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(f"category IN ({CATEGORY_VALUES})", name="category"),
        CheckConstraint(f"section IN ({SECTION_VALUES})", name="section"),
        CheckConstraint(f"status IN ({STATUS_VALUES})", name="status"),
        CheckConstraint(f"type IN ({TYPE_VALUES})", name="type"),
        CheckConstraint(f"priority IN ({PRIORITY_VALUES})", name="priority"),
        CheckConstraint(
            f"financial_direction IS NULL OR financial_direction IN ({DIRECTION_VALUES})",
            name="financial_direction",
        ),
        CheckConstraint(
            f"financial_progress_state IN ({PROGRESS_STATE_VALUES})",
            name="financial_progress_state",
        ),
        CheckConstraint(
            "task_progress IS NULL OR (task_progress >= 0 AND task_progress <= 100)",
            name="task_progress_range",
        ),
        CheckConstraint(
            "financial_progress IS NULL OR (financial_progress >= 0 AND financial_progress <= 100)",
            name="financial_progress_range",
        ),
        CheckConstraint("priority_rank >= 0", name="priority_rank"),
        Index("uq_milestone_case_stable", "case_id", "stable_key", unique=True),
        Index("ix_milestone_case_status", "case_id", "status"),
        Index("ix_milestone_case_category", "case_id", "category"),
        Index("ix_milestone_case_priority", "case_id", "priority_rank"),
        Index("ix_milestone_checkin", "status", "checkin_next_date"),
        Index("ix_milestone_due", "status", "due_date"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Milestone {self.id} {self.category} {self.status}>"
