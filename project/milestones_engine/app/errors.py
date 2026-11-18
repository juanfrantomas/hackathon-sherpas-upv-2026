"""Application level errors.

Services raise these; the API layer turns them into the uniform error
envelope.  Every error carries a stable ``code`` so the frontend can react to
it without parsing messages.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for the errors the API reports."""

    code = "INTERNAL_ERROR"
    status_code = 500

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class InvalidCaseIdError(AppError):
    code = "INVALID_CASE_ID"
    status_code = 400


class CaseNotAllowedError(AppError):
    code = "CASE_NOT_ALLOWED"
    status_code = 403


class FinancialPlanNotFoundError(AppError):
    code = "FINANCIAL_PLAN_NOT_FOUND"
    status_code = 404


class McpUnavailableError(AppError):
    code = "MCP_UNAVAILABLE"
    status_code = 503


class AiProviderUnavailableError(AppError):
    code = "AI_PROVIDER_UNAVAILABLE"
    status_code = 503


class AiInvalidResponseError(AppError):
    code = "AI_INVALID_RESPONSE"
    status_code = 502


class AiResponseTooLargeError(AppError):
    code = "AI_RESPONSE_TOO_LARGE"
    status_code = 502


class DatabaseError(AppError):
    code = "DATABASE_ERROR"
    status_code = 500


class MilestoneNotFoundError(AppError):
    code = "MILESTONE_NOT_FOUND"
    status_code = 404


class TaskNotFoundError(AppError):
    code = "TASK_NOT_FOUND"
    status_code = 404


class InvalidStatusTransitionError(AppError):
    code = "INVALID_STATUS_TRANSITION"
    status_code = 409


class InvalidFinancialObservationError(AppError):
    code = "INVALID_FINANCIAL_OBSERVATION"
    status_code = 422


class SyncConflictError(AppError):
    code = "SYNC_CONFLICT"
    status_code = 409


class GenerationDisabledError(AppError):
    code = "GENERATION_DISABLED"
    status_code = 503
