"""The normaliser: turning plan payloads into a bounded digest."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.integration.mcp.normalizer import (
    detect_language,
    extract_facts,
    normalize_plan,
    parse_persona,
)

CASES = Path(__file__).resolve().parents[2].parent.parent / "cases"


@pytest.fixture(scope="module")
def weah_files() -> dict:
    case = CASES / "timothy-melanie-weah"
    return {
        "financial_health": json.loads(
            (case / "financial-health.json").read_text(encoding="utf-8")
        ),
        "investment_analysis": json.loads(
            (case / "investment-analysis.json").read_text(encoding="utf-8")
        ),
        "persona": (case / "persona.md").read_text(encoding="utf-8"),
    }


def test_persona_is_split_into_sections(weah_files):
    sections, concerns, tensions = parse_persona(weah_files["persona"])
    assert "D0: Wealth tier" in sections
    assert "Tensions" in sections
    assert len(concerns) == 7
    assert len(tensions) == 4


def test_concerns_carry_their_severity(weah_files):
    _sections, concerns, _tensions = parse_persona(weah_files["persona"])
    first = concerns[0]
    assert first.code == "O1"
    assert first.severity == "SIGNIFICANT"
    assert "Life insurance" in first.title


def test_the_other_persona_layout_is_understood():
    markdown = "## Objective concerns\n\n- **O1 SIGNIFICANT: Retirement shortfall.** Savings run out.\n"
    _sections, concerns, _tensions = parse_persona(markdown)
    assert concerns[0].code == "O1"
    assert concerns[0].severity == "SIGNIFICANT"
    assert concerns[0].title == "Retirement shortfall"


def test_tensions_in_the_second_layout_are_understood():
    markdown = "## Tensions\n\n- **T1: Two goals compete (HIGH).** They share the same money.\n"
    _sections, _concerns, tensions = parse_persona(markdown)
    assert tensions[0].code == "T1"
    assert tensions[0].severity == "HIGH"


def test_facts_and_rules_are_extracted(weah_files):
    facts, rules = extract_facts(weah_files["financial_health"])
    assert len(rules) >= 5
    assert any(fact.key == "cash.accessibleCash" for fact in facts)
    cash = next(fact for fact in facts if fact.key == "cash.accessibleCash")
    assert cash.unit == "USD"
    assert cash.label


def test_the_digest_stays_inside_the_budget(weah_files):
    digest = normalize_plan(
        "timothy-melanie-weah",
        financial_health=weah_files["financial_health"],
        investment_analysis=weah_files["investment_analysis"],
        persona=weah_files["persona"],
        max_chars=60_000,
    )
    total = sum(len(block) for block in digest.sections.values())
    assert total <= 60_000
    assert digest.omitted_sections == []
    assert "persona" in digest.sections


def test_the_budget_drops_the_least_important_blocks(weah_files):
    digest = normalize_plan(
        "timothy-melanie-weah",
        financial_health=weah_files["financial_health"],
        investment_analysis=weah_files["investment_analysis"],
        persona=weah_files["persona"],
        max_chars=20_000,
    )
    total = sum(len(block) for block in digest.sections.values())
    assert total <= 20_000
    assert digest.omitted_sections


def test_the_fingerprint_changes_with_the_data(weah_files):
    first = normalize_plan(
        "timothy-melanie-weah",
        financial_health=weah_files["financial_health"],
        investment_analysis=weah_files["investment_analysis"],
        persona=weah_files["persona"],
    )
    second = normalize_plan(
        "timothy-melanie-weah",
        financial_health=weah_files["financial_health"],
        investment_analysis=weah_files["investment_analysis"],
        persona=weah_files["persona"],
    )
    assert first.fingerprint == second.fingerprint

    changed = dict(weah_files["financial_health"])
    changed["score"] = {**changed["score"], "published_score": 61}
    third = normalize_plan(
        "timothy-melanie-weah",
        financial_health=changed,
        investment_analysis=weah_files["investment_analysis"],
        persona=weah_files["persona"],
    )
    assert third.fingerprint != first.fingerprint


def test_the_metrics_carry_the_balances_of_the_plan(weah_files):
    digest = normalize_plan(
        "timothy-melanie-weah",
        financial_health=weah_files["financial_health"],
        persona=weah_files["persona"],
    )
    keys = {metric.metric_key for metric in digest.metrics}
    assert "liability_chase_cc" in keys
    assert "account_cash_account" in keys


def test_language_detection():
    assert detect_language(["the household has a plan and the family is here"]) == "en"
    assert detect_language(["la familia tiene un plan y el hogar está aquí"]) == "es"


def test_every_offline_case_produces_a_digest():
    for case_dir in sorted(CASES.iterdir()):
        if not case_dir.is_dir():
            continue
        financial_health = json.loads(
            (case_dir / "financial-health.json").read_text(encoding="utf-8")
        )
        persona = (case_dir / "persona.md").read_text(encoding="utf-8")
        digest = normalize_plan(case_dir.name, financial_health=financial_health, persona=persona)
        assert digest.fingerprint
        assert digest.sections
        assert digest.metrics


def test_asyncio_is_available_for_the_sources():
    assert asyncio.get_event_loop_policy() is not None
