"""Reading a case for a conversation: context, compaction and the couple."""

from __future__ import annotations

import asyncio

import pytest

from app.domain.cases import get_short_id, normalize_case_id
from app.domain.couple import build_partner_instruction, member_focus
from app.integration.mcp.compaction import (
    MAX_TOOL_RESPONSE_CHARS,
    compact_payload,
    summarize_projections,
)
from app.integration.mcp.context import CaseContext
from app.integration.mcp.normalizer import extract_persona_section, parse_classification
from app.services.case_service import validate_case_id

CASES = {
    "weah": "timothy-melanie-weah",
    "carter": "michael-carter",
    "johnson": "daniel-emily-johnson",
    "lewis": "samantha-lewis",
}


@pytest.fixture()
def context(case_source):
    return CaseContext(case_source)


# --- identifiers -------------------------------------------------------


@pytest.mark.parametrize(("alias", "slug"), CASES.items())
def test_the_short_alias_resolves_to_the_slug(alias, slug):
    assert normalize_case_id(alias) == slug
    assert validate_case_id(alias) == slug


@pytest.mark.parametrize("slug", CASES.values())
def test_the_slug_resolves_to_itself(slug):
    assert normalize_case_id(slug) == slug


def test_the_short_id_is_the_one_the_prototype_used():
    assert get_short_id("timothy-melanie-weah") == "weah"
    assert get_short_id("weah") == "weah"


def test_an_unknown_identifier_is_left_alone():
    assert normalize_case_id("somebody-else") == "somebody-else"


# --- persona -----------------------------------------------------------


def test_the_classification_is_parsed(cases_dir):
    markdown = (cases_dir / "timothy-melanie-weah" / "persona.md").read_text()
    classification = parse_classification(markdown)
    assert classification["D0"] == "EMERGING"
    assert classification["D5"] == "COLLABORATOR"
    assert classification["D6"] == "PROTECTION"


def test_a_persona_section_is_extracted(cases_dir):
    markdown = (cases_dir / "timothy-melanie-weah" / "persona.md").read_text()
    section = extract_persona_section(markdown, "D3")
    assert "MODERATE GAPS" in section
    assert len(section) < len(markdown)


def test_the_classification_section_is_the_compact_block(cases_dir):
    markdown = (cases_dir / "samantha-lewis" / "persona.md").read_text()
    section = extract_persona_section(markdown, "classification")
    assert "D0:" in section
    assert "EMERGING" in section
    assert len(section) < 1000


def test_an_unknown_persona_section_falls_back_to_the_classification(cases_dir):
    markdown = (cases_dir / "timothy-melanie-weah" / "persona.md").read_text()
    section = extract_persona_section(markdown, "D9")
    assert "D0:" in section
    assert len(section) < 1000


# --- compaction --------------------------------------------------------


def test_a_small_payload_is_left_alone():
    payload = {"score": 60}
    assert compact_payload(payload) == payload


def test_a_bulky_block_becomes_a_summary():
    payload = {"key_metrics": {f"key_{index}": "x" * 900 for index in range(20)}}
    compacted = compact_payload(payload)
    assert "_notice" in compacted
    assert "available_sub_sections" in compacted
    assert len(str(compacted)) < len(str(payload))


def test_a_sub_section_narrows_the_payload():
    payload = {"incomes": {"a": 1}, "expenses": {"b": 2}}
    assert compact_payload(payload, sub_section="incomes") == {"incomes": {"a": 1}}


def test_an_unknown_sub_section_explains_itself():
    compacted = compact_payload({"incomes": {}}, sub_section="nope")
    assert "_hint" in compacted
    assert "incomes" in compacted["_hint"]


def test_the_projections_are_summarised():
    years = [{"year": 2020 + index, "ending_savings": 100} for index in range(40)]
    years[-1]["ending_savings"] = -1
    summary = summarize_projections({"years": years})
    assert summary["total_years_modeled"] == 40
    assert summary["first_depletion_year"] == 2059
    assert len(summary["key_milestone_years"]) < 40


def test_a_compacted_answer_never_exceeds_the_budget():
    payload = {"key_metrics": {f"key_{index}": "x" * 900 for index in range(50)}}
    compacted = compact_payload(payload)
    assert len(str(compacted)) <= MAX_TOOL_RESPONSE_CHARS * 2


# --- the household -----------------------------------------------------


def test_the_compact_context_describes_the_household(context):
    data = asyncio.run(context.get_compact_client_context("timothy-melanie-weah"))
    assert data["is_couple"] is True
    assert [member["first_name"] for member in data["adults"]] == ["Timothy", "Melanie"]
    assert data["score_summary"]["published_score"] == 60
    assert "D5" in data["classification"]


def test_the_compact_context_of_a_single_person(context):
    data = asyncio.run(context.get_compact_client_context("michael-carter"))
    assert data["is_couple"] is False
    assert len(data["adults"]) == 1


def test_the_couple_dynamics_describe_both_partners(context):
    data = asyncio.run(context.get_couple_dynamics("timothy-melanie-weah"))
    assert data["is_couple"] is True
    assert [member["name"] for member in data["members"]] == ["Timothy", "Melanie"]
    assert data["members"][0]["risk_profile"] == "Growth"
    assert "PUENTE" not in data["consensus_bridge"].upper()
    assert data["consensus_bridge"]


def test_the_couple_dynamics_of_a_single_person(context):
    data = asyncio.run(context.get_couple_dynamics("samantha-lewis"))
    assert data["is_couple"] is False
    assert len(data["members"]) == 1


# --- the brief ---------------------------------------------------------


def test_the_brief_holds_the_household_and_the_gaps(context):
    brief = asyncio.run(context.build_realtime_brief("timothy-melanie-weah"))
    assert "HOGAR:" in brief
    assert "SCORE: 60/100" in brief
    assert "PASOS QUE SUBEN SU SCORE" in brief
    assert "MODO PAREJA" in brief
    assert len(brief) < 8000


def test_the_brief_carries_the_topic(context):
    brief = asyncio.run(
        context.build_realtime_brief("michael-carter", topic="the credit card")
    )
    assert "TEMA ACTIVO" in brief
    assert "the credit card" in brief


def test_the_brief_of_a_single_person_has_no_couple_mode(context):
    brief = asyncio.run(context.build_realtime_brief("michael-carter"))
    assert "MODO PAREJA" not in brief


# --- the partner instruction -------------------------------------------


def test_the_focus_depends_on_the_risk_profile():
    assert "rentabilidad" in member_focus("Growth")
    assert "Seguridad" in member_focus("Moderate")
    assert member_focus(None) == member_focus("moderate")


def test_the_partner_instruction_addresses_one_member():
    couple = {
        "is_couple": True,
        "members": [
            {"key": "timothy", "name": "Timothy", "age": 40, "risk_profile": "Growth", "personal_focus": "a"},
            {"key": "melanie", "name": "Melanie", "age": 38, "risk_profile": "Moderate", "personal_focus": "b"},
        ],
        "consensus_bridge": "the bridge",
    }
    instruction = build_partner_instruction(couple, "melanie")
    assert "MELANIE" in instruction
    assert "Timothy" in instruction
    assert "the bridge" in instruction


def test_the_partner_instruction_addresses_both_by_default():
    couple = {
        "is_couple": True,
        "members": [
            {"key": "timothy", "name": "Timothy", "age": 40, "risk_profile": "Growth", "personal_focus": "a"},
            {"key": "melanie", "name": "Melanie", "age": 38, "risk_profile": "Moderate", "personal_focus": "b"},
        ],
        "consensus_bridge": "the bridge",
    }
    instruction = build_partner_instruction(couple)
    assert "MODO PAREJA ACTIVO" in instruction
    assert "Timothy" in instruction and "Melanie" in instruction


def test_the_partner_instruction_of_a_single_person():
    couple = {
        "is_couple": False,
        "members": [
            {"key": "samantha", "name": "Samantha", "age": 45, "risk_profile": "Growth", "personal_focus": "a"}
        ],
    }
    instruction = build_partner_instruction(couple)
    assert "INTERLOCUTOR" in instruction
    assert "Samantha" in instruction
