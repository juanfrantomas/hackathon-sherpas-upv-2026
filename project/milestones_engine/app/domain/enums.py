"""Domain enumerations.

These values are part of the API contract and of the persistence layer.  They
live in ``app.domain`` because they carry no infrastructure dependency.
"""

from __future__ import annotations

from enum import StrEnum


class MilestoneStatus(StrEnum):
    """Lifecycle of a milestone.  Only the client changes these."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {MilestoneStatus.COMPLETED, MilestoneStatus.CANCELLED}


class MilestoneType(StrEnum):
    """Educational milestones are about understanding; financial ones about results."""

    EDUCATIONAL = "educational"
    FINANCIAL = "financial"


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        return {"high": 0, "medium": 1, "low": 2}[self.value]


class Category(StrEnum):
    """Closed catalogue of milestone categories."""

    DEBT = "Debt"
    SAVINGS = "Savings"
    INVESTMENTS = "Investments"
    RETIREMENT = "Retirement"
    INSURANCE_AND_PROTECTION = "Insurance & Protection"
    EDUCATION = "Education"
    TAX_PLANNING = "Tax Planning"
    HOUSING = "Housing"
    ESTATE_PLANNING = "Estate Planning"
    FINANCIAL_PLANNING = "Financial Planning"
    OTHER = "Other"

    @property
    def slug(self) -> str:
        return {
            Category.DEBT: "debt",
            Category.SAVINGS: "savings",
            Category.INVESTMENTS: "investments",
            Category.RETIREMENT: "retirement",
            Category.INSURANCE_AND_PROTECTION: "insurance_and_protection",
            Category.EDUCATION: "education",
            Category.TAX_PLANNING: "tax_planning",
            Category.HOUSING: "housing",
            Category.ESTATE_PLANNING: "estate_planning",
            Category.FINANCIAL_PLANNING: "financial_planning",
            Category.OTHER: "other",
        }[self]


class PlanSection(StrEnum):
    """The six sections of a Sherpas plan, as rendered by the React client."""

    SUMMARY = "summary"
    RETIREMENT = "retirement"
    ASSETS = "assets"
    DEBT = "debt"
    SAVINGS = "savings"
    PROTECTION = "protection"

    @property
    def label(self) -> str:
        return {
            PlanSection.SUMMARY: "Summary",
            PlanSection.RETIREMENT: "Retirement & Goals",
            PlanSection.ASSETS: "Assets & Investments",
            PlanSection.DEBT: "Debt management",
            PlanSection.SAVINGS: "Savings & Expenses",
            PlanSection.PROTECTION: "Insurance & Protection",
        }[self]


class ObservationSource(StrEnum):
    """Where a financial observation comes from.  Both are kept independently."""

    MCP = "mcp"
    CLIENT = "client"


class MetricType(StrEnum):
    BALANCE = "balance"
    COVERAGE = "coverage"
    SAVINGS = "savings"
    CONTRIBUTION = "contribution"
    RATIO = "ratio"
    GAP = "gap"


class FinancialDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"


class FinancialProgressState(StrEnum):
    NOT_QUANTIFIABLE = "not_quantifiable"
    ON_TRACK = "on_track"
    ACHIEVED = "achieved"
    REGRESSED = "regressed"
    CONFLICTING = "conflicting"


class TaskStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class TaskOrigin(StrEnum):
    AI = "ai"
    CLIENT = "client"


class CheckinStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    MISSED = "missed"


class NotificationType(StrEnum):
    CHECKIN_PENDING = "checkin_pending"
    OVERDUE = "overdue"


class SyncStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class SyncTrigger(StrEnum):
    FIRST_ACCESS = "first_access"
    INTERVAL = "interval"
    MANUAL = "manual"


#: Categories the AI may pick, and the plan section each one maps to by default.
CATEGORY_DEFAULT_SECTION: dict[Category, PlanSection] = {
    Category.DEBT: PlanSection.DEBT,
    Category.SAVINGS: PlanSection.SAVINGS,
    Category.INVESTMENTS: PlanSection.ASSETS,
    Category.RETIREMENT: PlanSection.RETIREMENT,
    Category.INSURANCE_AND_PROTECTION: PlanSection.PROTECTION,
    Category.EDUCATION: PlanSection.RETIREMENT,
    Category.TAX_PLANNING: PlanSection.SUMMARY,
    Category.HOUSING: PlanSection.SUMMARY,
    Category.ESTATE_PLANNING: PlanSection.SUMMARY,
    Category.FINANCIAL_PLANNING: PlanSection.SUMMARY,
    Category.OTHER: PlanSection.SUMMARY,
}

#: Status transitions the client is allowed to request.
VALID_STATUS_TRANSITIONS: dict[MilestoneStatus, set[MilestoneStatus]] = {
    MilestoneStatus.NOT_STARTED: {
        MilestoneStatus.IN_PROGRESS,
        MilestoneStatus.ON_HOLD,
        MilestoneStatus.CANCELLED,
    },
    MilestoneStatus.IN_PROGRESS: {
        MilestoneStatus.COMPLETED,
        MilestoneStatus.ON_HOLD,
        MilestoneStatus.CANCELLED,
    },
    MilestoneStatus.ON_HOLD: {MilestoneStatus.IN_PROGRESS, MilestoneStatus.CANCELLED},
    MilestoneStatus.COMPLETED: {MilestoneStatus.IN_PROGRESS},
    MilestoneStatus.CANCELLED: {MilestoneStatus.NOT_STARTED},
}
