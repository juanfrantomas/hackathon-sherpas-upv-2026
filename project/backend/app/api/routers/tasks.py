"""Task endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import authorize_case, settings_dependency
from app.db.session import DbSession
from app.schemas.milestone import (
    MilestoneResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskUpdateRequest,
)
from app.services import milestone_service, task_service

router = APIRouter(prefix="/api/cases/{case_id}", tags=["tasks"])


@router.get("/milestones/{milestone_id}/tasks", response_model=list[TaskResponse])
async def list_tasks(
    case_id: str,
    milestone_id: str,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> list[TaskResponse]:
    """The tasks of a milestone."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.get_milestone(session, case_id, milestone_id)
    tasks = task_service.list_tasks(session, milestone.id)
    return [
        TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            order=task.order_index,
            is_required=task.is_required,
            status=task.status,
            origin=task.origin,
            completed_at=task.completed_at,
        )
        for task in tasks
    ]


@router.post(
    "/milestones/{milestone_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    case_id: str,
    milestone_id: str,
    payload: TaskCreateRequest,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> TaskResponse:
    """Add a task to a milestone."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.get_milestone(session, case_id, milestone_id)
    task = task_service.create_task(session, milestone, payload)
    session.commit()
    session.refresh(task)
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        order=task.order_index,
        is_required=task.is_required,
        status=task.status,
        origin=task.origin,
        completed_at=task.completed_at,
    )


@router.patch(
    "/milestones/{milestone_id}/tasks/{task_id}", response_model=MilestoneResponse
)
async def update_task(
    case_id: str,
    milestone_id: str,
    task_id: str,
    payload: TaskUpdateRequest,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> MilestoneResponse:
    """Complete, uncomplete or edit a task.

    The answer is the milestone, because completing a task can change the
    progress and even close an educational milestone.
    """
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.get_milestone(session, case_id, milestone_id)
    task_service.update_task(session, milestone, task_id, payload)
    session.commit()
    session.refresh(milestone)
    return milestone_service.to_response(milestone)


@router.delete(
    "/milestones/{milestone_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    case_id: str,
    milestone_id: str,
    task_id: str,
    session: DbSession,
    settings=Depends(settings_dependency),
) -> Response:
    """Remove a task."""
    case_id = authorize_case(case_id, settings)
    milestone = milestone_service.get_milestone(session, case_id, milestone_id)
    task_service.delete_task(session, milestone, task_id)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
