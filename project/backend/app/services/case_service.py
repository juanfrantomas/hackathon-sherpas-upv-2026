"""Case level use cases: resolving the plan and keeping the case record."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.cases import normalize_case_id
from app.errors import (
    FinancialPlanNotFoundError,
    InvalidCaseIdError,
    McpUnavailableError,
)
from app.integration.mcp.case_source import CaseSource
from app.integration.mcp.digest import PlanDigest
from app.integration.mcp.errors import (
    McpAuthError,
    McpCaseNotFoundError,
    McpError,
    McpSectionNotFoundError,
)
from app.integration.mcp.errors import (
    McpUnavailableError as McpUnavailable,
)
from app.logging_config import get_logger
from app.models.case import FinancialCase
from app.repositories import case_repository

logger = get_logger(__name__)

def validate_case_id(case_id: str) -> str:
    """Reject a malformed case identifier before anything else happens.

    The short alias of a household is accepted and resolved to its official
    slug.
    """
    cleaned = (case_id or "").strip()
    if not cleaned:
        raise InvalidCaseIdError("The case identifier is empty")
    if len(cleaned) > 64:
        raise InvalidCaseIdError("The case identifier is too long")
    if not all(char.isalnum() or char in "-_" for char in cleaned):
        raise InvalidCaseIdError(
            "The case identifier may only contain letters, digits, '-' and '_'",
            details={"case_id": cleaned},
        )
    return normalize_case_id(cleaned)


async def get_digest(case_source: CaseSource, case_id: str) -> PlanDigest:
    """Fetch and normalise the plan of a case."""
    cleaned = validate_case_id(case_id)
    try:
        digest = await case_source.get_digest(cleaned)
    except McpCaseNotFoundError as exc:
        raise FinancialPlanNotFoundError(
            "This financial plan is not available", details={"case_id": cleaned}
        ) from exc
    except McpAuthError as exc:
        raise McpUnavailableError(
            "The case service rejected our credentials; refresh the MCP token",
            details={"case_id": cleaned},
        ) from exc
    except McpSectionNotFoundError as exc:
        raise FinancialPlanNotFoundError(
            "This financial plan is not available", details={"case_id": cleaned}
        ) from exc
    except McpUnavailable as exc:
        raise McpUnavailableError(
            "The case service is not available right now",
            details={"case_id": cleaned},
        ) from exc
    except McpError as exc:
        logger.warning("Unexpected MCP failure for %s: %s", cleaned, exc.code)
        raise McpUnavailableError(
            "The case service is not available right now",
            details={"case_id": cleaned},
        ) from exc
    return digest


def ensure_case(
    session: Session, case_id: str, digest: PlanDigest, *, data_source: str = "mcp"
) -> FinancialCase:
    """Create or refresh the stored case."""
    return case_repository.get_or_create_case(
        session,
        case_id,
        household_name=digest.household_name,
        data_source=data_source,
        plan_language=digest.language,
    )


def ensure_case_row(session: Session, case_id: str) -> FinancialCase:
    """Make sure the case exists before anything refers to it.

    The synchronisation state and the notifications point at the case, so the
    row has to be there before they are written.
    """
    return case_repository.get_or_create_case(session, case_id)
