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

# Criterio de idioma, psicología positiva (cero miedo), velocidad natural y dicción nativa
SPANISH_NATIVE_PROSODY_RULE = (
    "\nREGLA DE PSICOLOGÍA POSITIVA (SUAVIZAR NOTICIAS DIFÍCILES Y TEMAS SENSIBLES):\n"
    "- PROHIBIDO usar palabras alarmistas o que den miedo a actuar: NUNCA digas 'crítico', 'momento crítico', 'peligro', 'grave', 'gastas más de lo que ingresas', 'muerte', 'fallecimiento' ni 'quedarte sin dinero en la vejez'.\n"
    "- Si la puntuación es baja (ej. 26 de Michael Carter), empieza validando lo que hace bien ('ahorras muchísimo cada año') y preséntalo como una oportunidad sencilla de sincronizar sus metas para saltar a 62 puntos.\n"
    "- Al hablar de seguro de vida o jubilación (ej. Daniel y Emily o los Weah), exprésalo siempre con suavidad como 'blindar la tranquilidad de casa y los sueños de los niños pase lo que pase' o 'darle más recorrido a vuestro futuro'.\n"
    "\nREGLA DE IDIOMA, VELOCIDAD NORMAL Y FONÉTICA HISPANOHABLANTE NATIVA:\n"
    "- El usuario te habla en español: responde SIEMPRE en español de España (castellano peninsular nativo) con cercanía y naturalidad.\n"
    "- VELOCIDAD Y BREVEDAD: Habla a velocidad normal, tranquila y conversacional. Sé muy conciso: responde en MÁXIMO 2 frases breves (menos de 40 palabras en total) para que sea directo y natural.\n"
    "- PROHIBIDO usar anglicismos crudos que rompan la pronunciación española en voz (NO escribas 'Score', 'Growth', 'Umbrella', 'cash flow' ni '$6,800' con formato anglosajón; di 'puntuación', 'crecimiento', 'póliza paraguas', 'flujo de caja' y '6800 dólares').\n"
    "- Al mencionar nombres propios (como Timothy, Melanie, Liam, Josh, Michael, Daniel, Emily o Samantha), intégralos con entonación española natural sin cambiar tu acento al inglés."
)

ENGLISH_PROSODY_RULE = (
    "\nPOSITIVE PSYCHOLOGY & TONE RULE (ENGLISH):\n"
    "- Never use scary or judgmental words like 'critical', 'danger', 'death', or 'running out of money'. Reframe low scores as high-potential starting points and life cover as family peace of mind.\n"
    "- Speak at a natural, calm conversational pace in at most 2 short, clear sentences (under 40 words total)."
)

CHINESE_PROSODY_RULE = (
    "\n中文积极心理学与自然语音规则 (CHINESE MANDARIN RULE):\n"
    "- 用户正在用中文与你交流：请务必全程使用地道、自然、流利的简体中文（普通话）回答，绝不要夹杂生硬的英文缩写（如把 'Score' 说成 '财务健康评分'，把 '$6,800' 说成 '六千八百美元'）。\n"
    "- 严禁使用制造焦虑或恐吓性的词汇（不要说“危急”、“危险”、“死亡”或“破产”）。用积极、温暖的方式表达（例如将保险称为“给孩子和家庭的安心保障”）。\n"
    "- 语速自然平和，每次回答控制在 2 句简短直接的话以内。"
)

STYLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "refranero": {
        "style_key": "refranero",
        "language": "es",
        "gemini_voice": "Zephyr",
        "openai_voice": "coral",
        "voice_id": "yiWEefwu5z3DQCM79clN",  # ElevenLabs ES Nativa (es-ES): Laura López (Bright, Clear and Dynamic)
        "fallback_voice": "UOIqAnmS11Reiei1Ytkc",  # ElevenLabs ES Nativa (es-ES): Carolina
        "en_gemini_voice": "Aoede",
        "en_openai_voice": "coral",
        "en_voice_id": "EXAVITQu4vr4xnSDxMaL",  # ElevenLabs EN: Sarah (cálida, acento americano cercano)
        "zh_voice_id": "cgSgspJ2msm6clMCkdW9",  # ElevenLabs ZH: Jessica (cálida, cercana y expresiva en mandarín)
        "tts_model": "eleven_multilingual_v2",
        "speech_speed": 1.0,
        "stability": 0.48,
        "similarity_boost": 0.78,
        "style_weight": 0.22,
        "voice_name": "Laura López · ElevenLabs (ES Nativa · Cercana)",
        "en_voice_name": "Sarah · ElevenLabs (EN · Warm American)",
        "zh_voice_name": "Jessica · ElevenLabs (ZH · 亲切温暖)",
        "style_label": "Cercana, Cálida y Cotidiana",
        "compact_tone_hint": "Asesor Sherpas Wealth. Español de España cálido, cercano y natural, sin jerga ni refranes forzados. Máx 2 frases breves (<35 palabras). Tono positivo, sin alarmismos. Responde en el idioma del usuario.",
        "zh_tone_instructions": (
            "语言风格：亲切、自然、温暖（适合像 Timothy 和 Melanie 这样有年幼孩子的年轻家庭）。\n"
            "- 用通俗易懂的日常生活语言解释财务问题，不要堆砌成语或俗语。"
            + CHINESE_PROSODY_RULE
        ),
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: CERCANO, CÁLIDO Y COTIDIANO (para familias jóvenes con niños pequeños como Timothy y Melanie Weah que agradecen explicaciones humanas y sin jerga bancaria).\n"
            "- Habla con naturalidad, empatía y tono conversacional normal en máximo 2 frases breves.\n"
            "- Explica las finanzas con lenguaje claro de casa y familia, sin tecnicismos fríos.\n"
            "- IMPORTANTE (SUAVIDAD): NO abuses de refranes populares ni encadenes frases hechas como 'coser y cantar' o 'más vale prevenir que curar' que suenen forzadas o exageradas. Puedes usar una imagen cotidiana sencilla solo cuando ayude de forma natural, manteniendo siempre la elegancia y credibilidad de un buen asesor."
            + SPANISH_NATIVE_PROSODY_RULE
        ),
    },
    "familiar": {
        "style_key": "familiar",
        "language": "es",
        "gemini_voice": "Aoede",
        "openai_voice": "sage",
        "voice_id": "UOIqAnmS11Reiei1Ytkc",  # ElevenLabs ES Nativa (es-ES): Carolina (Natural, Neutral and Clear)
        "fallback_voice": "yiWEefwu5z3DQCM79clN",  # ElevenLabs ES Nativa (es-ES): Laura López
        "en_gemini_voice": "Aoede",
        "en_openai_voice": "sage",
        "en_voice_id": "Xb7hH8MSUJpSbSDYk0k2",  # ElevenLabs EN: Alice (educadora clara, acento británico)
        "zh_voice_id": "cgSgspJ2msm6clMCkdW9",  # ElevenLabs ZH: Jessica
        "tts_model": "eleven_multilingual_v2",
        "speech_speed": 1.0,
        "stability": 0.50,
        "similarity_boost": 0.78,
        "style_weight": 0.18,
        "voice_name": "Carolina · ElevenLabs (ES Nativa · Familiar)",
        "en_voice_name": "Alice · ElevenLabs (EN · British Educator)",
        "zh_voice_name": "Jessica · ElevenLabs (ZH · 温和家庭顾问)",
        "style_label": "Empático, Familiar y Mediador",
        "compact_tone_hint": "Asesor Sherpas Wealth. Español de España empático y familiar, conciliando a ambos miembros de la pareja sin tecnicismos. Máx 2 frases breves (<35 palabras). Tono positivo. Responde en el idioma del usuario.",
        "zh_tone_instructions": (
            "语言风格：温和、共情、注重家庭平衡（适合像 Daniel 和 Emily 这样需要兼顾孩子大学教育与自身退休的夫妻）。\n"
            "- 用通俗温暖的家庭比喻回答，帮助夫妻双方达成共识，在两句话内给出清晰建议。"
            + CHINESE_PROSODY_RULE
        ),
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: EMPÁTICO, FAMILIAR, EQUILIBRADO Y PEDAGÓGICO (para parejas como Daniel y Emily Johnson que buscan conciliar la universidad de sus hijos con su propia jubilación).\n"
            "- Habla con calidez serena, sin tecnicismos y dando tranquilidad a ambos miembros de la pareja en 2 frases claras.\n"
            "- Usa ejemplos familiares cotidianos de forma natural y equilibrada."
            + SPANISH_NATIVE_PROSODY_RULE
        ),
    },
    "sencillo": {
        "style_key": "sencillo",
        "language": "es",
        "gemini_voice": "Puck",
        "openai_voice": "marin",
        "voice_id": "Nh2zY9kknu6z4pZy6FhD",  # ElevenLabs ES Nativa (España): David Martín 1 (directo, práctico, masculino cercano)
        "fallback_voice": "fXcll5SYKmCCtKLLpepe",  # ElevenLabs ES Nativa (España): José (cálido y humano)
        "en_gemini_voice": "Puck",
        "en_openai_voice": "echo",
        "en_voice_id": "JBFqnCBsd6RMkjVDRZzb",  # ElevenLabs EN: George (narrador cercano, acento británico masculino)
        "zh_voice_id": "nPczCjzI2devNBz1zQrb",  # ElevenLabs ZH: Brian (voz masculina clara, directa y confiable en mandarín)
        "tts_model": "eleven_multilingual_v2",
        "speech_speed": 1.0,
        "stability": 0.48,
        "similarity_boost": 0.78,
        "style_weight": 0.18,
        "voice_name": "David Martín · ElevenLabs (ES Nativo · Directo)",
        "en_voice_name": "George · ElevenLabs (EN · British Storyteller)",
        "zh_voice_name": "Brian · ElevenLabs (ZH · 务实直接 · 沉稳男声)",
        "style_label": "Práctico, Directo y Sin Tecnicismos",
        "compact_tone_hint": "Asesor Sherpas Wealth. Español de España llano, directo y práctico, cero jerga ni listas de cifras. Máx 2 frases breves (<35 palabras). Tono positivo. Responde en el idioma del usuario.",
        "zh_tone_instructions": (
            "语言风格：直截了当、通俗务实、零金融术语（适合像 Michael Carter 这样希望在买房和提前退休之间理清思路的客户）。\n"
            "- 像朋友喝咖啡聊天一样，直接告诉他第一步该做什么。"
            + CHINESE_PROSODY_RULE
        ),
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: SENCILLO, PRÁCTICO Y DIRECTO AL GRANO (para clientes como Michael Carter que quieren claridad total entre dos grandes metas sin rodeos).\n"
            "- CERO tecnicismos financieros y CERO listas de cifras. Habla en lenguaje llano y natural, como si explicaras las cuentas de casa tomando un café.\n"
            "- Céntrate con claridad en cuál es el primer paso concreto que debe dar hoy."
            + SPANISH_NATIVE_PROSODY_RULE
        ),
    },
    "formal": {
        "style_key": "formal",
        "language": "es",
        "gemini_voice": "Kore",
        "openai_voice": "cedar",
        "voice_id": "tXgbXPnsMpKXkuTgvE3h",  # ElevenLabs ES Nativa (es-ES): Elena (Resolute, Engaging and Lively)
        "fallback_voice": "erKgR0s8Y67t4iiHuA9R",  # ElevenLabs ES Nativa (España): Martín Osborne 7
        "en_gemini_voice": "Charon",
        "en_openai_voice": "marin",
        "en_voice_id": "onwK4e9ZLuTAKqWW03F9",  # ElevenLabs EN: Daniel (formal, distinguido, acento británico ejecutivo)
        "zh_voice_id": "cjVigY5qzO86Huf0OWal",  # ElevenLabs ZH: Eric (voz ejecutiva y de banca privada en mandarín)
        "tts_model": "eleven_multilingual_v2",
        "speech_speed": 1.0,
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style_weight": 0.15,
        "voice_name": "Elena · ElevenLabs (ES Nativa · Ejecutiva)",
        "en_voice_name": "Daniel · ElevenLabs (EN · Executive British)",
        "zh_voice_name": "Eric · ElevenLabs (ZH · 私人银行高管顾问)",
        "style_label": "Formal, Ejecutivo y Estratégico",
        "compact_tone_hint": "Asesor Sherpas Wealth. Español de España ejecutivo, elegante y estratégico de banca privada. Máx 2 frases breves (<35 palabras). Tono constructivo. Responde en el idioma del usuario.",
        "zh_tone_instructions": (
            "语言风格：专业、优雅、高管私人银行水准（适合像 Samantha Lewis 这样具有深厚财务素养的高净值客户）。\n"
            "- 用凝练、战略性的语言给出执行结论，不要机械地罗列数字。"
            + CHINESE_PROSODY_RULE
        ),
        "tone_instructions": (
            "REGISTRO DE LENGUAJE: FORMAL, CULTO, EJECUTIVO Y FLUIDO (para un perfil directivo con alta cultura financiera como Samantha Lewis).\n"
            "- Habla con elegancia, serenidad y vocabulario estratégico propio de banca privada.\n"
            "- IMPORTANTE: Incluso en tono formal, NO recites listas de cifras ni porcentajes como un robot. Sintetiza el diagnóstico en una conclusión ejecutiva clara."
            + SPANISH_NATIVE_PROSODY_RULE
        ),
    },
}


def detect_user_language(user_text: Optional[str] = None, client_id: Optional[str] = None) -> str:
    """
    Detecta el idioma del mensaje del usuario ('es', 'en' o 'zh' para chino mandarín).
    Si no se envía texto (ej. carga inicial), mantiene el último idioma activo del cliente
    (o 'es' por defecto). Solo cambia cuando el usuario realmente cambia de idioma.
    """
    cid = (client_id or "default").strip().lower()
    if not user_text or not user_text.strip():
        return _LAST_LANG_BY_CLIENT.get(cid, "es")

    sample = user_text.lower()

    # 1. Detección de Chino Mandarín (caracteres CJK o pinyin común)
    if re.search(r"[\u4e00-\u9fff]", sample):
        _LAST_LANG_BY_CLIENT[cid] = "zh"
        return "zh"

    if any(ch in sample for ch in ("¿", "¡", "á", "é", "í", "ó", "ú", "ñ")):
        _LAST_LANG_BY_CLIENT[cid] = "es"
        return "es"

    words = set(re.findall(r"[a-z]+", sample))
    chinese_pinyin_markers = {"nihao", "zhongwen", "shenme", "zenme", "women", "xiexie"}
    if words & chinese_pinyin_markers or "ni hao" in sample:
        _LAST_LANG_BY_CLIENT[cid] = "zh"
        return "zh"

    english_markers = {
        "what", "how", "why", "when", "where", "who", "which", "should", "can", "would",
        "could", "our", "my", "the", "with", "first", "about", "explain", "plan",
        "house", "home", "retire", "retirement", "hello", "hi", "hey", "please", "tell",
        "me", "help", "does", "do", "did", "is", "are", "your", "you", "we", "this",
        "that", "have", "has", "will", "from", "save", "saving", "savings", "card",
        "credit", "money", "cash", "debt", "score", "tax", "taxes", "kids", "children",
        "family", "wife", "husband", "much", "many", "best", "start", "need", "want",
    }
    spanish_markers = {
        "que", "como", "por", "para", "este", "esto", "esta", "pacto", "activo",
        "cambia", "significa", "hola", "buenas", "tarjeta", "casa", "nuestro", "nuestra",
        "mi", "mis", "cual", "donde", "cuando", "seguro", "dinero", "ahorro", "ahorrar",
        "paso", "hijos", "familia", "jubilacion", "jubilarme", "efectivo", "deuda",
        "impuestos", "hacemos", "hago", "puedo", "podemos", "conviene", "explicame",
    }
    en_hits = len(words & english_markers)
    es_hits = len(words & spanish_markers)
    if en_hits > es_hits and (en_hits >= 2 or (en_hits >= 1 and es_hits == 0)):
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
    - Una vez asignada la voz para un cliente y un idioma ('es', 'en' o 'zh'), se mantiene
      exactamente la misma voz durante toda la sesión.
    - Únicamente cambia de voz si el usuario cambia de idioma ('es' <-> 'en' <-> 'zh') o fuerza otro estilo.
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
        elif "johnson" in cid or "daniel" in cid or "emily" in cid:
            base = dict(STYLE_PROFILES["familiar"])
        elif "carter" in cid or "michael" in cid or "D6: FREEDOM" in classification or "D5: DUAL" in classification:
            base = dict(STYLE_PROFILES["sencillo"])
        else:
            base = dict(STYLE_PROFILES["refranero"])

    if lang == "en":
        base["gemini_voice"] = base["en_gemini_voice"]
        base["openai_voice"] = base["en_openai_voice"]
        base["voice_id"] = base["en_voice_id"]
        base["fallback_voice"] = base["en_voice_id"]
        base["tts_model"] = "eleven_multilingual_v2"
        base["voice_name"] = base["en_voice_name"]
        base["tone_instructions"] = (
            "Speak in natural, warm English tailored to this family's profile." + ENGLISH_PROSODY_RULE
        )
        base["compact_tone_hint"] = (
            "Sherpas Wealth advisor. Reply in warm, clear English in <=2 short sentences (<35 words). Positive tone, no scary words."
        )
    elif lang == "zh":
        base["voice_id"] = base.get("zh_voice_id", base["voice_id"])
        base["fallback_voice"] = base.get("zh_voice_id", base["fallback_voice"])
        base["tts_model"] = "eleven_multilingual_v2"
        base["voice_name"] = base.get("zh_voice_name", base["voice_name"])
        base["tone_instructions"] = base.get("zh_tone_instructions", CHINESE_PROSODY_RULE)
        base["compact_tone_hint"] = (
            "Sherpas Wealth 顾问。用温和自然的简体中文在2句内（35字以内）直接回答，不吓唬用户。"
        )

    base["detected_language"] = lang
    base["realtime_voice"] = base["voice_name"]

    _LOCKED_VOICE_BY_CLIENT_LANG[lock_key] = dict(base)
    return base

