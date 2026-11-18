"""The register the mentor speaks in."""

from __future__ import annotations

import pytest

from app.domain.voice_profiles import (
    STYLE_PROFILES,
    available_styles,
    resolve_voice_profile,
)


def test_the_three_registers_exist():
    assert set(available_styles()) == {"refranero", "sencillo", "formal"}
    for profile in STYLE_PROFILES.values():
        assert profile["gemini_voice"]
        assert profile["openai_voice"]
        assert profile["voice_id"]
        assert profile["tone_instructions"]


@pytest.mark.parametrize(
    ("classification", "expected"),
    [
        ({"D5": "VALIDATOR"}, "formal"),
        ({"D6": "DUTY"}, "formal"),
        ({"D6": "FREEDOM"}, "sencillo"),
        ({"D5": "DUAL"}, "sencillo"),
        ({"D5": "COLLABORATOR", "D6": "PROTECTION"}, "refranero"),
        ({}, "refranero"),
        (None, "refranero"),
    ],
)
def test_the_classification_decides_the_register(classification, expected):
    assert resolve_voice_profile(classification)["style_key"] == expected


def test_the_classification_can_be_a_raw_block():
    block = "D0: EMERGING\nD5: DUAL\nD6: PROTECTION"
    assert resolve_voice_profile(block)["style_key"] == "sencillo"


@pytest.mark.parametrize("style", ["refranero", "sencillo", "formal"])
def test_the_household_can_ask_for_another_register(style):
    profile = resolve_voice_profile({"D5": "DUAL"}, style_override=style)
    assert profile["style_key"] == style
    assert profile["realtime_voice"] == profile["gemini_voice"]


def test_an_unknown_override_is_ignored():
    profile = resolve_voice_profile({"D5": "DUAL"}, style_override="shouting")
    assert profile["style_key"] == "sencillo"


def test_the_register_tells_the_model_how_to_speak():
    profile = resolve_voice_profile({"D6": "DUTY"})
    assert "FORMAL" in profile["tone_instructions"]
    assert "PROHIBIDO" in STYLE_PROFILES["refranero"]["tone_instructions"]
    assert "CERO tecnicismos" in STYLE_PROFILES["sencillo"]["tone_instructions"]
