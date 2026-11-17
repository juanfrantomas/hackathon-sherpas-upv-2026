"""``ai_service.py`` - the façade the application uses to talk to an AI.

Everything provider specific lives behind :class:`AIProvider`.  The service
owns the parts of the contract that belong to the *business*: what the model
is asked, how the answer is validated, what happens when the answer is
invalid and which rules from the plan are enforced on the result.

No import of ``openai`` (or of any other vendor SDK) happens below this
module's provider adapters.
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from app.domain.enums import Category, PlanSection
from app.domain.reconciliation import title_similarity
from app.integration.ai.errors import (
    AiInvalidResponseError,
    AiProviderUnavailableError,
)
from app.integration.ai.prompts import (
    PROMPT_VERSION,
    build_system_prompt,
    build_user_prompt,
)
from app.integration.ai.provider import AIProvider
from app.integration.mcp.digest import PlanDigest
from app.logging_config import get_logger
from app.schemas.ai import ChatResponse
from app.schemas.generation import (
    MILESTONE_GENERATION_SCHEMA,
    GenerationResult,
    MilestoneProposal,
)

logger = get_logger(__name__)

#: Two proposals with the same anchor (or a very similar title) are the same
#: milestone and must not both be stored.
_DUPLICATE_TITLE_THRESHOLD = 0.82
#: A financial target must start from the figure the plan states.
_START_VALUE_TOLERANCE = Decimal("0.01")

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


@dataclass
class ChatOutcome:
    """The result of a conversation in which the model could call tools."""

    content: str = ""
    tools_used: list[str] = field(default_factory=list)
    turns: int = 1
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: Decimal | None = None


@dataclass
class GenerationOutcome:
    """What one generation run produced."""

    result: GenerationResult
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: Decimal | None = None
    raw_response: str = ""
    repairs: int = 0
    dropped_milestones: list[str] = field(default_factory=list)

    @property
    def prompt_version(self) -> str:
        return PROMPT_VERSION


class AIService:
    """Generates milestones for a case."""

    def __init__(
        self,
        provider: AIProvider,
        *,
        model: str = "gpt-5-mini",
        max_output_tokens: int = 20000,
    ) -> None:
        self._provider = provider
        self._model = model
        self._max_output_tokens = max_output_tokens

    @property
    def model(self) -> str:
        return self._model

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """The answer of the model, as JSON text.

        The schema is passed to the provider as it is, so the answer comes
        back with the shape that was asked for.
        """
        response = await self._provider.complete_json(
            system=system,
            user=user,
            schema=schema,
            model=model or self._model,
            max_tokens=max_tokens,
        )
        return response.content

    async def chat_with_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_handler: Callable[[str, dict[str, Any]], Awaitable[str]],
        model: str | None = None,
        max_tokens: int | None = None,
        max_turns: int = 3,
    ) -> ChatOutcome:
        """Hold a conversation in which the model may call tools.

        The loop is the classic one: the model asks for a tool, the
        application answers it, and the model answers the client with what it
        found.  The handler is injected, so the service never has to know
        where the data comes from.
        """
        conversation = list(messages)
        tools_used: list[str] = []
        response: ChatResponse | None = None

        for _turn in range(max_turns):
            response = await self._provider.chat(
                messages=conversation,
                tools=tools,
                model=model or self._model,
                max_tokens=max_tokens,
            )
            if not response.wants_tools:
                break

            conversation.append(response.to_assistant_message())
            for call in response.tool_calls:
                result = await tool_handler(call.name, call.arguments)
                tools_used.append(call.name)
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )

        if response is None:  # pragma: no cover - the loop always runs once
            raise AiInvalidResponseError("The AI provider did not answer")

        return ChatOutcome(
            content=response.content,
            tools_used=tools_used,
            turns=len(tools_used) + 1,
            model=response.model or self._model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
        )

    async def generate_milestones(
        self,
        digest: PlanDigest,
        *,
        existing_anchors: list[str] | None = None,
    ) -> GenerationOutcome:
        """Generate, validate and clean up the milestones for a case."""
        system = build_system_prompt(digest, MILESTONE_GENERATION_SCHEMA["schema"])
        user = build_user_prompt(digest, existing_anchors=existing_anchors)

        try:
            return await self._ask(system, user, digest)
        except AiInvalidResponseError as exc:
            logger.info("The generation was rejected: %s", exc)
            repaired = await self._repair(system, user, digest, exc)
            if repaired is None:
                raise
            return repaired

    # -- provider calls --------------------------------------------------

    async def _ask(
        self, system: str, user: str, digest: PlanDigest
    ) -> GenerationOutcome:
        response = await self._provider.complete_json(
            system=system,
            user=user,
            schema=MILESTONE_GENERATION_SCHEMA,
            model=self._model,
            max_tokens=self._max_output_tokens,
        )
        payload = _parse_json(response.content)
        try:
            result = GenerationResult.model_validate(payload)
        except ValidationError as exc:
            raise _validation_error(exc, response.content) from exc

        try:
            result = self._apply_rules(result, digest)
        except AiInvalidResponseError:
            raise
        except ValueError as exc:
            raise AiInvalidResponseError(
                str(exc), error_summary=str(exc), raw=response.content
            ) from exc

        return GenerationOutcome(
            result=result,
            model=response.model or self._model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=response.cost_usd,
            raw_response=response.content,
            dropped_milestones=list(result.dropped_milestones),
        )

    async def _repair(
        self,
        system: str,
        user: str,
        digest: PlanDigest,
        error: AiInvalidResponseError,
    ) -> GenerationOutcome | None:
        """One second attempt, telling the model what was wrong."""
        repair_user = (
            f"{user}\n\n"
            "Your previous answer was rejected. Here it is:\n"
            f"{error.raw[:4000]}\n\n"
            "Here is what was wrong:\n"
            f"{error.error_summary or 'The answer did not satisfy the contract.'}\n\n"
            "Answer again with the same JSON schema, corrected."
        )
        try:
            outcome = await self._ask(system, repair_user, digest)
        except (AiInvalidResponseError, AiProviderUnavailableError) as exc:
            logger.warning("The generation could not be repaired: %s", exc)
            return None
        outcome.repairs = 1
        return outcome

    # -- rules -----------------------------------------------------------

    def _apply_rules(
        self, result: GenerationResult, digest: PlanDigest
    ) -> GenerationResult:
        """Enforce the rules that protect the client from invented data.

        A milestone that cites something the plan does not contain, or that
        anchors on something that does not exist, is dropped: it is never
        stored.  The rest of the answer is kept, because one bad milestone
        must not cost the household the whole plan.
        """
        kept: list[MilestoneProposal] = []
        dropped: list[str] = []
        for proposal in result.milestones:
            try:
                self._validate_source_refs(proposal, digest)
                self._validate_anchor(proposal, digest)
                self._validate_financial_target(proposal, digest)
            except ValueError as exc:
                logger.warning("Dropping a milestone: %s", exc)
                dropped.append(proposal.title)
                continue
            kept.append(proposal)

        if not kept:
            raise AiInvalidResponseError(
                "No milestone of the answer could be validated",
                error_summary="; ".join(dropped[:8]),
            )
        result.milestones = self._deduplicate(kept)
        result.dropped_milestones = dropped
        return result

    def _validate_source_refs(
        self, proposal: MilestoneProposal, digest: PlanDigest
    ) -> None:
        for ref in proposal.source_refs:
            if ref.json_path is None:
                continue
            if digest.path_is_known(ref.json_path):
                continue
            if _path_present(ref.json_path, digest):
                continue
            raise ValueError(
                f"milestone {proposal.title!r} cites {ref.json_path!r}, "
                "which is not part of the plan data"
            )

    def _validate_anchor(
        self, proposal: MilestoneProposal, digest: PlanDigest
    ) -> None:
        kind, _, value = proposal.anchor_key.partition(":")
        kind = kind.strip().lower()
        value = value.strip()
        if not value:
            raise ValueError(f"milestone {proposal.title!r} has an empty anchor_key")

        if kind == "concern":
            known = {concern.code for concern in digest.concerns}
        elif kind == "tension":
            known = {tension.code for tension in digest.tensions}
        elif kind == "metric":
            known = {metric.metric_key for metric in digest.metrics}
        elif kind == "section":
            known = {section.value for section in PlanSection}
        elif kind == "goal":
            known = set(digest.goals.keys()) if isinstance(digest.goals, dict) else set()
            known.add("goals")
        elif kind == "narrative":
            known = set(digest.narratives.keys())
            known |= {
                key.rsplit(".", 1)[-1] for key in digest.sections if "narrative" in key
            }
        else:
            raise ValueError(
                f"milestone {proposal.title!r} uses an unknown anchor kind {kind!r}"
            )

        if value not in known:
            raise ValueError(
                f"milestone {proposal.title!r} anchors on {proposal.anchor_key!r}, "
                "which does not exist in the plan data"
            )

    def _validate_financial_target(
        self, proposal: MilestoneProposal, digest: PlanDigest
    ) -> None:
        target = proposal.financial_target
        if target is None:
            return
        metric = digest.metric_by_key(target.metric_key)
        if metric is None:
            raise ValueError(
                f"milestone {proposal.title!r} measures {target.metric_key!r}, "
                "which is not a metric of the plan"
            )
        difference = abs(Decimal(str(target.start_value)) - metric.value)
        reference = abs(metric.value) or Decimal(1)
        if difference > reference * _START_VALUE_TOLERANCE + Decimal("0.01"):
            raise ValueError(
                f"milestone {proposal.title!r} starts from {target.start_value}, "
                f"but the plan states {metric.value}"
            )

    def _deduplicate(
        self, proposals: list[MilestoneProposal]
    ) -> list[MilestoneProposal]:
        """Remove milestones that say the same thing twice."""
        kept: list[MilestoneProposal] = []
        for proposal in proposals:
            duplicate = None
            for existing in kept:
                if existing.anchor_key == proposal.anchor_key:
                    duplicate = existing
                    break
                if (
                    existing.category == proposal.category
                    and title_similarity(existing.title, proposal.title)
                    >= _DUPLICATE_TITLE_THRESHOLD
                ):
                    duplicate = existing
                    break
            if duplicate is None:
                kept.append(proposal)
                continue
            # Merge: keep the richer version and the union of the references.
            merged_refs = list(duplicate.source_refs)
            known = {(r.part, r.section, r.json_path) for r in merged_refs}
            for ref in proposal.source_refs:
                key = (ref.part, ref.section, ref.json_path)
                if key not in known:
                    merged_refs.append(ref)
                    known.add(key)
            duplicate.source_refs = merged_refs
            merged_tasks = list(duplicate.tasks)
            titles = {task.title.strip().lower() for task in merged_tasks}
            for task in proposal.tasks:
                if task.title.strip().lower() not in titles:
                    merged_tasks.append(task)
                    titles.add(task.title.strip().lower())
            duplicate.tasks = merged_tasks
            if duplicate.financial_target is None:
                duplicate.financial_target = proposal.financial_target
        return kept


def _path_present(json_path: str, digest: PlanDigest) -> bool:
    """Whether a json path appears in the data handed to the model."""
    for key, text in digest.sections.items():
        if key.endswith(json_path) or json_path in key:
            return True
        if json_path in text:
            return True
    return False


def _parse_json(content: str) -> dict[str, Any]:
    """Parse the answer, tolerating a fenced code block."""
    stripped = content.strip()
    if not stripped:
        raise AiInvalidResponseError("The AI provider returned an empty answer")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(stripped)
        if match:
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError as exc:
                raise AiInvalidResponseError(
                    "The AI provider answered with something that is not JSON"
                ) from exc
        else:
            raise AiInvalidResponseError(
                "The AI provider answered with something that is not JSON"
            ) from None
    if not isinstance(payload, dict):
        raise AiInvalidResponseError(
            "The AI provider answered with a non object payload"
        )
    return payload


def _validation_error(exc: ValidationError, raw: str) -> AiInvalidResponseError:
    """Build the error raised when the answer does not satisfy the contract."""
    details = "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in exc.errors()[:8]
    )
    return AiInvalidResponseError(
        f"The AI answer did not satisfy the contract: {details}",
        error_summary=details,
        raw=raw,
    )


__all__ = ["AIService", "GenerationOutcome", "Category"]
