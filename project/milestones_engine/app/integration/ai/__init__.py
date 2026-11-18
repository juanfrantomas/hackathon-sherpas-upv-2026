"""AI integration: provider adapters and the :mod:`ai_service` façade."""

from app.integration.ai.ai_service import AIService, GenerationOutcome
from app.integration.ai.errors import (
    AiAuthError,
    AiError,
    AiInvalidResponseError,
    AiProviderUnavailableError,
    AiResponseTooLargeError,
)
from app.integration.ai.provider import AIProvider, AIResponse

__all__ = [
    "AIProvider",
    "AIResponse",
    "AIService",
    "AiAuthError",
    "AiError",
    "AiInvalidResponseError",
    "AiProviderUnavailableError",
    "AiResponseTooLargeError",
    "GenerationOutcome",
]
