"""The register the mentor speaks in.

Not every household wants the same voice.  Three registers are available and
the persona decides which one fits:

``refranero``
    Close and warm, with popular sayings, for households that want a human
    explanation instead of bank jargon.
``sencillo``
    Plain and practical, without technicalities, for households that want
    clarity without detours.
``formal``
    Executive and strategic, for households with a high financial culture.

The decision is deterministic: it comes from the classification the persona
closes with, and the household can always ask for another register.
"""

from __future__ import annotations

from typing import Any

#: The three registers the mentor knows.
STYLE_PROFILES: dict[str, dict[str, str]] = {
    "refranero": {
        "style_key": "refranero",
        "gemini_voice": "Aoede",
        "openai_voice": "coral",
        "voice_id": "gD1IexrzCvsXPHUuT0s3",  # ElevenLabs ES Nativa: Sara Martín
        "fallback_voice": "KHCvMklQZZo0O30ERnVn",
        "voice_name": "Sara Martín (ES Nativa / Cercana)",
        "style_label": "Cercana, Cálida y Cotidiana",
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: CERCANO, CÁLIDO Y COTIDIANO "
            "(para familias que quieren explicaciones humanas y sin jerga bancaria).\n"
            "- Explica la situación con naturalidad y ejemplos sencillos de casa y familia.\n"
            "- No abuses de refranes populares ni frases hechas forzadas; mantén un tono humano, "
            "cercano y elegante en máximo 2 frases breves."
        ),
    },
    "sencillo": {
        "style_key": "sencillo",
        "gemini_voice": "Puck",
        "openai_voice": "echo",
        "voice_id": "Nh2zY9kknu6z4pZy6FhD",  # ElevenLabs ES Nativa: David Martín
        "fallback_voice": "fXcll5SYKmCCtKLLpepe",
        "voice_name": "David Martín (ES Nativo / Práctico)",
        "style_label": "Sencillo, Directo y Sin Tecnicismos",
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: SENCILLO, PRÁCTICO Y DIRECTO AL GRANO "
            "(para clientes sin estudios financieros que quieren claridad total sin rodeos).\n"
            "- CERO tecnicismos financieros y CERO porcentajes o listas de cifras. Habla en "
            "lenguaje llano y cotidiano, como si explicaras las cuentas de casa en la mesa "
            "de la cocina.\n"
            "- Usa comparaciones prácticas del día a día ('primero se tapa la gotera del techo "
            "antes de comprar muebles nuevos') y céntrate en cuál es el primer paso concreto "
            "que deben dar hoy."
        ),
    },
    "formal": {
        "style_key": "formal",
        "gemini_voice": "Charon",
        "openai_voice": "marin",
        "voice_id": "Ir1QNHvhaJXbAGhT50w3",  # ElevenLabs ES Nativa: Sara Martín Ejecutiva
        "fallback_voice": "erKgR0s8Y67t4iiHuA9R",
        "voice_name": "Elena Martín (ES Nativa / Ejecutiva)",
        "style_label": "Formal, Ejecutivo y Estratégico",
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: FORMAL, CULTO Y EJECUTIVO "
            "(para un perfil con estudios superiores y alta cultura financiera).\n"
            "- Habla con elegancia, rigor y vocabulario estratégico propio de banca privada.\n"
            "- IMPORTANTE: Incluso en tono formal, NO recites listas de cifras ni porcentajes "
            "como un robot. Sintetiza el diagnóstico en una conclusión ejecutiva clara (ej. "
            "'Su balance destaca por la ausencia de deuda, pero presenta una desalineación "
            "fiscal y de horizonte que comprometería su liquidez a mitad de su jubilación')."
        ),
    },
}

#: The classification values that lead to a register.
_FORMAL_MARKERS = {("D5", "VALIDATOR"), ("D6", "DUTY")}
_PLAIN_MARKERS = {("D6", "FREEDOM"), ("D5", "DUAL")}


def _as_classification(classification: Any) -> dict[str, str]:
    """The classification as a dictionary, whatever shape it arrives in."""
    if isinstance(classification, dict):
        return {str(key).upper(): str(value).strip().upper() for key, value in classification.items()}
    if isinstance(classification, str):
        parsed: dict[str, str] = {}
        for line in classification.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().upper()
            if key.startswith("D") and key[1:].isdigit():
                parsed[key] = value.strip().upper()
        return parsed
    return {}


def resolve_voice_profile(
    classification: Any, style_override: str | None = None
) -> dict[str, str]:
    """The register and the voice of a household.

    ``style_override`` wins when it names one of the three registers.
    """
    if style_override and style_override in STYLE_PROFILES:
        profile = dict(STYLE_PROFILES[style_override])
        profile["realtime_voice"] = profile["gemini_voice"]
        return profile

    parsed = _as_classification(classification)
    pairs = set(parsed.items())

    if pairs & _FORMAL_MARKERS:
        profile = dict(STYLE_PROFILES["formal"])
    elif pairs & _PLAIN_MARKERS:
        profile = dict(STYLE_PROFILES["sencillo"])
    else:
        profile = dict(STYLE_PROFILES["refranero"])

    profile["realtime_voice"] = profile["gemini_voice"]
    return profile


def available_styles() -> list[str]:
    """The registers the household can ask for."""
    return list(STYLE_PROFILES)
