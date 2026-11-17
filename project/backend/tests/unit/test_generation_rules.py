"""The rules the generator has to obey."""

from __future__ import annotations

import json

import pytest

from app.integration.ai.ai_service import AIService
from app.integration.ai.errors import AiInvalidResponseError
from app.integration.ai.fake import FailingProvider, FakeProvider
from app.integration.ai.prompts import build_system_prompt, build_user_prompt
from app.schemas.generation import (
    MILESTONE_GENERATION_SCHEMA,
    GenerationResult,
)


@pytest.fixture()
def digest(case_source):
    import asyncio

    return asyncio.run(case_source.get_digest("timothy-melanie-weah"))


def _service(payload) -> tuple[AIService, FakeProvider]:
    provider = FakeProvider(payload)
    return AIService(provider, model="fake-model"), provider


def test_a_valid_answer_is_accepted(digest):
    from tests.conftest import make_payload

    service, provider = _service(make_payload(digest))
    outcome = _run(service, digest)
    assert len(outcome.result.milestones) == 2
    assert outcome.result.milestones[0].category
    assert provider.calls


def _run(service, digest):
    import asyncio

    return asyncio.run(service.generate_milestones(digest))


def test_an_answer_that_is_not_json_is_rejected(digest):
    service, _ = _service("this is not json")
    with pytest.raises(AiInvalidResponseError):
        _run(service, digest)


def test_an_answer_that_breaks_the_contract_is_rejected(digest):
    service, _ = _service({"milestones": [{"title": "too short"}]})
    with pytest.raises(AiInvalidResponseError):
        _run(service, digest)


def test_a_milestone_without_sources_is_rejected(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    payload["milestones"][0]["source_refs"] = []
    service, _ = _service(payload)
    with pytest.raises(AiInvalidResponseError):
        _run(service, digest)


def test_a_citation_of_an_invented_path_drops_the_milestone(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    payload["milestones"][0]["source_refs"][0]["json_path"] = "financial-health.made.up"
    service, _ = _service(payload)
    outcome = _run(service, digest)
    assert len(outcome.result.milestones) == 1
    assert outcome.dropped_milestones == [payload["milestones"][0]["title"]]


def test_a_citation_of_a_real_path_is_accepted(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    payload["milestones"][0]["source_refs"][0]["json_path"] = (
        "key_metrics.facts.retirement.spendingGap"
    )
    service, _ = _service(payload)
    outcome = _run(service, digest)
    assert len(outcome.result.milestones) == 2
    assert outcome.dropped_milestones == []


def test_an_answer_where_nothing_holds_up_is_rejected(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    for milestone in payload["milestones"]:
        milestone["anchor_key"] = "concern:O999"
    service, _ = _service(payload)
    with pytest.raises(AiInvalidResponseError):
        _run(service, digest)


def test_an_anchor_that_does_not_exist_drops_the_milestone(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    payload["milestones"][0]["anchor_key"] = "concern:O999"
    service, _ = _service(payload)
    outcome = _run(service, digest)
    assert len(outcome.result.milestones) == 1
    assert outcome.dropped_milestones == [payload["milestones"][0]["title"]]


def test_an_unknown_anchor_kind_drops_the_milestone(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    payload["milestones"][0]["anchor_key"] = "planet:mars"
    service, _ = _service(payload)
    outcome = _run(service, digest)
    assert len(outcome.result.milestones) == 1


def test_a_financial_target_of_a_metric_that_does_not_exist_drops_the_milestone(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    payload["milestones"][1]["financial_target"]["metric_key"] = "metric_that_is_not_there"
    service, _ = _service(payload)
    outcome = _run(service, digest)
    assert len(outcome.result.milestones) == 1
    assert outcome.dropped_milestones == [payload["milestones"][1]["title"]]


def test_a_financial_target_that_invents_the_starting_figure_drops_the_milestone(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    payload["milestones"][1]["financial_target"]["start_value"] = 999999999
    service, _ = _service(payload)
    outcome = _run(service, digest)
    assert len(outcome.result.milestones) == 1


def test_duplicates_are_removed(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    payload["milestones"].append(dict(payload["milestones"][0]))
    service, _ = _service(payload)
    outcome = _run(service, digest)
    assert len(outcome.result.milestones) == 2


def test_milestones_with_a_similar_title_are_merged(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    twin = dict(payload["milestones"][0])
    twin["title"] = payload["milestones"][0]["title"] + " in detail"
    twin["anchor_key"] = "concern:O2"
    payload["milestones"].append(twin)
    service, _ = _service(payload)
    outcome = _run(service, digest)
    assert len(outcome.result.milestones) == 2


def test_the_generation_is_repaired_once(digest):
    from tests.conftest import make_payload

    payload = make_payload(digest)
    provider = FakeProvider(payload, invalid_once=True)
    service = AIService(provider, model="fake-model")
    outcome = _run(service, digest)
    assert outcome.repairs == 1
    assert len(outcome.result.milestones) == 2


def test_the_generation_uses_the_schema_and_the_plan_rules(digest):
    service, provider = _service({"milestones": []})
    with pytest.raises(AiInvalidResponseError):
        _run(service, digest)
    call = provider.calls[0]
    assert call["schema"] == MILESTONE_GENERATION_SCHEMA
    for rule in digest.fact_rules:
        assert rule in call["system"]


def test_the_prompt_carries_the_plan_and_the_coverage_instructions(digest):
    user = build_user_prompt(digest, existing_anchors=["concern:O2"])
    assert "concern:O2" in user
    assert "COVERAGE" in user
    assert "financial-health" in user or "persona" in user


def test_the_system_prompt_lists_the_taxonomy(digest):
    system = build_system_prompt(digest, MILESTONE_GENERATION_SCHEMA["schema"])
    assert "Insurance & Protection" in system
    assert "education" in system
    assert "checkin_offset_days" in system


def test_the_provider_failure_is_not_swallowed(digest):
    service = AIService(FailingProvider(), model="fake-model")
    with pytest.raises(AiInvalidResponseError):
        _run(service, digest)


def test_the_generation_result_rejects_unknown_fields():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GenerationResult.model_validate(
            {"milestones": [], "something_else": True}
        )


def test_the_schema_requires_every_field():
    required = MILESTONE_GENERATION_SCHEMA["schema"]["properties"]["milestones"]["items"][
        "required"
    ]
    assert set(required) == {
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
    }


def test_the_schema_is_json_serialisable():
    assert json.loads(json.dumps(MILESTONE_GENERATION_SCHEMA))
