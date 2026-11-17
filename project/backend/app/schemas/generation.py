"""The contract the milestone generator has to satisfy.

Two things live here:

* the Pydantic models used to *validate* what the model produced, and
* the JSON schema sent to the model as ``response_format``.

The JSON schema is written by hand on purpose: OpenAI-compatible structured
output needs every property to be listed in ``required`` and forbids
``$ref`` indirection in some servers.  ``test_generation_schema.py`` keeps the
schema and the models in sync.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import Category, PlanSection

#: The parts of a plan a recommendation may cite.
PlanPart = Literal["financial-health", "investment-analysis", "persona"]


class SourceRef(BaseModel):
    """A pointer to the plan data a recommendation comes from."""

    model_config = ConfigDict(extra="forbid")

    part: PlanPart
    section: str | None
    json_path: str | None
    quote: str | None = Field(default=None, max_length=300)


class TaskProposal(BaseModel):
    """A step the client has to take to advance a milestone."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=240)
    description: str | None = Field(default=None, max_length=1000)
    is_required: bool
    order: int = Field(ge=0, le=50)


class FinancialTarget(BaseModel):
    """A measurable financial goal attached to a milestone."""

    model_config = ConfigDict(extra="forbid")

    metric_key: str = Field(min_length=3, max_length=64)
    metric_type: str = Field(min_length=2, max_length=32)
    direction: Literal["increase", "decrease"]
    start_value: Decimal
    target_value: Decimal
    unit: str = Field(min_length=1, max_length=32)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    source_ref: SourceRef

    @model_validator(mode="after")
    def _check_values(self) -> FinancialTarget:
        if self.start_value < 0 or self.target_value < 0:
            raise ValueError("financial values cannot be negative")
        if self.start_value == self.target_value:
            raise ValueError("start_value and target_value must differ")
        if self.direction == "increase" and self.target_value < self.start_value:
            raise ValueError("an increasing target cannot be below the starting value")
        if self.direction == "decrease" and self.target_value > self.start_value:
            raise ValueError("a decreasing target cannot be above the starting value")
        if "USD" in self.unit and self.currency is None:
            object.__setattr__(self, "currency", "USD")
        return self


class MilestoneProposal(BaseModel):
    """One milestone proposed by the generator."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=200)
    why: str = Field(min_length=3, max_length=1000)
    action: str = Field(min_length=3, max_length=1000)
    type: Literal["educational", "financial"]
    category: Category
    priority: Literal["high", "medium", "low"]
    section: PlanSection
    anchor_key: str = Field(min_length=3, max_length=128)
    source_refs: list[SourceRef] = Field(min_length=1, max_length=8)
    tasks: list[TaskProposal] = Field(default_factory=list, max_length=12)
    checkin_offset_days: int = Field(ge=1, le=90)
    due_offset_days: int | None = Field(default=None, ge=1, le=1825)
    financial_target: FinancialTarget | None = None

    @field_validator("tasks")
    @classmethod
    def _unique_task_titles(cls, tasks: list[TaskProposal]) -> list[TaskProposal]:
        seen: set[str] = set()
        for task in tasks:
            key = task.title.strip().lower()
            if key in seen:
                raise ValueError("task titles must be unique inside a milestone")
            seen.add(key)
        return tasks

    @model_validator(mode="after")
    def _check_type(self) -> MilestoneProposal:
        if self.type == "financial" and self.financial_target is None:
            # A financial milestone without a measurable target is allowed but
            # flagged downstream; the generator is asked for one.
            pass
        return self


class GenerationResult(BaseModel):
    """The whole answer of the generator."""

    model_config = ConfigDict(extra="forbid")

    milestones: list[MilestoneProposal] = Field(min_length=1, max_length=40)
    #: Milestones that were dropped because they did not hold up.
    dropped_milestones: list[str] = Field(default_factory=list)


CATEGORY_VALUES = [category.value for category in Category]
SECTION_VALUES = [section.value for section in PlanSection]

#: JSON schema handed to the model as ``response_format.json_schema``.
MILESTONE_GENERATION_SCHEMA: dict[str, Any] = {
    "name": "milestone_generation",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["milestones"],
        "properties": {
            "milestones": {
                "type": "array",
                "minItems": 1,
                "maxItems": 40,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "title",
                        "why",
                        "action",
                        "type",
                        "category",
                        "priority",
                        "section",
                        "anchor_key",
                        "source_refs",
                        "tasks",
                        "checkin_offset_days",
                        "due_offset_days",
                        "financial_target",
                    ],
                    "properties": {
                        "title": {"type": "string", "minLength": 3, "maxLength": 200},
                        "why": {"type": "string", "minLength": 3, "maxLength": 1000},
                        "action": {"type": "string", "minLength": 3, "maxLength": 1000},
                        "type": {"type": "string", "enum": ["educational", "financial"]},
                        "category": {"type": "string", "enum": CATEGORY_VALUES},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                        "section": {"type": "string", "enum": SECTION_VALUES},
                        "anchor_key": {"type": "string", "minLength": 3, "maxLength": 128},
                        "source_refs": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["part", "section", "json_path", "quote"],
                                "properties": {
                                    "part": {
                                        "type": "string",
                                        "enum": [
                                            "financial-health",
                                            "investment-analysis",
                                            "persona",
                                        ],
                                    },
                                    "section": {
                                        "type": ["string", "null"],
                                        "maxLength": 64,
                                    },
                                    "json_path": {
                                        "type": ["string", "null"],
                                        "maxLength": 128,
                                    },
                                    "quote": {
                                        "type": ["string", "null"],
                                        "maxLength": 300,
                                    },
                                },
                            },
                        },
                        "tasks": {
                            "type": "array",
                            "maxItems": 12,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["title", "description", "is_required", "order"],
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "minLength": 3,
                                        "maxLength": 240,
                                    },
                                    "description": {
                                        "type": ["string", "null"],
                                        "maxLength": 1000,
                                    },
                                    "is_required": {"type": "boolean"},
                                    "order": {"type": "integer", "minimum": 0, "maximum": 50},
                                },
                            },
                        },
                        "checkin_offset_days": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 90,
                        },
                        "due_offset_days": {
                            "type": ["integer", "null"],
                            "minimum": 1,
                            "maximum": 1825,
                        },
                        "financial_target": {
                            "anyOf": [
                                {"type": "null"},
                                {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": [
                                        "metric_key",
                                        "metric_type",
                                        "direction",
                                        "start_value",
                                        "target_value",
                                        "unit",
                                        "currency",
                                        "source_ref",
                                    ],
                                    "properties": {
                                        "metric_key": {
                                            "type": "string",
                                            "minLength": 3,
                                            "maxLength": 64,
                                        },
                                        "metric_type": {
                                            "type": "string",
                                            "minLength": 2,
                                            "maxLength": 32,
                                        },
                                        "direction": {
                                            "type": "string",
                                            "enum": ["increase", "decrease"],
                                        },
                                        "start_value": {"type": "number"},
                                        "target_value": {"type": "number"},
                                        "unit": {"type": "string", "minLength": 1, "maxLength": 32},
                                        "currency": {
                                            "type": ["string", "null"],
                                            "pattern": "^[A-Z]{3}$",
                                        },
                                        "source_ref": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": [
                                                "part",
                                                "section",
                                                "json_path",
                                                "quote",
                                            ],
                                            "properties": {
                                                "part": {
                                                    "type": "string",
                                                    "enum": [
                                                        "financial-health",
                                                        "investment-analysis",
                                                        "persona",
                                                    ],
                                                },
                                                "section": {
                                                    "type": ["string", "null"],
                                                    "maxLength": 64,
                                                },
                                                "json_path": {
                                                    "type": ["string", "null"],
                                                    "maxLength": 128,
                                                },
                                                "quote": {
                                                    "type": ["string", "null"],
                                                    "maxLength": 300,
                                                },
                                            },
                                        },
                                    },
                                },
                            ]
                        },
                    },
                },
            }
        },
    },
}


def resolve_due_date(
    proposal: MilestoneProposal, *, plan_date: date
) -> date | None:
    """The target date of a milestone, relative to the plan date."""
    if proposal.due_offset_days is None:
        return None
    from datetime import timedelta

    return plan_date + timedelta(days=proposal.due_offset_days)
