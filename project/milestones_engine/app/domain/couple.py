"""The couple mode.

When two people share a plan they rarely want the same thing: one chases the
return, the other the peace of mind.  The mentor has to speak to both of them
and still help them decide together.

This module holds the rules of that conversation: what each risk profile is
after, how to address one partner instead of the other, and the bridge towards
a joint decision.
"""

from __future__ import annotations

from typing import Any

#: What each risk profile is after.
_FOCUS_BY_RISK = {
    "growth": (
        "Crecimiento, rentabilidad y coste de oportunidad fiscal/inversor"
    ),
    "moderate": "Seguridad familiar, colchón de liquidez y protección de los hijos",
    "conservative": "Preservación del capital, estabilidad y renta fija",
}

#: The bridge towards a joint decision, per household.
_CONSENSUS_BRIDGES = {
    "timothy-melanie-weah": (
        "Timothy (perfil Growth) busca que el dinero rinda y no perder un 18% en la tarjeta, "
        "mientras que Melanie (perfil Moderate) prioriza la seguridad de Liam y Josh con un gran "
        "colchón de liquidez. El punto de encuentro: usar solo una parte del efectivo excedente "
        "($60k sobre la reserva) para liquidar la tarjeta al 18% y cubrir el seguro de vida "
        "mantiene intacto el fondo de emergencia de Melanie y logra el retorno garantizado que "
        "busca Timothy, subiendo su Score de 60 a 73."
    ),
    "daniel-emily-johnson": (
        "Emily (perfil Moderate) gestiona todo el ahorro anual ($26k/año hacia bróker y 529 de "
        "los niños), mientras que Daniel (perfil Growth) figura en la tarjeta al 24.9% y ninguno "
        "aporta hoy al 401(k). El punto de encuentro: redirigir temporalmente parte del flujo "
        "hacia liquidar la tarjeta al 24.9% y asegurar la vida de ambos protege a Oliver y Sophia "
        "(prioridad de Emily) y libera flujo para activar el ahorro fiscal del 401(k) (prioridad "
        "de Daniel), subiendo el Score de 52 a 60."
    ),
}


def member_focus(risk_profile: str | None) -> str:
    """What a partner with this risk profile is after."""
    key = (risk_profile or "moderate").strip().lower()
    return _FOCUS_BY_RISK.get(key, _FOCUS_BY_RISK["moderate"])


def build_consensus_bridge(
    case_id: str, members: list[dict[str, Any]]
) -> str:
    """The bridge towards a decision the two of them can take together."""
    known = _CONSENSUS_BRIDGES.get(case_id)
    if known:
        return known
    if not members:
        return ""
    name = members[0].get("name") or "Cliente"
    return (
        f"Plan individual para {name}: alinear la liquidez de corto plazo "
        "con el perfil de largo plazo."
    )


def build_partner_instruction(
    couple: dict[str, Any], partner: str | None = None
) -> str:
    """How the mentor addresses the household.

    ``partner`` names one of the members (``timothy``, ``melanie``, ...) or
    asks for the couple mode (``both``, ``couple``, ``auto``).
    """
    members = couple.get("members") or []
    if not couple.get("is_couple") or len(members) < 2:
        if members:
            member = members[0]
            return (
                f"INTERLOCUTOR: Hablas directamente con {member['name']} "
                f"({member['age']} años, perfil de riesgo {member['risk_profile']})."
            )
        return ""

    first, second = members[0], members[1]
    wanted = (partner or "auto").strip().lower()

    for member, other in ((first, second), (second, first)):
        if wanted in (member.get("key"), member.get("role")):
            return (
                f"MODO PAREJA (HABLANDO AHORA CON {member['name'].upper()}):\n"
                f"- Estás hablando con {member['name']} ({member['age']} años, "
                f"perfil {member['risk_profile']}), cuya prioridad es: "
                f"{member['personal_focus']}.\n"
                f"- Su pareja es {other['name']} ({other['age']} años, perfil "
                f"{other['risk_profile']}), que prioriza: {other['personal_focus']}.\n"
                "- Adapta tus argumentos al enfoque de "
                f"{member['name']}, pero explícale cómo la recomendación también deja "
                f"tranquila a su pareja {other['name']} para que tomen la decisión juntos.\n"
                f"- PUENTE DE CONSENSO DE LA PAREJA: {couple.get('consensus_bridge', '')}"
            )

    return (
        f"MODO PAREJA ACTIVO ({first['name']} & {second['name']}):\n"
        f"- Este plan pertenece a DOS personas con visiones distintas: {first['name']} es "
        f"perfil {first['risk_profile']} ({first['personal_focus']}) y {second['name']} es "
        f"perfil {second['risk_profile']} ({second['personal_focus']}).\n"
        f"- Dirígete a ambos por sus nombres ({first['name']} y {second['name']}) de forma "
        "natural. Cuando expliques un paso, muestra en una frase por qué le encaja al lado "
        f"práctico/rentable de {first['name']} y por qué protege la tranquilidad que busca "
        f"{second['name']}.\n"
        f"- PUENTE DE CONSENSO: {couple.get('consensus_bridge', '')}"
    )
