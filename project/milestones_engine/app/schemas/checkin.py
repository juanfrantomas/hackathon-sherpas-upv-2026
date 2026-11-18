"""API schemas for check-ins and notifications."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckinResponse(BaseModel):
    """One scheduled review."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    milestone_id: str
    title: str | None = None
    scheduled_date: date
    effective_date: date | None = None
    status: str
    completed_at: datetime | None = None
    pending: bool = False
    note: str | None = None


class CheckinListResponse(BaseModel):
    """The reviews of a case."""

    checkins: list[CheckinResponse]


class MilestoneCheckinResponse(BaseModel):
    """The review schedule of one milestone."""

    milestone_id: str
    next_review: date | None = None
    next_review_display: str | None = None
    pending: bool = False
    overdue: bool = False
    last_reviewed_at: datetime | None = None
    history: list[CheckinResponse] = Field(default_factory=list)


class ReviewCompletedRequest(BaseModel):
    """The client reports that a review happened."""

    effective_date: date | None = Field(
        default=None, description="When the review actually took place"
    )
    note: str | None = Field(default=None, max_length=1000)


class ReviewCompletedResponse(BaseModel):
    """The result of registering a review."""

    checkin: CheckinResponse
    next_review: date | None = None
    next_review_display: str | None = None
    pending: bool = False


class NotificationResponse(BaseModel):
    """An internal notice."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    milestone_id: str | None = None
    type: str
    title: str
    body: str
    reference_date: date | None = None
    created_at: datetime
    read_at: datetime | None = None


class NotificationListResponse(BaseModel):
    """The notices of a case."""

    notifications: list[NotificationResponse]
    unread_count: int = 0


class MarkReadResponse(BaseModel):
    """The result of marking notices as read."""

    read: int = 0
