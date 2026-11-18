"""Notification endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import authorize_case, settings_dependency
from app.db.session import DbSession
from app.schemas.checkin import (
    MarkReadResponse,
    NotificationListResponse,
    NotificationResponse,
)
from app.services import notification_service

router = APIRouter(prefix="/api/cases/{case_id}", tags=["notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    case_id: str,
    session: DbSession,
    unread: bool = Query(False),
    type_filter: str | None = Query(None, alias="type"),
    settings=Depends(settings_dependency),
) -> NotificationListResponse:
    """The notices of a case.

    The notices are evaluated before answering, so a pending review is
    reported even when the client never had the application open.
    """
    case_id = authorize_case(case_id, settings)
    notification_service.evaluate(session, case_id)
    session.commit()
    return notification_service.list_notifications(
        session, case_id, unread_only=unread, notification_type=type_filter
    )


@router.post(
    "/notifications/{notification_id}/read", response_model=NotificationResponse
)
async def mark_notification_read(
    case_id: str,
    notification_id: str,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> NotificationResponse:
    """Mark one notice as read."""
    case_id = authorize_case(case_id, settings)
    response = notification_service.mark_read(session, case_id, notification_id)
    session.commit()
    return response


@router.post("/notifications/read-all", response_model=MarkReadResponse)
async def mark_all_read(
    case_id: str,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> MarkReadResponse:
    """Mark every notice of a case as read."""
    case_id = authorize_case(case_id, settings)
    response = notification_service.mark_all_read(session, case_id)
    session.commit()
    return response
