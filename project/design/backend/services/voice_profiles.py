"""
services/voice_profiles.py
--------------------------
Servicio de análisis psicológico, detección de idioma del interlocutor y personalización de voz.
Determina la voz hispanohablante nativa (ElevenLabs Multilingual v2 / Gemini Live / OpenAI Realtime)
y el registro de habla adaptado simultáneamente a:
1) El perfil psicológico del cliente (D0-D6 de persona.md):
   - 'refranero': Cercano, empático, cálido y con refranes tradicionales españoles (Timothy & Melanie Weah).
   - 'sencillo': Práctico, llano y cotidiano, de mesa de cocina (Michael Carter / Daniel & Emily Johnson).
   - 'formal': Ejecutivo, estratégico y culto, de banca privada (Samantha Lewis).
2) El idioma en el que habla el usuario (si habla en español, exige voz hispanohablante nativa y
   motor multilingüe con fonética 100% castellana, evitando voces anglosajonas con acento extranjero).
"""

import re
from typing import Any, Dict, Optional, Tuple

# Registro en memoria de la voz fijada por (client_id, language) para que NUNCA cambie
# dentro del mismo cliente e idioma, y solo cambie cuando el usuario cambia de idioma ('es' <-> 'en').
_LOCKED_VOICE_BY_CLIENT_LANG: Dict[Tuple[str, str], Dict[str, Any]] = {}
_LAST_LANG_BY_CLIENT: Dict[str, str] = {}

# Criterio de idioma, psicología positiva (cero miedo), ritmo ágil y dicción nativa
SPANISH_NATIVE_PROSODY_RULE = (
    "\nREGLA DE PSICOLOGÍA POSITIVA (SUAVIZAR NOTICIAS DIFÍCILES Y TEMAS SENSIBLES):\n"
    "- PROHIBIDO usar palabras alarmistas o que den miedo a actuar: NUNCA digas 'crítico', 'momento crítico', 'peligro', 'grave', 'gastas más de lo que ingresas', 'muerte', 'fallecimiento' ni 'quedarte sin dinero en la vejez'.\n"
    "- Si la puntuación es baja (ej. 26 de Michael Carter), empieza validando lo que hace bien ('ahorras muchísimo cada año') y preséntalo como una oportunidad sencilla de sincronizar sus metas para saltar a 62 puntos.\n"
    "- Al hablar de seguro de vida o jubilación (ej. Daniel y Emily o los Weah), exprésalo siempre con suavidad como 'blindar la tranquilidad de casa y los sueños de los niños pase lo que pase' o 'darle más recorrido a vuestro futuro'.\n"
    "\nREGLA DE IDIOMA, RITMO ÁGIL Y FONÉTICA HISPANOHABLANTE NATIVA:\n"
    "- El usuario te habla en español: responde SIEMPRE en español de España (castellano peninsular nativo) con cercanía y naturalidad.\n"
    "- RITMO Y VELOCIDAD: Habla con ritmo RÁPIDO, ÁGIL, DINÁMICO Y CON ENERGÍA. Prohibido hablar lento, arrastrado o con pausas largas que duerman al cliente. Sé conciso (máximo 2 frases cortas y directas).\n"
    "- PROHIBIDO usar anglicismos crudos que rompan la pronunciación española en voz (NO escribas 'Score', 'Growth', 'Umbrella', 'cash flow' ni '$6,800' con formato anglosajón; di 'puntuación', 'crecimiento', 'póliza paraguas', 'flujo de caja' y '6.800 dólares').\n"
    "- Al mencionar nombres propios (como Timothy, Melanie, Liam, Josh, Michael, Daniel, Emily o Samantha), intégralos con entonación española natural sin cambiar tu acento al inglés."
)

ENGLISH_PROSODY_RULE = (
    "\nPOSITIVE PSYCHOLOGY & TONE RULE (ENGLISH):\n"
    "- Never use scary or judgmental words like 'critical', 'danger', 'death', or 'running out of money'. Reframe low scores as high-potential starting points and life cover as family peace of mind.\n"
    "- Keep a brisk, warm, energetic pace (maximum 2 short, clear sentences)."
)

STYLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "refranero": {
        "style_key": "refranero",
        "language": "es",
        "gemini_voice": "Zephyr",  # Voz fija en español para Weah (ágil, despierta y cercana)
        "openai_voice": "coral",
        "voice_id": "FGY2WhTYpPnrIDTdsKH5",  # ElevenLabs Multilingual v2 fija: Laura (directa sin fallos 404)
        "fallback_voice": "FGY2WhTYpPnrIDTdsKH5",
        "en_gemini_voice": "Aoede",  # Voz fija si cambia a inglés
        "en_openai_voice": "coral",
        "en_voice_id": "21m00Tcm4TlvDq8ikWAM",  # ElevenLabs EN fija: Rachel
        "tts_model": "eleven-multilingual-v2",
        "speech_speed": 1.20,
        "voice_name": "Laura / Zephyr (Voz Fija ES · Ágil y Cercana)",
        "en_voice_name": "Rachel / Aoede (Fixed Voice EN · Warm)",
        "style_label": "Ágil, Cercana y con Refranes",
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: ÁGIL, ENÉRGICO, CERCANO Y CON REFRANES POPULARES (para familias jóvenes con niños pequeños como Timothy y Melanie Weah que tienen poco tiempo y necesitan explicaciones vivas, rápidas y sin jerga bancaria).\n"
            "- Habla con mucha chispa, vitalidad y ritmo rápido: ve directo al grano en 2 frases cortas.\n"
            "- PROHIBIDO aburrir con porcentajes, tablas o cifras exactas. No recites números: explica la situación con metáforas de casa y familia ('tener tanto dinero parado en el banco mientras debéis la tarjeta es como tener un cubo con un agujero en el fondo').\n"
            "- Incluye de forma natural y ágil algún refrán tradicional español que venga al caso: 'más vale prevenir que curar', 'grano a grano se hace el granero', 'no se puede empezar la casa por el tejado'.\n"
            "- Usa palabras cotidianas y cercanas, transmitiendo energía y confianza para que tanto Timothy como Melanie quieran pasar a la acción hoy mismo."
            + SPANISH_NATIVE_PROSODY_RULE
        ),
    },
    "sencillo": {
        "style_key": "sencillo",
        "language": "es",
        "gemini_voice": "Puck",  # Voz fija en español para Carter / Johnson
        "openai_voice": "marin",
        "voice_id": "SAz9YHcvj6GT2YYXdXww",  # ElevenLabs Multilingual v2 fija: River (directa sin fallos 404)
        "fallback_voice": "SAz9YHcvj6GT2YYXdXww",
        "en_gemini_voice": "Puck",
        "en_openai_voice": "echo",
        "en_voice_id": "Xb7hH8MSUJpSbSDYk0k2",  # ElevenLabs EN fija: Alice
        "tts_model": "eleven-multilingual-v2",
        "speech_speed": 1.18,
        "voice_name": "River / Puck (Voz Fija ES · Dinámica y Sencilla)",
        "en_voice_name": "Alice / Puck (Fixed Voice EN · Plain & Direct)",
        "style_label": "Dinámico, Directo y Sin Tecnicismos",
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: SENCILLO, PRÁCTICO, RÁPIDO Y DIRECTO AL GRANO (para clientes sin estudios financieros que quieren claridad total sin rodeos).\n"
            "- CERO tecnicismos financieros y CERO porcentajes o listas de cifras. Habla con ritmo vivo en lenguaje llano y cotidiano, como si explicaras las cuentas de casa en la mesa de la cocina.\n"
            "- Usa comparaciones prácticas del día a día ('primero se tapa la gotera del techo antes de comprar muebles nuevos') y céntrate en cuál es el primer paso concreto que deben dar hoy."
            + SPANISH_NATIVE_PROSODY_RULE
        ),
    },
    "formal": {
        "style_key": "formal",
        "language": "es",
        "gemini_voice": "Kore",  # Voz fija en español para Samantha Lewis
        "openai_voice": "cedar",
        "voice_id": "XrExE9yKIg1WjnnlVkGX",  # ElevenLabs Multilingual v2 fija: Matilda (directa sin fallos 404)
        "fallback_voice": "XrExE9yKIg1WjnnlVkGX",
        "en_gemini_voice": "Charon",
        "en_openai_voice": "marin",
        "en_voice_id": "29vD33N1CtxCmqQRPOHJ",  # ElevenLabs EN fija: Drew
        "tts_model": "eleven-multilingual-v2",
        "speech_speed": 1.15,
        "voice_name": "Matilda / Kore (Voz Fija ES · Ejecutiva)",
        "en_voice_name": "Drew / Charon (Fixed Voice EN · Executive)",
        "style_label": "Formal, Ejecutivo y Ágil",
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: FORMAL, CULTO, EJECUTIVO Y FLUIDO (para un perfil directivo con alta cultura financiera).\n"
            "- Habla con elegancia, ritmo ejecutivo ágil y vocabulario estratégico propio de banca privada.\n"
            "- IMPORTANTE: Incluso en tono formal, NO recites listas de cifras ni porcentajes como un robot. Sintetiza el diagnóstico en una conclusión ejecutiva clara y rápida."
            + SPANISH_NATIVE_PROSODY_RULE
        ),
    },
}


def detect_user_language(user_text: Optional[str] = None, client_id: Optional[str] = None) -> str:
    """
    Detecta el idioma del mensaje del usuario ('es' o 'en').
    Si no se envía texto (ej. carga inicial), mantiene el último idioma activo del cliente
    (o 'es' por defecto). Solo cambia cuando el usuario realmente cambia de idioma.
    """
    cid = (client_id or "default").strip().lower()
    if not user_text or not user_text.strip():
        return _LAST_LANG_BY_CLIENT.get(cid, "es")

    sample = user_text.lower()
    if any(ch in sample for ch in ("¿", "¡", "á", "é", "í", "ó", "ú", "ñ")):
        _LAST_LANG_BY_CLIENT[cid] = "es"
        return "es"

    words = set(re.findall(r"[a-z]+", sample))
    english_markers = {
        "what", "how", "why", "should", "can", "would", "could", "our", "my",
        "the", "with", "first", "about", "explain", "plan", "house", "retire",
    }
    spanish_markers = {
        "que", "como", "por", "para", "este", "esto", "pacto", "activo",
        "cambia", "significa", "hola", "tarjeta", "casa", "nuestro", "mi",
    }
    en_hits = len(words & english_markers)
    es_hits = len(words & spanish_markers)
    if en_hits >= 2 and en_hits > es_hits:
        _LAST_LANG_BY_CLIENT[cid] = "en"
        return "en"

    _LAST_LANG_BY_CLIENT[cid] = "es"
    return "es"


def resolve_voice_profile(
    client_id: str,
    compact_context: Dict[str, Any],
    style_override: Optional[str] = None,
    user_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Selecciona y FIJA la voz para (client_id, idioma):
    - Una vez asignada la voz para un cliente y un idioma ('es' o 'en'), se mantiene
      exactamente la misma voz durante toda la sesión.
    - Únicamente cambia de voz si el usuario cambia de idioma ('es' <-> 'en') o fuerza otro estilo.
    """
    cid = (client_id or "timothy-melanie-weah").strip().lower()
    lang = detect_user_language(user_text, client_id=cid)
    style_tag = style_override if (style_override and style_override in STYLE_PROFILES) else "auto"
    lock_key = (cid, lang, style_tag)

    if lock_key in _LOCKED_VOICE_BY_CLIENT_LANG:
        return dict(_LOCKED_VOICE_BY_CLIENT_LANG[lock_key])

    if style_tag != "auto":
        base = dict(STYLE_PROFILES[style_tag])
    else:
        classification = (compact_context.get("classification") or "").upper()
        if "samantha" in cid or "lewis" in cid or "D5: VALIDATOR" in classification or "D6: DUTY" in classification:
            base = dict(STYLE_PROFILES["formal"])
        elif "carter" in cid or "johnson" in cid or "D6: FREEDOM" in classification or "D5: DUAL" in classification:
            base = dict(STYLE_PROFILES["sencillo"])
        else:
            base = dict(STYLE_PROFILES["refranero"])

    if lang == "en":
        base["gemini_voice"] = base["en_gemini_voice"]
        base["openai_voice"] = base["en_openai_voice"]
        base["voice_id"] = base["en_voice_id"]
        base["fallback_voice"] = base["en_voice_id"]
        base["tts_model"] = "eleven-flash-v2.5"
        base["voice_name"] = base["en_voice_name"]
        base["tone_instructions"] = (
            "Speak in natural, warm English tailored to this family's profile." + ENGLISH_PROSODY_RULE
        )

    base["detected_language"] = lang
    base["realtime_voice"] = base["gemini_voice"]

    _LOCKED_VOICE_BY_CLIENT_LANG[lock_key] = dict(base)
    return base

