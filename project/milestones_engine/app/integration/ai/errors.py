"""Errors raised by the AI integration."""

from __future__ import annotations


class AiError(Exception):
    """Base class for AI failures."""

    code = "AI_ERROR"


class AiProviderUnavailableError(AiError):
    """The provider could not be reached, or refused the request."""

    code = "AI_PROVIDER_UNAVAILABLE"


class AiInvalidResponseError(AiError):
    """The provider answered something that does not satisfy the contract."""

    code = "AI_INVALID_RESPONSE"

    def __init__(
        self, message: str, *, error_summary: str = "", raw: str = ""
    ) -> None:
        super().__init__(message)
        self.error_summary = error_summary
        self.raw = raw


class AiResponseTooLargeError(AiError):
    """The provider answered with a truncated payload."""

    code = "AI_RESPONSE_TOO_LARGE"


class AiAuthError(AiError):
    """The provider rejected our credentials."""

    code = "AI_PROVIDER_UNAVAILABLE"
