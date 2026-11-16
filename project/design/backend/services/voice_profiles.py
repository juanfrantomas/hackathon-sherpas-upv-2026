"""
services/voice_profiles.py
--------------------------
Servicio de análisis psicológico, nivel educativo/lingüístico y personalización de voz.
Determina la voz nativa (Gemini Live / OpenAI Realtime) y de ElevenLabs, así como el
registro de habla adaptado al perfil del cliente:
- 'refranero': Cercano, empático y con refranes tradicionales españoles.
- 'sencillo': Práctico, llano y cotidiano (cero tecnicismos bancarios ni porcentajes).
- 'formal': Ejecutivo, estratégico y culto (para clientes con alta cultura financiera).
"""

from typing import Any, Dict, Optional

STYLE_PROFILES: Dict[str, Dict[str, str]] = {
    "refranero": {
        "style_key": "refranero",
        "gemini_voice": "Aoede",
        "openai_voice": "coral",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",  # ElevenLabs: Rachel
        "fallback_voice": "alloy",
        "voice_name": "Aoede (Cercana / Refranero Popular)",
        "style_label": "Cercana, Familiar y con Refranes",
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: CERCANO, CÁLIDO Y CON REFRANES POPULARES (para familias que quieren explicaciones humanas y sin jerga bancaria).\n"
            "- PROHIBIDO aburrir con porcentajes, tablas o cifras exactas. No recites números: explica la situación con metáforas de casa y familia ('tener tanto dinero parado en el banco mientras debéis la tarjeta es como tener un cubo con un agujero en el fondo').\n"
            "- Incluye de forma natural algún refrán tradicional español que venga al caso: 'más vale prevenir que curar', 'más vale pájaro en mano que ciento volando', 'grano a grano se hace el granero', 'no dejes para mañana lo que puedas quitar hoy', 'no se puede empezar la casa por el tejado'.\n"
            "- Usa palabras cotidianas y cercanas, siempre con respeto y profesionalidad."
        ),
    },
    "sencillo": {
        "style_key": "sencillo",
        "gemini_voice": "Puck",
        "openai_voice": "echo",
        "voice_id": "Xb7hH8MSUJpSbSDYk0k2",  # ElevenLabs: Alice
        "fallback_voice": "shimmer",
        "voice_name": "Puck (Práctico / Sin Tecnicismos)",
        "style_label": "Sencillo, Directo y Sin Tecnicismos",
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: SENCILLO, PRÁCTICO Y DIRECTO AL GRANO (para clientes sin estudios financieros que quieren claridad total sin rodeos).\n"
            "- CERO tecnicismos financieros y CERO porcentajes o listas de cifras. Habla en lenguaje llano y cotidiano, como si explicaras las cuentas de casa en la mesa de la cocina.\n"
            "- Usa comparaciones prácticas del día a día ('primero se tapa la gotera del techo antes de comprar muebles nuevos') y céntrate en cuál es el primer paso concreto que deben dar hoy."
        ),
    },
    "formal": {
        "style_key": "formal",
        "gemini_voice": "Charon",
        "openai_voice": "marin",
        "voice_id": "29vD33N1CtxCmqQRPOHJ",  # ElevenLabs: Drew
        "fallback_voice": "onyx",
        "voice_name": "Charon (Ejecutivo / Patrimonial)",
        "style_label": "Formal, Ejecutivo y Estratégico",
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: FORMAL, CULTO Y EJECUTIVO (para un perfil con estudios superiores y alta cultura financiera).\n"
            "- Habla con elegancia, rigor y vocabulario estratégico propio de banca privada.\n"
            "- IMPORTANTE: Incluso en tono formal, NO recites listas de cifras ni porcentajes como un robot. Sintetiza el diagnóstico en una conclusión ejecutiva clara (ej. 'Su balance destaca por la ausencia de deuda, pero presenta una desalineación fiscal y de horizonte que comprometería su liquidez a mitad de su jubilación')."
        ),
    },
}


def resolve_voice_profile(
    client_id: str,
    compact_context: Dict[str, Any],
    style_override: Optional[str] = None,
) -> Dict[str, str]:
    """
    Determina la voz y el registro lingüístico según el perfil del cliente
    (o usa `style_override` si el frontend solicita un registro específico:
    'refranero', 'sencillo', 'formal').
    """
    if style_override and style_override in STYLE_PROFILES:
        profile = dict(STYLE_PROFILES[style_override])
        profile["realtime_voice"] = profile["gemini_voice"]
        return profile

    classification = (compact_context.get("classification") or "").upper()

    # 1. Samantha Lewis (D5: VALIDATOR / D6: DUTY, directiva con $250k e inversiones en ETFs) -> Formal Ejecutivo
    if "D5: VALIDATOR" in classification or "D6: DUTY" in classification:
        profile = dict(STYLE_PROFILES["formal"])
    # 2. Michael Carter (D6: FREEDOM) o Daniel & Emily Johnson (D5: DUAL) -> Sencillo, Práctico y Directo
    elif "D6: FREEDOM" in classification or "D5: DUAL" in classification:
        profile = dict(STYLE_PROFILES["sencillo"])
    # 3. Timothy & Melanie Weah (Pareja con niños pequeños, mucho efectivo parado) -> Cercano y Refranero
    else:
        profile = dict(STYLE_PROFILES["refranero"])

    profile["realtime_voice"] = profile["gemini_voice"]
    return profile
