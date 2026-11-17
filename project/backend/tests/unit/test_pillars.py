"""The decision laboratory and the rest of the pillars."""

from __future__ import annotations

import asyncio

import pytest

from app.domain.simulator import simulate, slug_of
from app.integration.ai.ai_service import AIService
from app.integration.ai.fake import FakeProvider
from app.integration.mcp.context import CaseContext
from app.services.couple_service import CoupleService
from app.services.insights_service import InsightsService
from app.services.simulator_service import SimulatorService
from app.services.story_service import StoryService


@pytest.fixture()
def context(case_source):
    return CaseContext(case_source)


def _score_block() -> dict:
    """The score block of the Weah household, as the plan states it."""
    return {
        "published_score": 60,
        "top_moves": [
            {
                "title": "Pay down revolving card",
                "action": "Pay $6,800 on the 18% card from cash",
                "score_before": 60,
                "score_after": 62,
            },
            {
                "title": "Add life cover",
                "action": "Add $235,000 of life cover",
                "score_before": 60,
                "score_after": 60,
            },
            {
                "title": "Add umbrella cover",
                "action": "Add $1M of umbrella",
                "score_before": 60,
                "score_after": 60,
            },
        ],
        "combined_moves": [
            {"moves": ["Pay down revolving card", "Add life cover", "Add umbrella cover"], "score_after": 78},
            {"moves": ["Pay down revolving card", "Add life cover"], "score_after": 73},
            {"moves": ["Pay down revolving card", "Add umbrella cover"], "score_after": 62},
            {"moves": ["Add life cover", "Add umbrella cover"], "score_after": 60},
        ],
    }


# --- the engine --------------------------------------------------------


def test_the_identifier_of_a_step_is_derived_from_its_title():
    assert slug_of("Pay down revolving card") == "pay-down-revolving-card"


def test_without_decisions_the_score_does_not_move():
    result = simulate(_score_block(), [])
    assert result.score_base == 60
    assert result.score_simulated == 60
    assert result.score_delta == 0
    assert result.synergy_detected is False


def test_one_decision_uses_the_score_of_the_plan():
    result = simulate(_score_block(), ["pay-down-revolving-card"])
    assert result.score_simulated == 62
    assert result.score_delta == 2


def test_two_decisions_use_the_combination_of_the_plan():
    result = simulate(
        _score_block(), ["pay-down-revolving-card", "add-life-cover"]
    )
    assert result.score_simulated == 73
    assert result.score_delta == 13


def test_three_decisions_reach_the_top_of_the_plan():
    result = simulate(
        _score_block(),
        ["pay-down-revolving-card", "add-life-cover", "add-umbrella-cover"],
    )
    assert result.score_simulated == 78
    assert result.score_delta == 18
    assert result.synergy_detected is True
    assert result.synergy_score == 78


def test_a_combination_that_does_not_exist_falls_back_to_the_best_step():
    result = simulate(_score_block(), ["add-life-cover", "add-umbrella-cover"])
    assert result.score_simulated == 60


def test_the_power_ups_carry_the_figures_of_the_plan():
    result = simulate(_score_block(), ["pay-down-revolving-card"])
    card = next(p for p in result.power_ups if p.id == "pay-down-revolving-card")
    assert card.score_before == 60
    assert card.score_after == 62
    assert card.score_impact == 2
    assert card.active is True
    assert "$6,800" in card.action


def test_a_plan_without_combined_moves_still_works():
    block = {"published_score": 26, "top_moves": [
        {"title": "Add umbrella cover", "action": "x", "score_before": 26, "score_after": 31}
    ]}
    result = simulate(block, ["add-umbrella-cover"])
    assert result.score_simulated == 31
    assert result.synergy_detected is False


# --- the services ------------------------------------------------------


def test_the_laboratory_answers_with_the_figures_of_the_plan(context):
    provider = FakeProvider(chat_answers=[])
    service = AIService(provider, model="fake-model")
    simulator = SimulatorService(service, context)

    answer = asyncio.run(
        simulator.simulate("timothy-melanie-weah", ["pay-down-revolving-card"])
    )

    assert answer.score_base == 60
    assert answer.simulated_score == 62
    assert answer.score_delta == 2
    assert answer.power_ups
    assert answer.generated is False  # the fake provider has no copy


def test_the_laboratory_adds_the_copy_of_the_model(context):
    copy = {
        "synergy_message": "Un combo",
        "combo_mentor_question": "¿Qué cambia?",
        "annual_saving_dollars": 3240,
        "saving_label": "intereses",
        "time_impact": "13 años menos",
        "visual_summary": "摘要",
        "power_up_copy": [
            {
                "id": "pay-down-revolving-card",
                "icon": "💳",
                "effort": "Bajo",
                "lock_label": "Abre el candado",
                "individual_impact": "Ahorra 3.240 al año",
                "mentor_question": "¿Qué cambia?",
            }
        ],
        "timeline_comparison": [
            {
                "milestone": "Hoy",
                "icon": "💸",
                "without_changes": "Pierdes 3.240 al año",
                "with_decisions": "Lo ahorras",
                "highlighted_change": "+3.240/año",
            }
        ],
        "pact_cards": [],
    }
    provider = FakeProvider(payload=copy)
    service = AIService(provider, model="fake-model")
    simulator = SimulatorService(service, context)

    answer = asyncio.run(simulator.simulate("timothy-melanie-weah", []))
    assert answer.generated is True
    assert answer.annual_saving_dollars == 3240
    assert answer.power_ups[0].icon == "💳"
    assert answer.timeline_comparison[0].highlighted_change == "+3.240/año"


def test_the_insights_answer_with_the_register_of_the_household(context):
    copy = {
        "proactive_nudge": {
            "badge": "Píldora del día",
            "greeting": "Buenos días",
            "message": "MIRA esto",
            "cta_label": "Abrir el plan",
            "voice_question": "¿Por qué?",
        },
        "jargon_pills": [
            {
                "term": "Fondo de emergencia",
                "short_tag": "Colchón",
                "metaphor_title": "Un cubo",
                "metaphor_explanation": "Reserva para lo imprevisto",
                "family_impact": "Tranquilidad",
                "voice_question": "¿Qué es un fondo de emergencia?",
            }
        ],
    }
    provider = FakeProvider(payload=copy)
    service = AIService(provider, model="fake-model")
    insights = InsightsService(service, context)

    answer = asyncio.run(insights.insights("samantha-lewis"))
    assert answer.style_key == "formal"
    assert answer.proactive_nudge.badge == "Píldora del día"
    assert answer.jargon_pills[0].term == "Fondo de emergencia"
    assert answer.generated is True


def test_the_story_has_four_scenes(context):
    scenes = [
        {
            "scene_id": index,
            "chapter": f"Chapter {index}",
            "headline_figure": "60 / 100",
            "title": "Title",
            "subtitle": "Subtitle",
            "caption_narration": "Narration",
        }
        for index in range(1, 5)
    ]
    provider = FakeProvider(
        payload={"main_challenge": "The challenge", "scenes": scenes}
    )
    service = AIService(provider, model="fake-model")
    story = StoryService(service, context)

    answer = asyncio.run(story.story("timothy-melanie-weah"))
    assert len(answer.scenes) == 4
    assert answer.main_challenge == "The challenge"
    assert answer.score == 60
    assert answer.is_couple is True
    assert answer.first_step_cta
    assert answer.generated is True


def test_the_couple_shows_both_members(context, db_session):
    provider = FakeProvider(
        payload={
                    "kids_safe_view": [
                        {
                            "id": "college",
                            "icon": "🎓",
                            "friendly_title": "La universidad",
                            "visual_meta": "2038",
                            "progress_percentage": 0,
                            "children_explanation": "Vuestrojecture",
                        }
                    ]
                }
    )
    service = AIService(provider, model="fake-model")
    couple = CoupleService(service, context)

    answer = asyncio.run(couple.overview(db_session, "timothy-melanie-weah"))
    assert answer.is_couple is True
    assert [member.name for member in answer.members] == ["Timothy", "Melanie"]
    assert answer.consensus_bridge
    assert answer.kids_safe_view[0].id == "college"
    assert answer.high_fives == []


def test_a_high_five_is_stored_and_read_back(context, db_session):
    from app.repositories import family_high_five_repository
    from app.services.case_service import ensure_case_row

    ensure_case_row(db_session, "timothy-melanie-weah")
    db_session.commit()

    family_high_five_repository.add_high_five(
        db_session,
        "timothy-melanie-weah",
        from_member="Timothy",
        to_member="Melanie",
        milestone_title="Pay the card",
        message="Bien hecho",
    )
    db_session.commit()

    stored = family_high_five_repository.list_high_fives(
        db_session, "timothy-melanie-weah"
    )
    assert len(stored) == 1
    assert stored[0].from_member == "Timothy"
    assert stored[0].message == "Bien hecho"
