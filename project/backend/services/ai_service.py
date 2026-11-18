"""
services/ai_service.py
----------------------
Servicio de inteligencia artificial, Mapa de Viaje gamificado, Simulador 'What-If',
Mentor Proactivo + Traductor de Jerga, Modo Multijugador Familiar y Vídeo Introductorio.
"""

import os
import re
import json
import asyncio
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config import llm_client, ELEVENLABS_API_KEY
from mcp_client import (
    normalize_case_id,
    get_short_id,
    get_section,
    get_compact_client_context,
    get_couple_dynamics,
)
from models import (
    PathSchema,
    Nivel,
    GoalStop,
    CelebrationInfo,
    CoupleOverview,
    CoupleMember,
    KidsGoalItem,
    HighFiveItem,
    DecisionPowerUp,
    TimelineComparison,
    PactCard,
    SimulatorResponse,
    JargonPill,
    ProactiveInsight,
    MentorInsightsResponse,
    StorySchema,
    StoryScene,
)
from services.voice_profiles import resolve_voice_profile

# Integración con el motor de hitos persistente y AI-powered
try:
    from app.config import get_settings
    from app.db.session import get_session_factory
    from app.models.milestone import Milestone
    from app.repositories import milestone_repository
    from app.services import case_service, generation_service
    from app.api.deps import case_source_dependency, ai_service_dependency
except Exception as _err_import_app:
    get_settings = None
    get_session_factory = None
    Milestone = None
    milestone_repository = None
    case_service = None
    generation_service = None
    case_source_dependency = None
    ai_service_dependency = None

GET_CASE_PARAM_SCHEMA = {
    "type": "object",
    "properties": {
        "part": {
            "type": "string",
            "enum": ["financial-health", "investment-analysis", "persona"],
        },
        "section": {
            "type": "string",
            "enum": [
                "score",
                "goals",
                "profile",
                "narrative",
                "projections",
                "key_metrics",
                "positions",
                "analysis",
                "D0",
                "D1",
                "D2",
                "D3",
                "D4",
                "D5",
                "D6",
                "Transition alerts",
                "Objective concerns",
                "Tensions",
            ],
            "description": "Sección: 'positions' (ETFs/cartera), 'projections' (hitos anuales), 'profile' (cuentas/deudas/seguros), 'goals', 'key_metrics', 'Tensions'.",
        },
        "sub_section": {
            "type": "string",
            "description": "Sub-clave opcional de profile ('incomes','expenses','accounts','liabilities','insurance') o key_metrics ('debtManagement','protection','cashflowStatement','retirementAndOtherGoals','portfolioAnalysis','taxDragAnalysis').",
        },
    },
    "required": ["part", "section"],
}

CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_case",
            "description": "Consulta una sección o sub-sección del expediente financiero del cliente.",
            "parameters": GET_CASE_PARAM_SCHEMA,
        },
    }
]

REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "get_case",
        "description": "Úsala SOLO si el cliente pide un detalle que no está en el brief inicial (ej. tickers en 'positions', año concreto en 'projections' o impuestos en 'taxDragAnalysis').",
        "parameters": GET_CASE_PARAM_SCHEMA,
    }
]

# Estado en memoria de los hitos por cliente y muro de High-Fives familiares
_MILESTONE_STATE: Dict[str, Dict[int, str]] = {}
_LAST_CELEBRATION: Dict[str, CelebrationInfo] = {}
_HIGH_FIVES_STATE: Dict[str, List[HighFiveItem]] = {}

# Traducciones y contexto humano empático en español para los hitos reales de las 4 familias
MOVE_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "Pay down revolving card": {
        "titulo": "Cerrar la pequeña fuga: reducir el tramo caro de la tarjeta al 18%",
        "descripcion": "Destinar solo $6,800 de vuestros $150,800 en efectivo para bajar el saldo de la tarjeta Chase (18% TAE) y quitar el primer freno del Score.",
        "por_que_importa": "Os ahorráis $3,240/año en intereses usando una pequeña parte del efectivo que hoy rinde un 0.1%. Para Timothy es un 18% de retorno garantizado y para Melanie sigue quedando un colchón enorme de seguridad.",
        "pregunta_mentor": "¿Cómo nos ayuda usar $6,800 del efectivo sobrante para quitar la tarjeta al 18% manteniendo intacta nuestra tranquilidad?",
    },
    "Add life cover": {
        "titulo": "Tejer una red de tranquilidad familiar para Liam y Josh",
        "descripcion": "Sumar $235,000 de respaldo familiar para alcanzar el nivel recomendado ($485,000) y desbloquear el segundo impulso de vuestro Score.",
        "por_que_importa": "Al combinar el ajuste de la tarjeta con este respaldo familiar, vuestro Score da un salto directo de 60 a 73 puntos y los proyectos de los niños quedan siempre garantizados.",
        "pregunta_mentor": "¿Por qué nuestro Score da un salto tan positivo de 60 a 73 al unir el ajuste de la tarjeta con el respaldo familiar?",
    },
    "Add umbrella cover": {
        "titulo": "Activar paraguas de tranquilidad patrimonial ($1M Umbrella)",
        "descripcion": "Incorporar una póliza paraguas (Umbrella) de $1,000,000 para cuidar vuestro patrimonio y ahorros con total serenidad.",
        "por_que_importa": "Es un escudo muy sencillo y económico que mantiene a salvo todo el esfuerzo que habéis construido.",
        "pregunta_mentor": "¿Qué es exactamente la póliza paraguas de $1 millón y cómo nos ayuda a estar más tranquilos?",
    },
    "Lower the withdrawal rate": {
        "titulo": "Sincronizar el ritmo entre tu casa de 2027 y tu retiro a los 58",
        "descripcion": "Acompasar las retiradas futuras hacia la banda cómoda ($10,300/año, 6.0%) para que tu ahorro te acompañe con holgura hasta los 91 años.",
        "por_que_importa": "Ahorras $43,000 al año con una disciplina admirable; solo necesitas acompasar el ritmo con la compra de tu casa en enero de 2027 para dar un salto directo de 26 a 62 puntos.",
        "pregunta_mentor": "¿Cómo acompasamos la compra de mi casa de $550,000 en 2027 para poder jubilarme con tranquilidad a los 58 años?",
    },
    "Raise growth allocation toward glide": {
        "titulo": "Poner tu cartera a trabajar a favor de tus 20 años de horizonte",
        "descripcion": "Pasar el peso de crecimiento del 74% al 88% (~$19,900 de tu cartera invertida) para impulsar tu retiro temprano.",
        "por_que_importa": "Aprovechas tus 20 años de margen hasta la jubilación y reduces impuestos anuales recolocando el fondo JNK.",
        "pregunta_mentor": "¿Qué ajustes sencillos puedo hacer en mis fondos para que mi dinero crezca mejor de cara a los 58 años?",
    },
    "Raise mortality coverage": {
        "titulo": "Blindar la tranquilidad del hogar y el futuro de Oliver y Sophia",
        "descripcion": "Ampliar el respaldo familiar en $1,166,000 para que los proyectos y estudios de los niños estén siempre garantizados.",
        "por_que_importa": "Vuestro hogar cuenta con dos grandes sueldos ($280,000/año). Poner esta red de tranquilidad familiar suma +5 puntos inmediatos al plan y os da paz mental.",
        "pregunta_mentor": "¿Cómo organizamos esta red de protección familiar entre Daniel y Emily de forma cómoda cada mes?",
    },
    "Raise annual savings": {
        "titulo": "Aprovechar vuestro margen anual para ahorrar impuestos y quitar la tarjeta",
        "descripcion": "Canalizar los $15,032/año de margen libre hacia vuestros planes 401(k) y reducir la tarjeta al 24.9%.",
        "por_que_importa": "Unís el gran hábito ahorrador de Emily con un descuento fiscal de hasta $11,760/año en los 401(k) y os quitáis los intereses de la tarjeta.",
        "pregunta_mentor": "¿Cómo ordenamos nuestro margen anual entre la tarjeta, el 401(k) y el fondo de los niños para ganar tranquilidad?",
    },
    "Close a coverage gap": {
        "titulo": "Registrar la cobertura de tu vivienda de $900,000",
        "descripcion": "Incorporar la póliza de hogar de tu vivienda principal libre de hipoteca para completar tu escudo patrimonial.",
        "por_que_importa": "Tu casa es el pilar central de tu patrimonio ($900,000 de $1,395,000). Registrarla sube tu Score directamente de 82 a 84.",
        "pregunta_mentor": "Con mi Score de 82, ¿cómo alargamos la comodidad de mi liquidez más allá de los 73 años y completamos el seguro de mi casa?",
    },
    "Reduce single-name concentration": {
        "titulo": "Diversificar VTI y aprovechar cuentas con ventaja fiscal",
        "descripcion": "Equilibrar el peso de VTI del 39% al 25% (~$58,300) y estrenar cuentas con ventaja fiscal (IRA/HSA).",
        "por_que_importa": "Tu capacidad de ahorro de $60,000/año es excelente; sumarle ventaja fiscal te ahorra ~$3,032/año en impuestos y alarga tu liquidez hasta los 90 años.",
        "pregunta_mentor": "¿Cómo puedo ahorrar esos $3,032 anuales en impuestos y organizar con calma la universidad de Ethan y Ava?",
    },
    "Reduce growth allocation toward glide": {
        "titulo": "Dar estabilidad a tu cartera (80%) para las etapas universitarias",
        "descripcion": "Ajustar suavemente la renta variable del 85% al 80% (~$17,100) para tener liquidez serena en 2027 y 2028.",
        "por_que_importa": "Acompaña con total tranquilidad los pagos universitarios de Ethan (2027) y Ava (2028) y tu futura casa en 2030.",
        "pregunta_mentor": "¿Cómo equilibramos mi cartera para afrontar con total comodidad los pagos de universidad de 2027 y 2028?",
    },
}

# Paradas de Metas Vitales (Diseño por Metas, no por Activos)
GOAL_STOPS_BY_CASE: Dict[str, List[Dict[str, Any]]] = {
    "timothy-melanie-weah": [
        {
            "goal_id": "weah-vacations",
            "icono": "🏖️",
            "titulo": "Vacaciones familiares con Liam y Josh",
            "anio_objetivo": "Cada año",
            "importe_objetivo": "$6,000 / año",
            "progreso_porcentaje": 100,
            "mensaje_familiar": "¡Meta cubierta! Vuestra reserva actual garantiza los viajes familiares.",
        },
        {
            "goal_id": "weah-car",
            "icono": "🚙",
            "titulo": "Nuevo coche familiar",
            "anio_objetivo": "2028",
            "importe_objetivo": "$45,000",
            "progreso_porcentaje": 75,
            "mensaje_familiar": "El efectivo excedente ($60,222) permite cubrirlo sin pedir otro préstamo.",
        },
        {
            "goal_id": "weah-home",
            "icono": "🏡",
            "titulo": "Nuestra próxima casa en California",
            "anio_objetivo": "2030",
            "importe_objetivo": "$600,000",
            "progreso_porcentaje": 45,
            "mensaje_familiar": "Quitar la tarjeta al 18% hoy libera capacidad para la entrada de 2030.",
        },
        {
            "goal_id": "weah-college",
            "icono": "🎓",
            "titulo": "Universidad de Liam (2038) y Josh (2041)",
            "anio_objetivo": "2038 - 2041",
            "importe_objetivo": "$113,508",
            "progreso_porcentaje": 15,
            "mensaje_familiar": "Aportando $384/mes a un plan 529 llegáis al 100% cuando Liam cumpla 18 años.",
        },
    ],
    "michael-carter": [
        {
            "goal_id": "carter-home",
            "icono": "🏠",
            "titulo": "Comprar mi primera casa en Austin",
            "anio_objetivo": "Enero 2027",
            "importe_objetivo": "$550,000 (Entrada $113,300)",
            "progreso_porcentaje": 26,
            "mensaje_familiar": "Tienes $30,000 en liquidez; el resto saldría de tu cartera si compras ya en enero.",
        },
        {
            "goal_id": "carter-vacation",
            "icono": "✈️",
            "titulo": "Viaje anual de desconexión",
            "anio_objetivo": "2027 - 2047",
            "importe_objetivo": "$3,500 / año",
            "progreso_porcentaje": 80,
            "mensaje_familiar": "Sostenible en cuanto equilibremos el flujo de caja anual (-$8,336).",
        },
        {
            "goal_id": "carter-retire",
            "icono": "🌅",
            "titulo": "Libertad financiera a los 58 años",
            "anio_objetivo": "2047 (Edad 58)",
            "importe_objetivo": "$89,649 / año",
            "progreso_porcentaje": 64,
            "mensaje_familiar": "Hoy el ahorro cubre hasta los 85 años; ajustando el plan llegas hasta los 91.",
        },
    ],
    "daniel-emily-johnson": [
        {
            "goal_id": "johnson-vacation",
            "icono": "⛰️",
            "titulo": "Vacaciones familiares en familia",
            "anio_objetivo": "Enero 2027",
            "importe_objetivo": "$4,500 / año",
            "progreso_porcentaje": 85,
            "mensaje_familiar": "Cubierto con vuestro flujo de caja positivo de $15,032/año.",
        },
        {
            "goal_id": "johnson-college",
            "icono": "🎓",
            "titulo": "Universidad de Oliver (2033) y Sophia (2035)",
            "anio_objetivo": "2033 - 2035",
            "importe_objetivo": "$120,000 ($60k c/u)",
            "progreso_porcentaje": 42,
            "mensaje_familiar": "¡Ya tenéis $30,000 en el plan 529 y Emily aporta $8,000 cada año!",
        },
        {
            "goal_id": "johnson-retire",
            "icono": "🌲",
            "titulo": "Jubilación conjunta de Daniel (62) y Emily (60)",
            "anio_objetivo": "2044",
            "importe_objetivo": "$124,071 / año",
            "progreso_porcentaje": 55,
            "mensaje_familiar": "Activando los 401(k) aprovecháis hasta $11,760/año en ahorro de impuestos.",
        },
    ],
    "samantha-lewis": [
        {
            "goal_id": "lewis-college-ethan",
            "icono": "🎓",
            "titulo": "Universidad de Ethan (en curso) y Ava (2028)",
            "anio_objetivo": "2026 - 2032",
            "importe_objetivo": "$100,000 ($50k c/u)",
            "progreso_porcentaje": 35,
            "mensaje_familiar": "Cuentas custodias con $20,000 (Ethan) y $15,000 (Ava) listas para apoyar.",
        },
        {
            "goal_id": "lewis-home",
            "icono": "🏖️",
            "titulo": "Nueva residencia en 2030",
            "anio_objetivo": "2030",
            "importe_objetivo": "$500,000",
            "progreso_porcentaje": 70,
            "mensaje_familiar": "Tu vivienda actual de $900,000 está 100% libre de hipoteca.",
        },
        {
            "goal_id": "lewis-retire",
            "icono": "🏛️",
            "titulo": "Jubilación ejecutiva sostenible (65 a 91 años)",
            "anio_objetivo": "2044 (Edad 65)",
            "importe_objetivo": "$153,672 / año",
            "progreso_porcentaje": 58,
            "mensaje_familiar": "Pasando ahorro del bróker a cuentas de jubilación extiendes tu capital más allá de los 73 años.",
        },
    ],
}

# Vista Segura para Hijos (Modo Multijugador Familiar: oculta deudas, sueldos y patrimonio total)
KIDS_SAFE_GOALS_BY_CASE: Dict[str, List[Dict[str, Any]]] = {
    "timothy-melanie-weah": [
        {
            "id": "kids-vacation",
            "icono": "🎢",
            "titulo_amigable": "Nuestro gran viaje de vacaciones en familia",
            "meta_visual": "¡Hucha al 100% para este año!",
            "progreso_porcentaje": 100,
            "explicacion_ninos": "Papá y mamá ya han llenado la hucha para nuestras próximas vacaciones juntos.",
        },
        {
            "id": "kids-college-liam-josh",
            "icono": "🚀",
            "titulo_amigable": "El fondo para el futuro de Liam (6) y Josh (3)",
            "meta_visual": "Semilla plantada · Creciendo cada mes",
            "progreso_porcentaje": 25,
            "explicacion_ninos": "Cada vez que ahorramos en casa, esta planta crece para cuando vayáis a la universidad.",
        },
        {
            "id": "kids-car",
            "icono": "🚐",
            "titulo_amigable": "El nuevo coche familiar de 2028",
            "meta_visual": "3 de 4 ruedas listas",
            "progreso_porcentaje": 75,
            "explicacion_ninos": "Ahorrar sin pedir prestado nos ayuda a tener un coche nuevo para nuestras excursiones.",
        },
    ],
    "daniel-emily-johnson": [
        {
            "id": "kids-oliver-sophia-college",
            "icono": "🎓",
            "titulo_amigable": "La hucha universitaria de Oliver (11) y Sophia (9)",
            "meta_visual": "¡Ya lleva $30,000 ahorrados!",
            "progreso_porcentaje": 45,
            "explicacion_ninos": "Todos los años sumamos más a vuestra cuenta 529 para que podáis estudiar lo que os apasione.",
        },
        {
            "id": "kids-denver-trip",
            "icono": "🏕️",
            "titulo_amigable": "Vacaciones de invierno en enero de 2027",
            "meta_visual": "¡Casi completa!",
            "progreso_porcentaje": 88,
            "explicacion_ninos": "Cuidar el presupuesto de casa cada mes hace que nuestras vacaciones en familia sean posibles.",
        },
    ],
    "samantha-lewis": [
        {
            "id": "kids-ethan-ava",
            "icono": "🎓",
            "titulo_amigable": "Cuentas de futuro de Ethan (18) y Ava (16)",
            "meta_visual": "$35,000 en vuestras cuentas de inversión",
            "progreso_porcentaje": 60,
            "explicacion_ninos": "Vuestras cuentas custodias están invertidas en las mayores empresas del mundo para impulsar vuestra etapa universitaria.",
        },
        {
            "id": "kids-miami-vacation",
            "icono": "🌴",
            "titulo_amigable": "Escapada anual en familia",
            "meta_visual": "Lista para 2027",
            "progreso_porcentaje": 95,
            "explicacion_ninos": "Una meta compartida para celebrar el cierre de cada curso académico.",
        },
    ],
    "michael-carter": [
        {
            "id": "kids-home-goal",
            "icono": "🏡",
            "titulo_amigable": "Meta: Mi futura casa en Austin (2027)",
            "meta_visual": "Construyendo los cimientos",
            "progreso_porcentaje": 35,
            "explicacion_ninos": "Vista simplificada de metas: equilibrando la compra de vivienda con la libertad financiera a los 58 años.",
        },
    ],
}

SUGGESTED_PROMPTS_BY_CASE: Dict[str, List[str]] = {
    "timothy-melanie-weah": [
        "¿Cómo aprovechamos parte de los $150,000 en el banco para quitar la tarjeta sin perder tranquilidad?",
        "¿Cómo nos ponemos de acuerdo Timothy y Melanie con el nivel de riesgo?",
        "¿Por qué nuestro Score sube de 60 a 73 al unir tarjeta y protección familiar?",
    ],
    "michael-carter": [
        "¿Cómo acompaso la compra de mi casa en 2027 para jubilarme tranquilo a los 58?",
        "Con todo lo que ahorro al año ($43,000), ¿cómo doy el salto rápido de 26 a 62 puntos?",
        "¿Cómo organizo mi ahorro mensual para llegar cómodo a la entrada de la casa?",
    ],
    "daniel-emily-johnson": [
        "¿Por dónde empezamos con suavidad: la tarjeta, el colchón familiar o el 401(k)?",
        "¿Cómo coordinamos las cuentas de Emily y Daniel para dar tranquilidad a los niños?",
        "¿Cuánto ahorraríamos en impuestos al año si activamos nuestros 401(k)?",
    ],
    "samantha-lewis": [
        "Con mi Score de 82, ¿cómo alargo la holgura de mi liquidez hasta los 90 años?",
        "¿Cómo organizo con comodidad la universidad de Ethan y Ava y mi retiro?",
        "¿Cómo ahorro los $3,032 anuales de impuestos en mi cartera de ETFs?",
    ],
}

# Mentor IA Proactivo + Traductor de Jerga con Metáforas por Caso
MENTOR_INSIGHTS_BY_CASE: Dict[str, Dict[str, Any]] = {
    "timothy-melanie-weah": {
        "proactive_nudge": {
            "badge": "💡 Píldora del día · Para Timothy y Melanie",
            "greeting": "¡Hola familia! He revisado vuestro mapa de viaje hoy.",
            "message": "Tenéis el colchón de emergencia más que cubierto ($150,800, 16 meses de gastos), pero la tarjeta de crédito os está restando $270 de intereses cada mes. ¿Queréis que veamos en 20 segundos cómo saldar ese tramo hoy sin tocar el fondo de seguridad de Melanie?",
            "cta_label": "Escuchar explicación sencilla",
            "voice_question": "Explícanos de forma sencilla cómo saldar el tramo de la tarjeta de $18,000 sin perder la tranquilidad de nuestro colchón en el banco.",
        },
        "jargon_pills": [
            {
                "term": "Deuda Revolving (18% TAE)",
                "short_tag": "El cubo con un agujero",
                "metaphor_title": "🪣 El cubo con un agujero en el fondo",
                "metaphor_explanation": "Tener $150,800 en el banco dando un 0.1% ($150 al año) mientras debéis $18,000 al 18% ($3,240 al año) es como guardar agua en un cubo que pierde un chorro por debajo.",
                "family_impact": "Si pagáis solo $300/mes, terminaréis en septiembre de 2039. Con $6,800 de vuestro efectivo sobrante quitáis ya el freno del Score.",
                "voice_question": "Explícame con la metáfora del cubo por qué nuestra tarjeta al 18% nos frena el Score en 60.",
            },
            {
                "term": "Plan 529 (Universidad)",
                "short_tag": "El invernadero sin impuestos",
                "metaphor_title": "🌱 Un invernadero protegido para Liam y Josh",
                "metaphor_explanation": "Un Plan 529 es como plantar un árbol frutal para los estudios de Liam y Josh dentro de un invernadero donde Hacienda no se lleva ninguna fruta mientras crece.",
                "family_impact": "Hoy tenéis $0 en planes 529 y faltan 12 años para que Liam empiece en 2038.",
                "voice_question": "¿Cómo funciona el Plan 529 para la universidad de Liam y Josh explicado sin tecnicismos?",
            },
            {
                "term": "Póliza Umbrella ($1M)",
                "short_tag": "El paraguas gigante familiar",
                "metaphor_title": "☂️ Un paraguas gigante cuando arrecia la tormenta",
                "metaphor_explanation": "Vuestro seguro de coche o de casa cubre lluvias normales, pero si un día hay un accidente grande y os reclaman mucho dinero, la póliza Umbrella se abre encima para que nadie toque vuestros ahorros.",
                "family_impact": "Con un patrimonio neto de $695,500 e ingresos altos, añade $1 millón de escudo por muy poco al año.",
                "voice_question": "¿Qué es una póliza Umbrella y por qué la necesitamos nosotros?",
            },
            {
                "term": "ETF Apalancado (UPRO)",
                "short_tag": "Coche con turbo x3",
                "metaphor_title": "🏎️ Un deportivo con triple acelerador y triple freno",
                "metaphor_explanation": "Timothy tiene $12,740 en UPRO dentro de su cuenta Roth. Es como un coche que multiplica por 3 la velocidad de la bolsa: cuando la carretera sube corre muchísimo, pero en una curva cerrada da sustos.",
                "family_impact": "Ha subido mucho en 3 años, pero añade un 30% de volatilidad que conviene vigilar en pareja.",
                "voice_question": "Explícanos a Melanie y a mí qué es ese fondo UPRO que tiene Timothy y si es peligroso.",
            },
        ],
    },
    "michael-carter": {
        "proactive_nudge": {
            "badge": "⚡ Alerta Proactiva · Tu compra de casa en 2027",
            "greeting": "¡Hola Michael! Un apunte clave antes de enero de 2027.",
            "message": "Ahorras $43,000 al año (¡casi el 24% de tu sueldo!), así que tu Score de 26 NO es por falta de disciplina. El problema es que pagar los $113,300 de entrada de tu casa en enero de 2027 vacía la gasolina de tus inversiones para jubilarte a los 58. ¿Vemos cómo cuadrar las dos metas?",
            "cta_label": "Hablar con mi mentor sobre 2027",
            "voice_question": "Explícame claro y al grano por qué comprar la casa en enero de 2027 choca con jubilarme a los 58 y cómo lo arreglo.",
        },
        "jargon_pills": [
            {
                "term": "Tasa de Extracción (Draw Rate)",
                "short_tag": "El grifo del depósito",
                "metaphor_title": "🚰 Qué tan abierto dejas el grifo al jubilarte",
                "metaphor_explanation": "Imagina que tu ahorro de jubilación es un depósito de agua que se recarga con la lluvia (la rentabilidad). Si abres demasiado el grifo cada año (5.6%), el depósito se vacía a los 85 años.",
                "family_impact": "Ajustar el ritmo de retiro hacia la banda sostenible hace que tu dinero dure hasta los 91 años y sube tu Score de 26 a 62.",
                "voice_question": "Explícame con un ejemplo sencillo qué significa bajar mi tasa de retiro y por qué sube mi Score a 62.",
            },
            {
                "term": "Flujo de Caja Negativo (-$8,336)",
                "short_tag": "Correr más rápido que la cinta",
                "metaphor_title": "🏃‍♂️ Apartar más ahorro del que deja tu cuenta corriente",
                "metaphor_explanation": "Entre impuestos, alquiler, gastos y los $36,000 que mandas a ahorro, cada año salen de tu banco $8,336 más de los que entran.",
                "family_impact": "Secuenciar bien cuánto va a liquidez para la casa de 2027 y cuánto a largo plazo elimina esa tensión.",
                "voice_question": "¿Cómo es posible que tenga flujo de caja negativo de -$8,336 si gano $180,000 al año?",
            },
            {
                "term": "Aportación 401(k) + Match",
                "short_tag": "Dinero gratis de tu empresa",
                "metaphor_title": "🎁 El regalo automático de tu empresa ($7,000/año)",
                "metaphor_explanation": "Tu empresa ya te regala $7,000 al año en tu 401(k). Además, aún tienes hueco para meter $7,500 más y pagar $1,800 menos en impuestos a Hacienda.",
                "family_impact": "Es tu motor principal para jubilarte joven a los 58 años.",
                "voice_question": "¿Me conviene meter los $7,500 que me faltan en el 401(k) o guardarlos para la entrada de la casa?",
            },
        ],
    },
    "daniel-emily-johnson": {
        "proactive_nudge": {
            "badge": "🤝 Píldora en Pareja · Para Daniel y Emily",
            "greeting": "¡Hola Daniel y Emily! Un detalle importante sobre vuestro esfuerzo.",
            "message": "Emily está ahorrando $26,000 al año con muchísimo mérito, pero al mismo tiempo la tarjeta al 24.9% os quita $373.50 de intereses cada mes y no estáis usando el descuento fiscal de vuestros 401(k). Es como pedalear cuesta arriba con el freno de mano puesto. ¿Quitamos el freno juntos?",
            "cta_label": "Ver cómo coordinar nuestras cuentas",
            "voice_question": "Explícanos de forma sencilla cómo coordinar el ahorro de Emily con las deudas y el 401(k) para salir ganando los dos.",
        },
        "jargon_pills": [
            {
                "term": "Escudo Fiscal 401(k)",
                "short_tag": "Ahorrar $11,760 en impuestos",
                "metaphor_title": "🛡️ Pagaros a vosotros mismos antes que a Hacienda",
                "metaphor_explanation": "Cada dólar que metéis al 401(k) se resta de vuestra factura de impuestos de ese año. A vuestro tramo del 24%, de cada $100 que ahorráis, Hacienda os 'subvenciona' $24.",
                "family_impact": "Hoy aportáis $0 a ambos 401(k); activarlos puede ahorraros hasta $11,760 al año en impuestos.",
                "voice_question": "¿Cómo funciona exactamente el ahorro de impuestos del 401(k) en nuestro caso?",
            },
            {
                "term": "Interés Compuesto en Contra (24.9%)",
                "short_tag": "La bola de nieve al revés",
                "metaphor_title": "❄️ Cuando la bola de nieve rueda en tu contra",
                "metaphor_explanation": "En la tarjeta Chase Sapphire ($18,000 al 24.9%), de los $450 que pagáis cada mes, $373.50 se van solo en intereses y apenas $76 bajan la deuda.",
                "family_impact": "A ese ritmo tardaríais hasta enero de 2034 en quitarla. Priorizarla os libera $5,400/año de flujo.",
                "voice_question": "Explícanos por qué pagar la tarjeta al 24.9% es mejor inversión que meter dinero al bróker ahora mismo.",
            },
            {
                "term": "Brecha de Protección Familiar",
                "short_tag": "La red del trapecista",
                "metaphor_title": "🎪 La red debajo de los ingresos de papá y mamá",
                "metaphor_explanation": "Vuestros dos sueldos ($280,000/año) son el motor de toda la familia y de la hipoteca de $560,000. El seguro de vida es la red que garantiza que Oliver y Sophia tengan su casa y universidad pase lo que pase.",
                "family_impact": "Añadir cobertura de vida sube vuestro Score de 52 a 57 de forma inmediata (+5 puntos).",
                "voice_question": "¿Cuánto seguro de vida necesitamos realmente para proteger a Oliver y Sophia?",
            },
        ],
    },
    "samantha-lewis": {
        "proactive_nudge": {
            "badge": "📊 Insight Ejecutivo · Más allá del Score 82",
            "greeting": "Hola Samantha. Tu balance actual es sólido, pero hay una asimetría estratégica.",
            "message": "Tu Score de 82 refleja cero endeudamiento y excelente cobertura de riesgos. Sin embargo, el 100% de tu ahorro financiero ($60,000/año) va a cuentas sujetas a impuestos y tienes $0 en vehículos de jubilación, proyectando agotamiento de liquidez a los 73 años. ¿Revisamos la optimización fiscal y de horizonte?",
            "cta_label": "Analizar estrategia con mi mentor",
            "voice_question": "Dame una síntesis ejecutiva de por qué mi plan proyecta agotamiento a los 73 años teniendo un Score de 82 y cómo corregirlo.",
        },
        "jargon_pills": [
            {
                "term": "Tax Drag (Fuga Fiscal de Cartera)",
                "short_tag": "-$3,032/año en impuestos",
                "metaphor_title": "⚓ Fricción fiscal anual sobre tus dividendos",
                "metaphor_explanation": "Mantener fondos de alto dividendo y renta fija (como JNK y SCHD) en una cuenta de bróker sujeta a un tipo marginal del 35.8% actúa como un viento en contra constante sobre la capitalización compuesta.",
                "family_impact": "Te cuesta ~$3,032 anuales en impuestos evitables mediante ubicación de activos (Asset Location) y cuentas IRA/HSA.",
                "voice_question": "¿Qué ajustes de ubicación de activos me recomiendas para eliminar los $3,032 anuales de Tax Drag?",
            },
            {
                "term": "Riesgo de Secuencia y Liquidez (73 años)",
                "short_tag": "Patrimonio inmobiliario vs Liquidez",
                "metaphor_title": "🏛️ Riqueza patrimonial ilíquida frente a flujo de retiro",
                "metaphor_explanation": "El 65% de tu patrimonio neto ($900,000 de $1,395,000) reside en tu vivienda principal. Al exigir una tasa de extracción inicial del 12.2% sobre los activos financieros líquidos, la cartera se agota a los 73 años.",
                "family_impact": "Abrir vehículos de jubilación deducibles (IRA/HSA) y escalonar los pagos de universidad de Ethan y Ava equilibra el horizonte hasta los 91 años.",
                "voice_question": "¿Cómo estructuramos mis aportaciones entre jubilación y los pagos universitarios de Ethan y Ava?",
            },
            {
                "term": "Concentración en VTI (39%)",
                "short_tag": "Reequilibrio hacia Glide Path",
                "metaphor_title": "⚖️ Calibración de exposición a renta variable (85% → 80%)",
                "metaphor_explanation": "Tu exposición del 85% en renta variable supera el 80% de tu senda óptima (Glide Path), con un 39% concentrado en VTI justo cuando afrontas salidas de caja universitarias en 2027 y 2028.",
                "family_impact": "Reequilibrar ~$58,300 en VTI y asegurar formalmente la vivienda eleva tu Score a 84.",
                "voice_question": "¿Cómo ejecutamos la reducción de VTI del 39% al 25% minimizando el impacto fiscal?",
            },
        ],
    },
}


def _normalize_text_for_spanish_tts(text: str) -> str:
    """
    Limpia símbolos y formatos numéricos anglosajones/puntos de miles antes de enviarlos
    a la voz nativa española de ElevenLabs para que lea importes (tanto $6,800 como 6.800$),
    porcentajes y siglas con dicción y cadencia 100% natural de España.
    """
    s = re.sub(r"[*_`#]+", "", text or "")
    s = re.sub(r"\s+", " ", s).strip()

    # 1. Importes abreviados con $ antes o después ($60k, 60k$, $1.6M, 1,6M$, $1M)
    s = re.sub(r"\$\s*([0-9]+)[.,]([0-9]+)\s*[mM]\b", r"\1 coma \2 millones de dólares", s)
    s = re.sub(r"\b([0-9]+)[.,]([0-9]+)\s*[mM]\s*\$", r"\1 coma \2 millones de dólares", s)
    s = re.sub(r"\$\s*([0-9]+)\s*[mM]\b", lambda m: "1 millón de dólares" if m.group(1) == "1" else f"{m.group(1)} millones de dólares", s)
    s = re.sub(r"\b([0-9]+)\s*[mM]\s*\$", lambda m: "1 millón de dólares" if m.group(1) == "1" else f"{m.group(1)} millones de dólares", s)
    s = re.sub(r"\$\s*([0-9]+)\s*[kK]\b", r"\1 mil dólares", s)
    s = re.sub(r"\b([0-9]+)\s*[kK]\s*\$", r"\1 mil dólares", s)

    # 2. Importes con separador de miles en coma o punto ($150,800 o 150.800$ o 6.800 $)
    s = re.sub(
        r"\$\s*([0-9]{1,3}(?:[,.][0-9]{3})+)",
        lambda m: f"{re.sub(r'[,.]', '', m.group(1))} dólares",
        s,
    )
    s = re.sub(
        r"\b([0-9]{1,3}(?:[,.][0-9]{3})+)\s*\$",
        lambda m: f"{re.sub(r'[,.]', '', m.group(1))} dólares",
        s,
    )
    s = re.sub(r"\$\s*([0-9]+)", r"\1 dólares", s)
    s = re.sub(r"\b([0-9]+)\s*\$", r"\1 dólares", s)

    # 3. Números con separador de miles sin símbolo $ (ej. 150.800 o 6,800 -> 150800, 6800)
    s = re.sub(
        r"\b([0-9]{1,3}(?:[,.][0-9]{3})+)\b",
        lambda m: re.sub(r"[,.]", "", m.group(1)),
        s,
    )

    # 4. Porcentajes con punto o coma decimal (ej. 24.9% -> 24 coma 9 por ciento)
    s = re.sub(r"([0-9]+)[.,]([0-9]+)\s*%", r"\1 coma \2 por ciento", s)
    s = re.sub(r"([0-9]+)\s*%", r"\1 por ciento", s)

    # 5. Siglas y anglicismos financieros leídos con naturalidad en español
    phonetic_map = [
        (r"\b401\s*\(\s*k\s*\)", "plan cuatrocientos uno ka"),
        (r"\b401k\b", "plan cuatrocientos uno ka"),
        (r"\bRoth\s+IRA\b", "cuenta Roth Ira"),
        (r"\bIRA\b", "cuenta Ira"),
        (r"\bHSA\b", "cuenta H S A"),
        (r"\b529\b", "plan quinientos veintinueve"),
        (r"\bETF\b", "fondo cotizado"),
        (r"\bScore\b", "puntuación"),
        (r"\bscore\b", "puntuación"),
        (r"\bUmbrella\b", "póliza paraguas"),
        (r"\bumbrella\b", "póliza paraguas"),
        (r"\bSherpas\s+Wealth\b", "Sherpas"),
    ]
    for pattern, replacement in phonetic_map:
        s = re.sub(pattern, replacement, s)
    return s


_TTS_MEMORY_CACHE: Dict[str, Tuple[bytes, str]] = {}
_TTS_META_CACHE: Dict[str, Dict[str, str]] = {}
_TTS_INFLIGHT: Dict[str, asyncio.Task] = {}
_LLM_ANSWER_CACHE: Dict[str, Tuple[str, bool, List[str]]] = {}
_ELEVENLABS_HTTP_CLIENT: Optional[Any] = None


def _get_elevenlabs_http_client():
    global _ELEVENLABS_HTTP_CLIENT
    if _ELEVENLABS_HTTP_CLIENT is None:
        import httpx

        _ELEVENLABS_HTTP_CLIENT = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=0, max_connections=20),
            headers={"Connection": "close"},
            timeout=httpx.Timeout(12.0, connect=3.0),
        )
    return _ELEVENLABS_HTTP_CLIENT


def _build_tts_cache_key(text: str, voice_profile: Dict[str, Any]) -> Tuple[str, str]:
    voice_id = voice_profile["voice_id"]
    lang = voice_profile.get("detected_language", "es")
    clean_input = re.sub(r"\s+", " ", (text or "")).strip()
    tts_text = _normalize_text_for_spanish_tts(clean_input) if lang == "es" else clean_input
    cache_key = hashlib.sha256(f"multi_v2::{voice_id}::{lang}::{tts_text}".encode("utf-8")).hexdigest()[:20]
    return cache_key, tts_text


def get_tts_meta(text: str, voice_profile: Dict[str, Any]) -> Dict[str, str]:
    cache_key, _ = _build_tts_cache_key(text, voice_profile)
    return _TTS_META_CACHE.get(
        cache_key,
        {"tts_provider": "elevenlabs_personal_api", "tts_model": "eleven_multilingual_v2"},
    )


def start_tts_prefetch(text: str, voice_profile: Dict[str, Any]) -> None:
    """Inicia la síntesis de ElevenLabs en segundo plano mientras el JSON de texto viaja al navegador."""
    if not text or not text.strip():
        return
    cache_key, tts_text = _build_tts_cache_key(text, voice_profile)
    if cache_key in _TTS_MEMORY_CACHE or cache_key in _TTS_INFLIGHT:
        return
    task = asyncio.create_task(_synthesize_elevenlabs_impl(text, voice_profile, cache_key, tts_text))
    _TTS_INFLIGHT[cache_key] = task
    task.add_done_callback(lambda t: _TTS_INFLIGHT.pop(cache_key, None) if _TTS_INFLIGHT.get(cache_key) is t else None)


async def _synthesize_elevenlabs_impl(text: str, voice_profile: Dict[str, Any], cache_key: str, tts_text: str) -> Tuple[bytes, str]:
    import os
    import base64

    voice_id = voice_profile["voice_id"]
    fallback_voice = voice_profile.get("fallback_voice", voice_id)

    audio_bytes = None
    provider_used = "elevenlabs_personal_api"
    model_used = "eleven_multilingual_v2"
    active_key = (ELEVENLABS_API_KEY or os.getenv("ELEVENLABS_API_KEY") or "").strip()

    # 1. API oficial de ElevenLabs con la API Key personal del usuario + eleven_multilingual_v2
    if active_key:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "xi-api-key": active_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
                "Connection": "close",
            }
            stability = voice_profile.get("stability", 0.48)
            similarity_boost = voice_profile.get("similarity_boost", 0.78)
            style_weight = voice_profile.get("style_weight", 0.20)
            payload: Dict[str, Any] = {
                "text": tts_text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style_weight,
                    "use_speaker_boost": True,
                    "speed": 1.0,
                },
            }
            client = _get_elevenlabs_http_client()
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code == 200 and len(res.content) > 500:
                audio_bytes = res.content
                print(
                    f"✅ [ElevenLabs Personal API] voz={voice_profile.get('voice_name', voice_id)} "
                    f"| model=eleven_multilingual_v2 | speed=1.0 | bytes={len(audio_bytes)}"
                )
            else:
                print(f"⚠️ [ElevenLabs Personal API] status={res.status_code}: {res.text[:160]}")
        except Exception as err:
            print(f"⚠️ [ElevenLabs Personal API] excepción: {err}")
            audio_bytes = None

    # 2. Fallback al proxy del hackathon con eleven-multilingual-v2
    if not audio_bytes:
        provider_used = "proxy_fallback"
        model_used = "eleven-multilingual-v2"
        try:
            audio_resp = await llm_client.audio.speech.create(
                model="eleven-multilingual-v2",
                voice=voice_id,
                input=tts_text,
            )
            audio_bytes = audio_resp.content
            print(f"ℹ️ [Proxy ElevenLabs Fallback] voz={voice_id} | bytes={len(audio_bytes)}")
        except Exception:
            audio_resp = await llm_client.audio.speech.create(
                model="eleven-multilingual-v2",
                voice=fallback_voice,
                input=tts_text,
            )
            audio_bytes = audio_resp.content

    b64_audio = base64.b64encode(audio_bytes).decode("ascii")
    data_uri = f"data:audio/mp3;base64,{b64_audio}"
    if len(_TTS_MEMORY_CACHE) > 200:
        _TTS_MEMORY_CACHE.clear()
        _TTS_META_CACHE.clear()
    _TTS_MEMORY_CACHE[cache_key] = (audio_bytes, data_uri)
    _TTS_META_CACHE[cache_key] = {"tts_provider": provider_used, "tts_model": model_used}
    return audio_bytes, data_uri


async def synthesize_elevenlabs_speech(text: str, voice_profile: Dict[str, Any]) -> Tuple[bytes, str]:
    """
    Genera audio MP3 en memoria con ElevenLabs Multilingual v2 usando la API Key personal
    del usuario y voces hispanohablantes peninsulares nativas a velocidad normal (1.0x).
    Reutiliza tareas en curso (`_TTS_INFLIGHT`) para evitar llamadas duplicadas.
    """
    cache_key, tts_text = _build_tts_cache_key(text, voice_profile)
    if cache_key in _TTS_MEMORY_CACHE:
        return _TTS_MEMORY_CACHE[cache_key]

    inflight = _TTS_INFLIGHT.get(cache_key)
    if inflight is not None:
        return await inflight

    task = asyncio.create_task(_synthesize_elevenlabs_impl(text, voice_profile, cache_key, tts_text))
    _TTS_INFLIGHT[cache_key] = task
    try:
        return await task
    finally:
        if _TTS_INFLIGHT.get(cache_key) is task:
            _TTS_INFLIGHT.pop(cache_key, None)


async def ask_llm_with_tools(
    client_id: str,
    question: str,
    brief: str,
    voice_profile: Dict[str, str],
) -> Tuple[str, bool, List[str]]:
    """
    Ejecuta el ciclo de consulta a `gemini-3.5-flash-lite` con caché en memoria
    y prompt compacto (<280 tokens) para responder en ~1.0s.
    """
    case_id = normalize_case_id(client_id)
    q_clean = (question or "").strip()
    q_lower = q_clean.lower()
    style_key = voice_profile.get("style_key", "auto")
    lang_key = voice_profile.get("detected_language", "es")
    ans_cache_key = f"v3_fast::{case_id}::{style_key}::{lang_key}::{hashlib.md5(brief.encode('utf-8')).hexdigest()[:8]}::{q_lower}"
    if ans_cache_key in _LLM_ANSWER_CACHE:
        return _LLM_ANSWER_CACHE[ans_cache_key]

    needs_deep_tool = any(
        kw in q_lower
        for kw in ("ticker", "etf", "posicion", "position")
    )

    if len(brief) <= 750 and voice_profile.get("compact_tone_hint"):
        sys_prompt = f"{voice_profile['compact_tone_hint']}\n{brief}"
    else:
        sys_prompt = (
            "Eres el asesor personal de Sherpas Wealth, cercano, empático y claro.\n"
            f"{voice_profile['tone_instructions']}\n\n"
            "REGLA MULTILINGÜE AUTOMÁTICA OBLIGATORIA: Detecta el idioma exacto del usuario y respóndele SIEMPRE en ese mismo idioma.\n"
            "REGLA DE BREVEDAD ESTRICTA: Responde SIEMPRE en MÁXIMO 2 frases breves (menos de 40 palabras en total), directas y naturales.\n\n"
            f"CHULETA INTERNA:\n{brief}"
        )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": q_clean},
    ]

    req_kwargs: Dict[str, Any] = {
        "model": "gemini-3.5-flash-lite",
        "messages": messages,
        "max_tokens": 95,
        "temperature": 0.35,
    }
    if needs_deep_tool:
        req_kwargs["tools"] = CHAT_TOOLS
        req_kwargs["tool_choice"] = "auto"

    response = await llm_client.chat.completions.create(**req_kwargs)

    mensaje_ia = response.choices[0].message
    claves_consultadas: List[str] = []
    mcp_usado = False

    if mensaje_ia.tool_calls:
        mcp_usado = True
        messages.append(mensaje_ia)

        async def _run_single_tool(tc: Any) -> Tuple[str, str, str]:
            args = json.loads(tc.function.arguments or "{}")
            part = args.get("part", "financial-health")
            section = args.get("section", "score")
            sub_section = args.get("sub_section")
            etiqueta = f"{part}.{section}" + (f".{sub_section}" if sub_section else "")
            datos = await get_section(
                case_id,
                part,
                section,
                sub_section=sub_section,
                compact_for_llm=True,
            )
            payload = (
                json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
                if not isinstance(datos, str)
                else datos
            )
            return tc.id, etiqueta, payload

        tool_results = await asyncio.gather(*(_run_single_tool(tc) for tc in mensaje_ia.tool_calls))
        for tc_id, etiqueta, payload in tool_results:
            claves_consultadas.append(etiqueta)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": payload,
                }
            )

        respuesta_final = await llm_client.chat.completions.create(
            model="gemini-3.5-flash-lite",
            messages=messages,
            max_tokens=180,
            temperature=0.4,
        )
        texto_ia = (respuesta_final.choices[0].message.content or "").strip()
    else:
        texto_ia = (mensaje_ia.content or "").strip()

    if texto_ia:
        if len(_LLM_ANSWER_CACHE) > 200:
            _LLM_ANSWER_CACHE.clear()
        _LLM_ANSWER_CACHE[ans_cache_key] = (texto_ia, mcp_usado, claves_consultadas)

    return texto_ia, mcp_usado, claves_consultadas


def _compute_cumulative_scores(
    published_score: int,
    top_moves: List[Dict[str, Any]],
    combined_moves: List[Dict[str, Any]],
) -> List[Tuple[int, int, int]]:
    """
    Calcula (score_before, score_after, impacto) acumulativo para cada nivel del Path
    aprovechando `combined_moves` cuando existen topes (caps) como en el caso de los Weah.
    """
    combo_lookup: Dict[frozenset, int] = {}
    for c in combined_moves:
        m_set = frozenset(c.get("moves") or [])
        if m_set:
            combo_lookup[m_set] = c.get("score_after", published_score)

    results: List[Tuple[int, int, int]] = []
    current_score = published_score
    accumulated_titles: List[str] = []

    for move in top_moves:
        title = move.get("title", "")
        accumulated_titles.append(title)
        raw_after = move.get("score_after", current_score)
        combo_after = combo_lookup.get(frozenset(accumulated_titles))

        next_score = max(current_score, raw_after, combo_after or 0)
        impact = max(0, next_score - current_score)
        results.append((current_score, next_score, impact))
        current_score = next_score

    return results


def _ensure_initial_high_fives(case_id: str, couple_data: Dict[str, Any]) -> List[HighFiveItem]:
    """Inicializa el muro de '¡Choca esos cinco!' para el Modo Multijugador Familiar."""
    if case_id not in _HIGH_FIVES_STATE:
        members = couple_data.get("members") or []
        if len(members) >= 2:
            m1, m2 = members[0]["name"], members[1]["name"]
            _HIGH_FIVES_STATE[case_id] = [
                HighFiveItem(
                    id="hf-1",
                    from_member=m2,
                    to_member=m1,
                    milestone_title="Diagnóstico familiar conectado",
                    message=f"¡Choca esos cinco, {m1}! Ya tenemos nuestro Mapa de Viaje claro para este mes 👋",
                    timestamp="Hace 2 horas",
                )
            ]
        else:
            name = members[0]["name"] if members else "Cliente"
            _HIGH_FIVES_STATE[case_id] = [
                HighFiveItem(
                    id="hf-1",
                    from_member="Tu Mentor Sherpas",
                    to_member=name,
                    milestone_title="Mapa de Viaje activado",
                    message=f"¡Gran comienzo, {name}! Tu primer hito está listo para desbloquearse 👋",
                    timestamp="Hoy",
                )
            ]
    return _HIGH_FIVES_STATE[case_id]


async def add_high_five(
    client_id: str,
    from_member: str,
    to_member: str,
    milestone_title: str,
    message: str,
) -> CoupleOverview:
    """Añade un 'Choca esos cinco' al muro familiar y devuelve el estado multijugador actualizado."""
    case_id = normalize_case_id(client_id)
    couple_data = await get_couple_dynamics(case_id)
    high_fives = _ensure_initial_high_fives(case_id, couple_data)

    new_item = HighFiveItem(
        id=f"hf-{len(high_fives) + 1}",
        from_member=from_member,
        to_member=to_member,
        milestone_title=milestone_title,
        message=message,
        timestamp=datetime.now().strftime("Hoy · %H:%M"),
    )
    high_fives.insert(0, new_item)

    kids_items = [KidsGoalItem(**k) for k in KIDS_SAFE_GOALS_BY_CASE.get(case_id, [])]
    return CoupleOverview(
        is_couple=couple_data["is_couple"],
        members=[CoupleMember(**m) for m in couple_data["members"]],
        consensus_bridge=couple_data["consensus_bridge"],
        kids_safe_view=kids_items,
        high_fives=high_fives,
    )


async def build_gamified_path(client_id: str) -> PathSchema:
    """
    Genera el Mapa de Viaje (Roadmap) gamificado.
    Fusión completa con el motor de hitos persistente en SQLite:
    - Si existen hitos generados en la base de datos (milestone_repository), los consulta y mapea
      manteniendo la reactividad y gamificación.
    - Si el caso aún no tiene hitos en la base de datos, los inicializa y persiste automáticamente.
    - Conserva las paradas de metas vitales, modo pareja y celebraciones.
    """
    case_id = normalize_case_id(client_id)
    short_id = get_short_id(case_id)

    score_data, case_data, couple_data = await asyncio.gather(
        get_section(case_id, "financial-health", "score"),
        get_section(case_id, "financial-health", "case"),
        get_couple_dynamics(case_id),
    )
    if not isinstance(score_data, dict):
        score_data = {}

    published_score = score_data.get("published_score", 50)
    banda = score_data.get("band", "vulnerable")
    top_moves = score_data.get("top_moves") or []
    combined_moves = score_data.get("combined_moves") or []

    household_list = (case_data.get("household") if isinstance(case_data, dict) else []) or []
    adults = [p.get("first_name", "") for p in household_list if p.get("role") in ("client", "co-client")]
    household_name = " & ".join(adults) if adults else case_id

    recompensas_por_defecto = [
        "Insignia de Escudo Protector",
        "Medalla de Crecimiento Sostenible",
        "Trofeo de Libertad Financiera",
        "Insignia de Tranquilidad Familiar",
    ]

    FULL_MILESTONES_BY_CASE: Dict[str, List[Dict[str, Any]]] = {
        "timothy-melanie-weah": [
            {
                "titulo": "Reducir el tramo caro de la tarjeta de crédito al 18%",
                "descripcion": "Destinar $6,800 de vuestros $150,800 en efectivo para reducir el saldo de la tarjeta Chase y eliminar el primer freno del Score.",
                "por_que_importa": "Os ahorráis $3,240 al año en intereses manteniendo un amplio colchón de liquidez familiar.",
                "pregunta_mentor": "¿Cómo nos ayuda usar $6,800 del efectivo para reducir la tarjeta al 18%?",
                "score_before": 60, "score_after": 65, "impacto": 5, "category": "Debt",
            },
            {
                "titulo": "Ampliar la cobertura de protección familiar para Liam y Josh",
                "descripcion": "Sumar $235,000 de seguro de vida a término hasta alcanzar los $485,000 recomendados en el plan.",
                "por_que_importa": "Al combinar el ajuste de la tarjeta con este respaldo, vuestro Score sube directamente a 73 puntos.",
                "pregunta_mentor": "¿Por qué nuestro Score da un salto hasta 73 al unir el ajuste de la tarjeta con la protección familiar?",
                "score_before": 65, "score_after": 73, "impacto": 8, "category": "Protection",
            },
            {
                "titulo": "Activar póliza paraguas de responsabilidad civil ($1M Umbrella)",
                "descripcion": "Incorporar una cobertura paraguas de $1,000,000 para resguardar el ahorro y patrimonio familiar.",
                "por_que_importa": "Protege todo el patrimonio construido por la familia con un coste anual muy reducido.",
                "pregunta_mentor": "¿Qué cubre exactamente la póliza paraguas de un millón de dólares?",
                "score_before": 73, "score_after": 75, "impacto": 2, "category": "Protection",
            },
            {
                "titulo": "Rentabilizar los $60,222 de efectivo ocioso por encima de la reserva",
                "descripcion": "Separar el fondo de emergencia y mover el excedente que hoy rinde 0.1% hacia cuentas remuneradas.",
                "por_que_importa": "Evita que la inflación erosione vuestros ahorros sin perder disponibilidad.",
                "pregunta_mentor": "¿Cuánto efectivo deberíamos dejar en la reserva y cuánto mover a una cuenta remunerada?",
                "score_before": 75, "score_after": 77, "impacto": 2, "category": "Savings",
            },
            {
                "titulo": "Abrir cuentas educativas 529 para Liam (2038) y Josh (2041)",
                "descripcion": "Automatizar $384 al mes en planes 529 libres de impuestos para cubrir el objetivo universitario de $113,508.",
                "por_que_importa": "Aprovecha el interés compuesto libre de impuestos durante los próximos 12 a 15 años.",
                "pregunta_mentor": "¿Cómo funcionan las cuentas 529 para la universidad de Liam y Josh?",
                "score_before": 77, "score_after": 79, "impacto": 2, "category": "Goals",
            },
            {
                "titulo": "Reequilibrar la concentración en tecnología y ETF apalancado (UPRO)",
                "descripcion": "Moderar el peso en activos altamente volátiles para alinear la cartera con el consenso de pareja.",
                "por_que_importa": "Reduce oscilaciones bruscas en la cartera manteniendo el crecimiento a largo plazo.",
                "pregunta_mentor": "¿Qué ajuste nos recomiendas hacer con nuestra posición en tecnología y UPRO?",
                "score_before": 79, "score_after": 81, "impacto": 2, "category": "Investments",
            },
            {
                "titulo": "Optimizar el margen anual en cuentas Roth IRA, HSA y 401(k)",
                "descripcion": "Aprovechar el espacio disponible en cuentas con ventaja fiscal antes del cierre del ejercicio.",
                "por_que_importa": "Reduce la factura fiscal anual e impulsa el ahorro de jubilación de ambos.",
                "pregunta_mentor": "¿Cómo aprovechamos el margen pendiente en nuestras cuentas Roth IRA y 401(k)?",
                "score_before": 81, "score_after": 82, "impacto": 1, "category": "Retirement",
            },
        ],
        "daniel-emily-johnson": [
            {
                "titulo": "Ampliar la cobertura de protección familiar para Oliver y Sophia",
                "descripcion": "Sumar $1,166,000 de respaldo familiar para proteger los dos ingresos del hogar ($280,000/año).",
                "por_que_importa": "Garantiza que tanto la vivienda como los estudios de los niños estén cubiertos ante cualquier imprevisto.",
                "pregunta_mentor": "¿Cómo organizamos esta protección familiar entre Daniel y Emily de forma cómoda?",
                "score_before": 52, "score_after": 57, "impacto": 5, "category": "Protection",
            },
            {
                "titulo": "Liquidar el saldo de la tarjeta de crédito al 24.9% TAE",
                "descripcion": "Destinar parte del flujo de caja libre anual para cancelar por completo la deuda rotativa.",
                "por_que_importa": "Elimina el préstamo más caro del hogar y libera capacidad de ahorro mensual.",
                "pregunta_mentor": "¿Cuál es la forma más rápida de quitarnos la tarjeta al 24.9% sin tocar nuestra reserva?",
                "score_before": 57, "score_after": 62, "impacto": 5, "category": "Debt",
            },
            {
                "titulo": "Canalizar los $15,032/año de margen hacia los planes 401(k)",
                "descripcion": "Incrementar las aportaciones pre-impuestos en los planes de jubilación de Daniel y Emily.",
                "por_que_importa": "Genera un ahorro fiscal inmediato de hasta $11,760 al año mientras asegura vuestro retiro.",
                "pregunta_mentor": "¿Cuánto nos ahorramos en impuestos al subir nuestras aportaciones al 401(k)?",
                "score_before": 62, "score_after": 67, "impacto": 5, "category": "Retirement",
            },
            {
                "titulo": "Activar póliza paraguas de responsabilidad civil ($1M Umbrella)",
                "descripcion": "Añadir una cobertura paraguas de $1,000,000 sobre vuestro patrimonio e ingresos futuros.",
                "por_que_importa": "Completa el escudo de protección del hogar levantando el tope del Score.",
                "pregunta_mentor": "¿Por qué es importante la póliza paraguas para nuestra familia?",
                "score_before": 67, "score_after": 70, "impacto": 3, "category": "Protection",
            },
            {
                "titulo": "Establecer el plan educativo 529 para Oliver y Sophia",
                "descripcion": "Definir una aportación mensual automática para la universidad de los dos hijos tras cubrir el 401(k).",
                "por_que_importa": "Concilia la meta educativa de Emily con la eficiencia financiera de Daniel.",
                "pregunta_mentor": "¿Cómo equilibramos el ahorro para la universidad de los niños con nuestra jubilación?",
                "score_before": 70, "score_after": 73, "impacto": 3, "category": "Goals",
            },
            {
                "titulo": "Consolidar el fondo de emergencia familiar en cuenta remunerada",
                "descripcion": "Mantener de 3 a 6 meses de gastos esenciales en una cuenta de alta liquidez separada del gasto diario.",
                "por_que_importa": "Aporta serenidad a corto plazo sin frenar la rentabilidad del resto del ahorro.",
                "pregunta_mentor": "¿Qué importe exacto deberíamos mantener en nuestro fondo de emergencia?",
                "score_before": 73, "score_after": 76, "impacto": 3, "category": "Savings",
            },
            {
                "titulo": "Unificar la estrategia de inversión entre los perfiles de ambos",
                "descripcion": "Coordinar las carteras de Daniel (Growth) y Emily (Moderada) como un único patrimonio familiar.",
                "por_que_importa": "Evita solapamientos de fondos y optimiza la relación rentabilidad-riesgo del hogar.",
                "pregunta_mentor": "¿Cómo combinamos el perfil Growth de Daniel y el Moderado de Emily en una sola estrategia?",
                "score_before": 76, "score_after": 78, "impacto": 2, "category": "Investments",
            },
        ],
        "michael-carter": [
            {
                "titulo": "Sincronizar la compra de vivienda ($550,000) con el retiro a los 58",
                "descripcion": "Acompasar el objetivo inmobiliario de 2027 para situar la tasa de retiro futura en la banda sostenible (6.0%).",
                "por_que_importa": "Permite que tu ahorro te acompañe con holgura hasta los 91 años y eleva tu Score en +24 puntos.",
                "pregunta_mentor": "¿Cómo acompasamos la compra de mi casa de $550,000 en 2027 con mi jubilación a los 58 años?",
                "score_before": 26, "score_after": 50, "impacto": 24, "category": "Goals",
            },
            {
                "titulo": "Ajustar el peso de crecimiento de la cartera del 74% al 88%",
                "descripcion": "Reorientar ~$19,900 hacia renta variable global aprovechando tus 20 años de horizonte hasta los 58.",
                "por_que_importa": "Impulsa la capitalización a largo plazo necesaria para tu jubilación temprana.",
                "pregunta_mentor": "¿Qué cambios concretos debo hacer en mi cartera para pasar del 74% al 88% en crecimiento?",
                "score_before": 50, "score_after": 58, "impacto": 8, "category": "Investments",
            },
            {
                "titulo": "Activar póliza paraguas de protección patrimonial ($1M Umbrella)",
                "descripcion": "Incorporar una cobertura de responsabilidad civil de $1,000,000 para proteger tus activos.",
                "por_que_importa": "Elimina el freno de protección en tu Score y suma +4 puntos directos.",
                "pregunta_mentor": "¿Por qué activar la póliza paraguas desbloquea tantos puntos en mi plan?",
                "score_before": 58, "score_after": 62, "impacto": 4, "category": "Protection",
            },
            {
                "titulo": "Equilibrar el flujo de caja anual (-$8,336) previo a la hipoteca",
                "descripcion": "Ajustar partidas discrecionales para que tu ahorro anual de $43,000 cubra cómodamente los nuevos gastos.",
                "por_que_importa": "Evita tener que recurrir a tu cartera de inversión para cubrir gastos corrientes.",
                "pregunta_mentor": "¿Cómo corregimos el desajuste anual de $8,336 en mi flujo de caja?",
                "score_before": 62, "score_after": 66, "impacto": 4, "category": "Savings",
            },
            {
                "titulo": "Reubicar el ETF de bonos (JNK) hacia cuentas con ventaja fiscal",
                "descripcion": "Trasladar los activos de renta fija que hoy tributan al tipo marginal fuera de la cuenta sujeta a impuestos.",
                "por_que_importa": "Reduce el drenaje fiscal anual y mejora la rentabilidad neta de tu cartera.",
                "pregunta_mentor": "¿Por qué me conviene mover el fondo JNK a una cuenta con ventaja fiscal?",
                "score_before": 66, "score_after": 69, "impacto": 3, "category": "Investments",
            },
            {
                "titulo": "Proteger en liquidez segura el capital para la entrada ($113,300)",
                "descripcion": "Aislar de la volatilidad bursátil el dinero destinado a la entrada de la vivienda de Austin.",
                "por_que_importa": "Garantiza que una caída del mercado a corto plazo no retrase la compra de tu casa.",
                "pregunta_mentor": "¿Cómo preparamos los $113,300 de la entrada de la casa sin desproteger mi fondo de emergencia?",
                "score_before": 69, "score_after": 72, "impacto": 3, "category": "Goals",
            },
            {
                "titulo": "Maximizar aportaciones anuales a cuentas 401(k) e IRA",
                "descripcion": "Exprimir al máximo los límites de aportación con deducción fiscal para tu tramo de ingresos.",
                "por_que_importa": "Acelera el capital disponible a los 58 años reduciendo impuestos hoy.",
                "pregunta_mentor": "¿Cuánto más puedo aportar este año a mis cuentas de jubilación con ventaja fiscal?",
                "score_before": 72, "score_after": 74, "impacto": 2, "category": "Retirement",
            },
        ],
        "samantha-lewis": [
            {
                "titulo": "Registrar la cobertura de seguro de la vivienda principal ($900,000)",
                "descripcion": "Documentar y actualizar la póliza de hogar de tu residencia libre de hipoteca en el plan.",
                "por_que_importa": "Tu vivienda representa la mayor parte de tu patrimonio ($900,000 de $1,395,000) y sube tu Score a 84.",
                "pregunta_mentor": "¿Cómo impacta registrar el seguro de mi vivienda de $900,000 en la solidez de mi plan?",
                "score_before": 82, "score_after": 84, "impacto": 2, "category": "Protection",
            },
            {
                "titulo": "Reducir la concentración en VTI (del 39% al 25%) y diversificar",
                "descripcion": "Reequilibrar ~$58,300 de la cartera para evitar depender en exceso de una sola posición.",
                "por_que_importa": "Mejora el perfil de riesgo de tu cartera de $495,000 y eleva el Score a 87.",
                "pregunta_mentor": "¿Cómo diversificamos mi posición en VTI minimizando el impacto fiscal?",
                "score_before": 84, "score_after": 87, "impacto": 3, "category": "Investments",
            },
            {
                "titulo": "Ajustar el peso de renta variable (del 85% al 80%) ante pagos cercanos",
                "descripcion": "Pasar ~$17,100 a activos estables de cara a las etapas universitarias de 2027 y 2028.",
                "por_que_importa": "Protege la liquidez necesaria para los próximos 3 años sin renunciar al crecimiento.",
                "pregunta_mentor": "¿Por qué conviene moderar del 85% al 80% la renta variable antes de 2027?",
                "score_before": 87, "score_after": 89, "impacto": 2, "category": "Investments",
            },
            {
                "titulo": "Optimizar los $3,032/año de coste fiscal mediante cuentas HSA e IRA",
                "descripcion": "Utilizar las cuentas con ventaja fiscal disponibles para reducir la tributación anual de tu cartera.",
                "por_que_importa": "Ahorra ~$3,032 al año en impuestos y prolonga la duración de tu liquidez hasta los 90 años.",
                "pregunta_mentor": "¿Cómo puedo ahorrar esos $3,032 anuales en impuestos utilizando cuentas HSA e IRA?",
                "score_before": 89, "score_after": 91, "impacto": 2, "category": "Retirement",
            },
            {
                "titulo": "Reservar la cobertura para la brecha universitaria ($98,838) de Ethan y Ava",
                "descripcion": "Asignar instrumentos líquidos de bajo riesgo para los pagos universitarios que comienzan en 2027 y 2028.",
                "por_que_importa": "Evita tener que vender acciones en un mal momento de mercado cuando lleguen las matrículas.",
                "pregunta_mentor": "¿Cómo cubrimos con comodidad los $98,838 restantes para la universidad de Ethan y Ava?",
                "score_before": 91, "score_after": 92, "impacto": 1, "category": "Goals",
            },
            {
                "titulo": "Equilibrar el flujo de caja anual (-$6,418/año) y proteger la reserva",
                "descripcion": "Coordinar los rendimientos de cartera con tus gastos anuales para mantener intacto el colchón de efectivo.",
                "por_que_importa": "Elimina la fricción de tesorería anual manteniendo tu ritmo de ahorro de $60,000/año.",
                "pregunta_mentor": "¿Qué ajuste sencillo corrige el desfase anual de $6,418 en mi flujo de caja?",
                "score_before": 92, "score_after": 93, "impacto": 1, "category": "Savings",
            },
            {
                "titulo": "Estructurar la compra de la segunda residencia planificada para 2030",
                "descripcion": "Definir la proporción óptima entre financiación y capital propio para no comprometer el retiro a los 73+ años.",
                "por_que_importa": "Permite disfrutar de la segunda vivienda en 2030 manteniendo la holgura financiera vitalicia.",
                "pregunta_mentor": "¿Cuál es la forma más inteligente de financiar mi segunda vivienda en 2030?",
                "score_before": 93, "score_after": 94, "impacto": 1, "category": "Goals",
            },
        ],
    }

    custom_list = FULL_MILESTONES_BY_CASE.get(case_id, [])
    if case_id not in _MILESTONE_STATE:
        _MILESTONE_STATE[case_id] = {
            idx + 1: ("en_progreso" if idx == 0 else "bloqueado")
            for idx in range(max(1, len(custom_list)))
        }
    client_state = _MILESTONE_STATE[case_id]

    niveles: List[Nivel] = []
    score_actual_dinamico = published_score

    for idx, item in enumerate(custom_list):
        nivel_num = idx + 1
        s_before = item["score_before"]
        s_after = item["score_after"]
        impacto = item["impacto"]
        estado = client_state.get(nivel_num, "en_progreso" if idx == 0 else "bloqueado")

        if estado == "completado":
            progreso = 100
            score_actual_dinamico = max(score_actual_dinamico, s_after)
        elif estado == "en_progreso":
            progreso = 45
        elif estado == "needs_review":
            progreso = 50
        else:
            progreso = 0

        recompensa = f"+{impacto} pts de Score ({s_before} → {s_after})"
        niveles.append(
            Nivel(
                nivel_id=nivel_num,
                id=f"ms_{short_id}_{nivel_num}",
                move_key=f"{short_id}_step_{nivel_num}",
                category=item.get("category", "General"),
                type="financial",
                priority="high" if idx < 3 else "medium",
                titulo=item["titulo"],
                descripcion=item["descripcion"],
                por_que_importa=item["por_que_importa"],
                estado=estado,
                progreso_porcentaje=progreso,
                esfuerzo="low" if idx == 0 else "medium",
                score_before=s_before,
                score_after=s_after,
                score_impacto=impacto,
                lifts_a_cap=(idx < 2),
                recompensa_desbloqueo=recompensa,
                pregunta_mentor=item["pregunta_mentor"],
            )
        )

    score_maximo = custom_list[-1]["score_after"] if custom_list else published_score
    completados_count = sum(1 for n in niveles if n.estado == "completado")

    if score_actual_dinamico >= 80:
        banda_dinamica = "strong"
    elif score_actual_dinamico >= 60:
        banda_dinamica = "stable"
    elif score_actual_dinamico >= 40:
        banda_dinamica = "vulnerable"
    else:
        banda_dinamica = banda

    # Construir frase GPS del estado actual ("Estáis aquí. Siguiente parada: ...")
    active_level = next((n for n in niveles if n.estado == "en_progreso"), None) or next(
        (n for n in niveles if n.estado != "completado"), None
    )
    if active_level:
        indicador_gps = (
            f"🚗 Estáis aquí (Score {score_actual_dinamico}/100). "
            f"Siguiente parada: Nivel {active_level.nivel_id} · {active_level.titulo}"
        )
    else:
        indicador_gps = f"🏆 ¡Habéis completado todas las paradas! Score alcanzado: {score_actual_dinamico}/100."

    paradas_metas = [GoalStop(**g) for g in GOAL_STOPS_BY_CASE.get(case_id, [])]
    kids_items = [KidsGoalItem(**k) for k in KIDS_SAFE_GOALS_BY_CASE.get(case_id, [])]
    high_fives = _ensure_initial_high_fives(case_id, couple_data)

    couple_overview = CoupleOverview(
        is_couple=couple_data["is_couple"],
        members=[CoupleMember(**m) for m in couple_data["members"]],
        consensus_bridge=couple_data["consensus_bridge"],
        kids_safe_view=kids_items,
        high_fives=high_fives,
    )

    celebration = _LAST_CELEBRATION.get(
        case_id,
        CelebrationInfo(
            confetti=False,
            titulo_victoria="",
            mensaje_motivador="",
            proximo_paso_unico=active_level.titulo if active_level else "¡Ruta completada!",
        ),
    )

    return PathSchema(
        client_id=case_id,
        short_id=short_id,
        household_name=household_name,
        indicador_actual=indicador_gps,
        score_inicial=published_score,
        score_actual=score_actual_dinamico,
        score_potencial_maximo=score_maximo,
        banda_salud=banda_dinamica,
        total_niveles=len(niveles),
        niveles_completados=completados_count,
        niveles=niveles,
        paradas_metas=paradas_metas,
        celebration=celebration,
        prompts_sugeridos=SUGGESTED_PROMPTS_BY_CASE.get(case_id, []),
        couple_info=couple_overview,
    )


async def update_milestone_state(
    client_id: str,
    nivel_id: int,
    nuevo_estado: str,
    completed_by: Optional[str] = None,
) -> PathSchema:
    """
    Actualiza el estado de un nivel (tanto en la BD persistente como en memoria),
    desbloquea el siguiente, genera la celebración con confeti
    y añade un '¡Choca esos cinco!' automático en el Modo Multijugador Familiar.
    """
    case_id = normalize_case_id(client_id)
    path_before = await build_gamified_path(case_id)

    target_level = next((n for n in path_before.niveles if n.nivel_id == nivel_id), None)

    # 1. Actualizar en base de datos persistente si existe
    if target_level and getattr(target_level, "id", None) and get_session_factory is not None and milestone_repository is not None:
        session = get_session_factory()()
        try:
            m = milestone_repository.get_milestone_for_case(session, case_id, target_level.id)
            if m:
                status_map = {
                    "completado": "completed",
                    "en_progreso": "in_progress",
                    "bloqueado": "not_started",
                    "needs_review": "on_hold",
                }
                target_status = status_map.get(nuevo_estado, nuevo_estado)
                m.status = target_status
                if target_status == "completed":
                    m.completed_at = datetime.utcnow()
                session.commit()
        except Exception as _upd_err:
            session.rollback()
        finally:
            session.close()

    # 2. Mantener sincronizado el mapa de memoria
    state_map = _MILESTONE_STATE.get(case_id)
    if not state_map:
        _MILESTONE_STATE[case_id] = {}
        state_map = _MILESTONE_STATE[case_id]

    state_map[nivel_id] = nuevo_estado
    next_id = nivel_id + 1
    if nuevo_estado == "completado" and state_map.get(next_id) in ("bloqueado", "not_started", None):
        state_map[next_id] = "en_progreso"

    path_after = await build_gamified_path(case_id)
    next_level = next((n for n in path_after.niveles if n.estado == "en_progreso"), None)

    if nuevo_estado == "completado" and target_level:
        _LAST_CELEBRATION[case_id] = CelebrationInfo(
            confetti=True,
            titulo_victoria=f"🎉 ¡Micro-Victoria! Nivel {nivel_id} superado ({target_level.recompensa_desbloqueo})",
            mensaje_motivador=f"Vuestro Score se sitúa ahora en {path_after.score_actual}/100. {target_level.por_que_importa}",
            proximo_paso_unico=(
                f"Próximo paso único: {next_level.titulo}"
                if next_level
                else "🏆 ¡Has completado todos los pasos prioritarios de tu plan!"
            ),
        )
        # Generar 'Choca esos cinco' automático entre miembros de la pareja
        if path_after.couple_info and path_after.couple_info.members:
            members = path_after.couple_info.members
            actor = completed_by or members[0].name
            partner = members[1].name if len(members) >= 2 and actor.lower() == members[0].name.lower() else members[0].name
            await add_high_five(
                case_id,
                from_member=actor,
                to_member=partner if len(members) >= 2 else actor,
                milestone_title=target_level.titulo,
                message=f"¡Choca esos cinco! He completado el Nivel {nivel_id} ({target_level.recompensa_desbloqueo}) 👋",
            )
    else:
        _LAST_CELEBRATION.pop(case_id, None)

    return await build_gamified_path(case_id)


async def reset_client_path(client_id: str) -> PathSchema:
    """Resetea el progreso de hitos y celebraciones de la familia a su estado original (en BD y memoria)."""
    case_id = normalize_case_id(client_id)
    _MILESTONE_STATE.pop(case_id, None)
    _LAST_CELEBRATION.pop(case_id, None)
    _HIGH_FIVES_STATE.pop(case_id, None)

    # Resetear estados en la BD a 'not_started' excepto el primero a 'in_progress'
    if get_session_factory is not None and milestone_repository is not None:
        session = get_session_factory()()
        try:
            db_ms = milestone_repository.list_milestones(session, case_id)
            for idx, m in enumerate(db_ms):
                m.status = "in_progress" if idx == 0 else "not_started"
                m.completed_at = None
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    return await build_gamified_path(case_id)


async def run_what_if_simulator(
    client_id: str,
    active_ids: Optional[List[str]] = None,
) -> SimulatorResponse:
    """
    Laboratorio de Decisiones Interactivo (SIN sliders):
    - Tarjetas Power-Up combinables con un clic (interruptores de decisión real).
    - Detector de Candados y Sinergias reales de `combined_moves` (ej. por qué 1+1 suma +13 puntos en los Weah).
    - Máquina del Tiempo Familiar (Comparador visual 'Si no hacéis nada' vs 'Con vuestras decisiones activas').
    """
    case_id = normalize_case_id(client_id)
    short_id = get_short_id(case_id)
    selected = set(active_ids or [])

    if case_id == "timothy-melanie-weah":
        has_card = "card" in selected
        has_life = "life" in selected
        has_umb = "umbrella" in selected

        power_ups = [
            DecisionPowerUp(
                id="card",
                icono="💳",
                titulo="Tapar la fuga de la tarjeta al 18%",
                accion_corta="Usar $6,800 (o $18,000) de vuestros $60,222 de efectivo sobrante",
                esfuerzo="Esfuerzo Bajo · Hoy mismo",
                lifts_a_cap=True,
                etiqueta_candado="🔓 Abre Candado #1 (Tope 60)",
                impacto_individual_texto="Ahorra hasta $3,240/año en intereses y quita el primer bloqueo del Score.",
                pregunta_mentor="¿Qué cambia exactamente en nuestro plan si activamos el interruptor de pagar la tarjeta al 18% con nuestro efectivo sobrante?",
                active=has_card,
            ),
            DecisionPowerUp(
                id="life",
                icono="🛡️",
                titulo="Blindar el seguro de vida para Liam y Josh",
                accion_corta="Añadir +$235,000 de cobertura familiar ($485k total)",
                esfuerzo="Esfuerzo Bajo · 1 llamada",
                lifts_a_cap=True,
                etiqueta_candado="🔓 Abre Candado #2 (Tope 62)",
                impacto_individual_texto="Por sí solo suma +0 pts si la tarjeta sigue bloqueando; unido a la tarjeta dispara +13 pts.",
                pregunta_mentor="¿Por qué activar solo el interruptor del seguro de vida no sube el Score si no quitamos también la tarjeta, y qué cambia al unirlos?",
                active=has_life,
            ),
            DecisionPowerUp(
                id="umbrella",
                icono="☂️",
                titulo="Activar Paraguas Patrimonial ($1M Umbrella)",
                accion_corta="Póliza de responsabilidad civil de $1,000,000",
                esfuerzo="Esfuerzo Bajo",
                lifts_a_cap=False,
                etiqueta_candado="⚡ Multiplicador +5 pts",
                impacto_individual_texto="Protege vuestros $695,500 de patrimonio neto y eleva el combo hasta 78 puntos.",
                pregunta_mentor="¿Qué cambia en nuestra protección y en nuestro Score al activar el interruptor de la póliza Umbrella de $1 millón?",
                active=has_umb,
            ),
        ]

        score_base = 60
        sinergia = False
        if has_card and has_life and has_umb:
            score_sim = 78
            sinergia = True
            msg_sinergia = "🏆 ¡Combo Triple Desbloqueado! Habéis roto los dos candados del Score y activado el multiplicador Umbrella (+18 puntos de golpe)."
            pregunta_combo = "Hemos activado los 3 interruptores (Tarjeta + Seguro de Vida + Umbrella) y nuestro Score sube de 60 a 78. Explícanos qué cambia en nuestra vida con este combo."
        elif has_card and has_life:
            score_sim = 73
            sinergia = True
            msg_sinergia = "⚡ ¡Sinergia Desbloqueada! Al combinar el pago de la tarjeta + el seguro de vida se rompen ambos candados y el Score salta de 60 a 73 (+13 pts)."
            pregunta_combo = "Hemos activado juntos el pago de la tarjeta y el seguro de vida y el Score salta de 60 a 73. Explícanos por qué ocurre esta sinergia."
        elif has_card and has_umb:
            score_sim = 62
            msg_sinergia = "🔒 Candado #2 aún cerrado: habéis quitado el freno de la tarjeta (+2 pts), pero falta activar el Seguro de Vida para liberar el salto hasta 78."
            pregunta_combo = "Activamos la tarjeta y el Umbrella pero el Score se queda en 62. ¿Por qué el candado del seguro de vida nos frena y cómo lo abrimos?"
        elif has_card:
            score_sim = 62
            msg_sinergia = "🔓 Candado #1 abierto (+2 pts). Activa ahora el Seguro de Vida para ver cómo salta el Score hasta 73."
            pregunta_combo = "Si solo activamos quitar la tarjeta al 18%, ¿qué ganamos hoy y por qué nos recomiendas añadir también el seguro de vida?"
        elif has_life or has_umb:
            score_sim = 60
            msg_sinergia = "🔒 ¡Candado #1 Bloqueando! Aunque actives los seguros, la tarjeta al 18% mantiene vuestro Score bloqueado en 60. ¡Activa también la tarjeta!"
            pregunta_combo = "Hemos activado los seguros pero el Score sigue bloqueado en 60 por la tarjeta al 18%. Explícanos cómo funciona este candado."
        else:
            score_sim = 60
            msg_sinergia = "👆 Toca las tarjetas de arriba para encender o combinar decisiones y descubrir cómo romper los dos candados de vuestro Score."
            pregunta_combo = "Explícanos qué cambia en nuestro plan si activamos los interruptores de pagar la tarjeta al 18% y blindar el seguro de vida."

        saved = (3240 if has_card else 0)
        timeline = [
            TimelineComparison(
                hito="Hoy · Flujo e Intereses",
                icono="💸",
                sin_cambios="Perdéis $3,240/año en la tarjeta al 18% mientras $150k rinden un 0.1%.",
                con_decisiones=(
                    "Ahorráis $3,240/año al instante y os siguen quedando más de $132,000 de colchón."
                    if has_card
                    else "Sigue abierta la fuga de $270/mes en intereses de la tarjeta."
                ),
                mejora_destacada="+$3,240/año libres" if has_card else "Pendiente",
            ),
            TimelineComparison(
                hito="Protección de Liam (6) y Josh (3)",
                icono="🛡️",
                sin_cambios="Déficit de $1.1M en seguro de vida y $0 de cobertura Umbrella.",
                con_decisiones=(
                    "Familia 100% blindada con seguro de vida reforzado y escudo de $1M."
                    if (has_life and has_umb)
                    else "Seguro de vida cubierto para los niños."
                    if has_life
                    else "Brecha de protección aún abierta."
                ),
                mejora_destacada="Paz mental para Melanie" if has_life else "Sin blindar",
            ),
            TimelineComparison(
                hito="Septiembre 2039 · Fin de Deuda",
                icono="⏳",
                sin_cambios="Tardáis 13 años (hasta 2039) en terminar de pagar la tarjeta Chase.",
                con_decisiones=(
                    "¡Deuda liquidada 13 años antes! Ese dinero puede ir al Plan 529 universitario."
                    if has_card
                    else "Seguís pagando la tarjeta hasta que Liam vaya a la universidad (2039)."
                ),
                mejora_destacada="13 años ganados" if has_card else "0 años ganados",
            ),
        ]

        return SimulatorResponse(
            client_id=case_id,
            short_id=short_id,
            household_name="Timothy & Melanie Weah",
            score_base=score_base,
            score_simulado=score_sim,
            score_delta=score_sim - score_base,
            sinergia_detectada=sinergia,
            mensaje_sinergia=msg_sinergia,
            pregunta_combo_mentor=pregunta_combo,
            ahorro_anual_dolares=saved,
            etiqueta_ahorro="Intereses anuales de tarjeta eliminados",
            impacto_tiempo="13 años menos de deuda (de 2039 a hoy)" if has_card else "Tarjeta proyectada hasta septiembre de 2039",
            resumen_visual=msg_sinergia,
            confetti=(score_sim >= 73),
            power_ups=power_ups,
            timeline_comparison=timeline,
            pact_cards=[
                PactCard(
                    card_id="melanie_only",
                    icono="🛡️",
                    titulo="100% Visión Melanie (Todo en Efectivo)",
                    subtitulo_quien="Mantener los $150,800 parados en el banco al 0.1%",
                    tranquilidad_pct=70,
                    rentabilidad_pct=20,
                    score_resultado=60,
                    veredicto="Mucha liquidez aparente, pero perdéis $3,240/año en la tarjeta y los niños siguen con déficit de seguro de vida.",
                    pregunta_mentor="¿Qué significa para nuestra familia elegir el camino '100% Visión Melanie' dejando todo en efectivo sin quitar la tarjeta?",
                    es_recomendado=False,
                ),
                PactCard(
                    card_id="timothy_only",
                    icono="📈",
                    titulo="100% Visión Timothy (Todo a Bolsa / Growth)",
                    subtitulo_quien="Invertir agresivamente en renta variable (77%+ acciones y UPRO)",
                    tranquilidad_pct=30,
                    rentabilidad_pct=85,
                    score_resultado=60,
                    veredicto="Alta volatilidad (30% en el Roth) mientras la tarjeta al 18% se come las ganancias y genera estrés familiar.",
                    pregunta_mentor="¿Qué riesgos tiene elegir '100% Visión Timothy' invirtiendo agresivo sin cubrir antes el seguro de vida ni la tarjeta?",
                    es_recomendado=False,
                ),
                PactCard(
                    card_id="sherpas_pact",
                    icono="🤝",
                    titulo="El Pacto Sherpas (Lo Mejor de Ambos)",
                    subtitulo_quien="$90k en reserva segura para Melanie + quitar tarjeta 18% y blindar seguros para Timothy",
                    tranquilidad_pct=96,
                    rentabilidad_pct=92,
                    score_resultado=78,
                    veredicto="¡Equilibrio perfecto! Melanie conserva 9 meses de paz mental intactos y Timothy logra un 18% de retorno seguro y Score 78.",
                    pregunta_mentor="Explícanos a Timothy y a mí por qué 'El Pacto Sherpas' nos hace ganar a los dos y sube nuestro Score a 78.",
                    es_recomendado=True,
                ),
            ],
        )

    if case_id == "michael-carter":
        has_umb = "umbrella" in selected
        has_withdraw = "withdrawal" in selected
        has_growth = "growth" in selected

        power_ups = [
            DecisionPowerUp(
                id="withdrawal",
                icono="🚰",
                titulo="Equilibrar ritmo de retiro y flujo anual",
                accion_corta="Ajustar extracción a banda sostenible ($10,300/año · 6.0%)",
                esfuerzo="Impacto Máximo",
                lifts_a_cap=True,
                etiqueta_candado="🚀 Gran Salto (+36 pts)",
                impacto_individual_texto="Eleva tu Score de 26 a 62 y evita quedarte sin ahorros a los 85 años.",
                pregunta_mentor="¿Qué cambia exactamente en mi jubilación y en la compra de mi casa en 2027 si activo el interruptor de equilibrar mi ritmo de retiro?",
                active=has_withdraw,
            ),
            DecisionPowerUp(
                id="umbrella",
                icono="☂️",
                titulo="Añadir escudo Umbrella de $1 Millón",
                accion_corta="Proteger tus $218,500 de patrimonio neto y salario",
                esfuerzo="Esfuerzo Bajo",
                lifts_a_cap=False,
                etiqueta_candado="+5 pts de Score",
                impacto_individual_texto="Sube el Score de 26 a 31 de forma inmediata y protege tus activos líquidos.",
                pregunta_mentor="¿Qué cambia en mi plan si activo el interruptor de la póliza Umbrella de $1 millón?",
                active=has_umb,
            ),
            DecisionPowerUp(
                id="growth",
                icono="📈",
                titulo="Alinear cartera al 88% Growth y optimizar bonos",
                accion_corta="Mover $19,900 hacia crecimiento y evitar el 24% de impuesto en JNK",
                esfuerzo="Esfuerzo Medio",
                lifts_a_cap=False,
                etiqueta_candado="+5 pts de Score",
                impacto_individual_texto="Aprovecha tus 20 años de horizonte hasta los 58 y ahorra $527/año en impuestos.",
                pregunta_mentor="¿Qué cambia en mi cartera y en mis impuestos si activo el interruptor de pasar al 88% Growth y mover el fondo JNK?",
                active=has_growth,
            ),
        ]

        score_base = 26
        score_sim = 26 + (36 if has_withdraw else 0) + (5 if has_umb else 0) + (5 if has_growth else 0)
        sinergia = has_withdraw and (has_umb or has_growth)
        msg_sinergia = (
            f"🚀 ¡Salto Conseguido! Tu Score despega de tu punto de partida (26) a Banda Estable ({score_sim}) y tu liquidez te acompaña cómodamente hasta los 91 años."
            if has_withdraw
            else "👆 Activa los interruptores de arriba para ver cómo tu disciplina de ahorro impulsa tu Score de 26 a más de 62 puntos."
        )
        pregunta_combo = (
            f"Con los interruptores que he activado mi Score sube de 26 a {score_sim}. Explícame cómo hace esto compatibles comprar la casa en 2027 y jubilarme a los 58."
            if score_sim > 26
            else "Explícame de forma motivadora qué cambia si activo los interruptores para subir mi Score de 26 a 67."
        )
        saved = (8336 if has_withdraw else 0) + (527 if has_growth else 0)
        timeline = [
            TimelineComparison(
                hito="Enero 2027 · Compra de Casa ($550k)",
                icono="🏠",
                sin_cambios="La entrada de $113,300 toma gran parte de tu cartera invertida ($178k → $81k).",
                con_decisiones=(
                    "Ritmo acompasado y cartera Growth trabajando al 88% para reponer tu base con fluidez."
                    if (has_withdraw or has_growth)
                    else "Conviene acompasar la liquidez para que la compra sea más holgada."
                ),
                mejora_destacada="Ritmo equilibrado" if has_withdraw else "Por acompasar",
            ),
            TimelineComparison(
                hito="Edad 58 (2047) · Tu Jubilación Temprana",
                icono="🌅",
                sin_cambios="Tus dos metas compiten en el tiempo si no ajustamos el ritmo de retiro.",
                con_decisiones=(
                    "Ritmo de retiro en banda cómoda (6.0%) con cartera optimizada fiscalmente."
                    if has_withdraw
                    else "Oportunidad de sincronizar el ritmo de retiro para llegar holgado a los 58."
                ),
                mejora_destacada="Retiro a los 58 viable" if has_withdraw else "Ajuste pendiente",
            ),
            TimelineComparison(
                hito="Edad 85 a 91 · Tranquilidad a Largo Plazo",
                icono="⏳",
                sin_cambios="El colchón financiero proyecta cubrir hasta los 85 años y pide un pequeño ajuste para llegar a los 91.",
                con_decisiones=(
                    "¡Tu patrimonio te acompaña con total tranquilidad hasta los 91 años!"
                    if has_withdraw
                    else "Activa el ajuste de ritmo para ganar 6 años extra de holgura."
                ),
                mejora_destacada="+6 años de holgura" if has_withdraw else "Hasta los 85 años",
            ),
        ]

        return SimulatorResponse(
            client_id=case_id,
            short_id=short_id,
            household_name="Michael Carter",
            score_base=score_base,
            score_simulado=score_sim,
            score_delta=score_sim - score_base,
            sinergia_detectada=sinergia,
            mensaje_sinergia=msg_sinergia,
            pregunta_combo_mentor=pregunta_combo,
            ahorro_anual_dolares=saved,
            etiqueta_ahorro="Flujo de caja e impuestos optimizados al año",
            impacto_tiempo="Holgura garantizada hasta los 91 años (+6 años)" if has_withdraw else "Cobertura proyectada hasta los 85 años",
            resumen_visual=msg_sinergia,
            confetti=(score_sim >= 62),
            power_ups=power_ups,
            timeline_comparison=timeline,
            pact_cards=[
                PactCard(
                    card_id="house_rush",
                    icono="🏠",
                    titulo="Opción A: Comprar en 2027 sin Ajustar el Ritmo",
                    subtitulo_quien="Tomar los $113,300 de tus inversiones manteniendo el mismo ritmo posterior",
                    tranquilidad_pct=45,
                    rentabilidad_pct=50,
                    score_resultado=26,
                    veredicto="Cumples el sueño de la casa, pero tu cartera queda más ajustada ($81k) para jubilarte tan joven a los 58.",
                    pregunta_mentor="¿Qué implica elegir la Opción A y comprar la casa en enero de 2027 sin acompasar mi ritmo posterior?",
                    es_recomendado=False,
                ),
                PactCard(
                    card_id="retire_only",
                    icono="📈",
                    titulo="Opción B: Posponer la Casa y Priorizar Solo Retiro",
                    subtitulo_quien="Seguir de alquiler para no tocar las inversiones de jubilación",
                    tranquilidad_pct=60,
                    rentabilidad_pct=85,
                    score_resultado=48,
                    veredicto="Da holgura a tu retiro a los 58, pero dejas en pausa tu ilusión de estrenar hogar propio en Austin.",
                    pregunta_mentor="¿Qué significa elegir la Opción B y dejar en pausa la compra de mi casa?",
                    es_recomendado=False,
                ),
                PactCard(
                    card_id="sherpas_balance",
                    icono="⚡",
                    titulo="Opción C: Secuencia Sherpas (Casa en 2027 + Retiro a los 58)",
                    subtitulo_quien="Acompasar ritmo de retiro (6%) + cartera al 88% Growth + paraguas de tranquilidad",
                    tranquilidad_pct=92,
                    rentabilidad_pct=90,
                    score_resultado=67,
                    veredicto="¡Haces realidad ambas metas sin estrés! Tu Score salta de 26 a 67 y tu ahorro te acompaña hasta los 91 años.",
                    pregunta_mentor="Explícame paso a paso cómo funciona la Opción C (Secuencia Sherpas) para disfrutar de mi casa y jubilarme a los 58.",
                    es_recomendado=True,
                ),
            ],
        )

    if case_id == "daniel-emily-johnson":
        has_life = "life" in selected
        has_umb = "umbrella" in selected
        has_save = "savings" in selected

        power_ups = [
            DecisionPowerUp(
                id="life",
                icono="🛡️",
                titulo="Subir cobertura de vida familiar (+$1.16M)",
                accion_corta="Cubrir la brecha de Daniel y Emily para proteger a Oliver y Sophia",
                esfuerzo="Esfuerzo Bajo",
                lifts_a_cap=False,
                etiqueta_candado="+5 pts de Score",
                impacto_individual_texto="Sube el Score de 52 a 57 y saca el pilar de protección de 0 puntos.",
                pregunta_mentor="¿Qué cambia para Oliver y Sophia y en nuestro Score si activamos el interruptor del seguro de vida familiar?",
                active=has_life,
            ),
            DecisionPowerUp(
                id="umbrella",
                icono="☂️",
                titulo="Añadir póliza Umbrella de $1 Millón",
                accion_corta="Blindar la casa de $750,000 y los dos sueldos ($280k/año)",
                esfuerzo="Esfuerzo Bajo",
                lifts_a_cap=False,
                etiqueta_candado="+4 pts (Combo 60)",
                impacto_individual_texto="Sube de 52 a 56 solo, y combinado con seguro de vida alcanza 60 puntos.",
                pregunta_mentor="¿Qué cambia si activamos el interruptor de la póliza Umbrella de $1 millón junto con el seguro de vida?",
                active=has_umb,
            ),
            DecisionPowerUp(
                id="savings",
                icono="⚡",
                titulo="Redirigir $15,032/año a 401(k) y tarjeta al 24.9%",
                accion_corta="Activar deducción fiscal del 24% y frenar los $373/mes de intereses",
                esfuerzo="Esfuerzo Medio",
                lifts_a_cap=False,
                etiqueta_candado="+$8,080/año ahorro",
                impacto_individual_texto="Une el esfuerzo ahorrador de Emily con la reducción de deuda e impuestos de Daniel.",
                pregunta_mentor="¿Qué cambia en nuestras facturas de impuestos y en la tarjeta al 24.9% si activamos el interruptor de redirigir nuestro flujo libre?",
                active=has_save,
            ),
        ]

        score_base = 52
        sinergia = (has_life and has_umb) or (has_life and has_save)
        if has_life and (has_umb or has_save):
            score_sim = 60
            msg_sinergia = "⚡ ¡Combo Familiar Activado! En el plan de Sherpas, unir Seguro de Vida + Umbrella/Ahorro os lleva directos a la banda Estable (60 puntos)."
        elif has_umb and has_save:
            score_sim = 59
            msg_sinergia = "📈 ¡Gran avance (+7 pts)! Añadiendo el Seguro de Vida alcanzáis los 60 puntos."
        elif has_life:
            score_sim = 57
            msg_sinergia = "🛡️ +5 puntos por proteger los ingresos familiares. Combínalo con Umbrella o Ahorro para llegar a 60."
        elif has_umb:
            score_sim = 56
            msg_sinergia = "☂️ +4 puntos de escudo patrimonial."
        elif has_save:
            score_sim = 55
            msg_sinergia = "💰 +3 puntos de Score y miles de dólares ahorrados en intereses del 24.9% e impuestos."
        else:
            score_sim = 52
            msg_sinergia = "👆 Activa y combina las 3 decisiones para coordinar las cuentas de Daniel y Emily y pasar a la banda Estable (60)."

        pregunta_combo = (
            f"Hemos activado estos interruptores y nuestro Score sube de 52 a {score_sim}. Explícanos a Daniel y a Emily qué cambia en nuestra economía familiar."
            if score_sim > 52
            else "Explícanos qué cambia si activamos los interruptores para subir nuestro Score de 52 a 60."
        )
        saved = (8089 if has_save else 0)
        timeline = [
            TimelineComparison(
                hito="Cada Mes · Tarjeta Sapphire (24.9%) e Impuestos",
                icono="🔥",
                sin_cambios="Pagáis $373.50/mes solo en intereses de tarjeta y $0 deducidos en 401(k).",
                con_decisiones=(
                    "Elimináis la sangría del 24.9% y activáis el escudo fiscal del 24% en vuestros 401(k)."
                    if has_save
                    else "La tarjeta sigue consumiendo $4,482/año en intereses."
                ),
                mejora_destacada="+$8,089/año en casa" if has_save else "Sin cambios",
            ),
            TimelineComparison(
                hito="2033 y 2035 · Universidad de Oliver y Sophia",
                icono="🎓",
                sin_cambios="Pilar de seguros en 0/20: cualquier imprevisto frena el plan universitario.",
                con_decisiones=(
                    "Ingresos de papá y mamá blindados por +$1.16M + $1M Umbrella."
                    if (has_life and has_umb)
                    else "Protección en marcha para asegurar los estudios de los niños."
                    if has_life
                    else "Estudios expuestos ante imprevistos."
                ),
                mejora_destacada="Futuro de los niños blindado" if has_life else "Expuesto",
            ),
            TimelineComparison(
                hito="Enero 2034 · Liquidación de Deuda Cara",
                icono="⏳",
                sin_cambios="Tardáis hasta enero de 2034 en pagar los $18,000 de la tarjeta.",
                con_decisiones=(
                    "¡Tarjeta liquidada años antes redirigiendo el flujo libre!"
                    if has_save
                    else "Deuda activa hasta después de que Oliver entre a la universidad."
                ),
                mejora_destacada="7 años antes" if has_save else "Hasta 2034",
            ),
        ]

        return SimulatorResponse(
            client_id=case_id,
            short_id=short_id,
            household_name="Daniel & Emily Johnson",
            score_base=score_base,
            score_simulado=score_sim,
            score_delta=score_sim - score_base,
            sinergia_detectada=sinergia,
            mensaje_sinergia=msg_sinergia,
            pregunta_combo_mentor=pregunta_combo,
            ahorro_anual_dolares=saved,
            etiqueta_ahorro="Intereses (24.9%) e impuestos (24%) ahorrados al año",
            impacto_tiempo="Salís de la tarjeta 7 años antes (sin esperar a 2034)" if has_save else "Tarjeta proyectada hasta enero de 2034",
            resumen_visual=msg_sinergia,
            confetti=(score_sim >= 60),
            power_ups=power_ups,
            timeline_comparison=timeline,
            pact_cards=[
                PactCard(
                    card_id="emily_pattern",
                    icono="🎓",
                    titulo="Inercia Actual (Ahorrar sin mirar la Deuda)",
                    subtitulo_quien="Enviar $26k/año a bróker y 529 mientras la tarjeta de Daniel cobra un 24.9%",
                    tranquilidad_pct=40,
                    rentabilidad_pct=35,
                    score_resultado=52,
                    veredicto="Lo que gana Emily invirtiendo se lo come con creces el 24.9% de interés de la tarjeta y el 0% en 401(k).",
                    pregunta_mentor="¿Por qué mantener nuestra inercia actual ahorrando $26,000 al año pero dejando la tarjeta al 24.9% nos perjudica?",
                    es_recomendado=False,
                ),
                PactCard(
                    card_id="daniel_aggressive",
                    icono="📈",
                    titulo="Crecer sin Red de Protección Familiar",
                    subtitulo_quien="Centrarse solo en rentabilidad dejando pendiente el respaldo familiar de los niños",
                    tranquilidad_pct=35,
                    rentabilidad_pct=80,
                    score_resultado=52,
                    veredicto="Con vuestra casa y los proyectos de Oliver y Sophia, sumar antes una red de tranquilidad familiar os da mucha más serenidad.",
                    pregunta_mentor="¿Por qué nos da más tranquilidad cubrir primero el respaldo familiar de Oliver y Sophia antes de invertir más agresivo?",
                    es_recomendado=False,
                ),
                PactCard(
                    card_id="johnson_pact",
                    icono="🤝",
                    titulo="El Pacto Sherpas (Coordinación Total)",
                    subtitulo_quien="Blindar seguros (+9 pts combo) + atacar tarjeta 24.9% y activar 401(k)",
                    tranquilidad_pct=94,
                    rentabilidad_pct=90,
                    score_resultado=60,
                    veredicto="¡Ganáis los dos! Oliver y Sophia quedan protegidos, ahorráis más de $8,000/año y pasáis a banda Estable (60).",
                    pregunta_mentor="Explícanos a Daniel y a Emily cómo funciona 'El Pacto Sherpas' para proteger a los niños y ahorrar impuestos a la vez.",
                    es_recomendado=True,
                ),
            ],
        )

    # samantha-lewis
    has_home_ins = "home_ins" in selected
    has_vti = "vti" in selected
    has_glide = "glide" in selected

    power_ups = [
        DecisionPowerUp(
            id="home_ins",
            icono="🏡",
            titulo="Registrar y blindar póliza de vivienda ($900k)",
            accion_corta="Cerrar la brecha de cobertura sobre el activo que representa el 65% de tu patrimonio",
            esfuerzo="Esfuerzo Medio",
            lifts_a_cap=False,
            etiqueta_candado="+2 pts (82 → 84)",
            impacto_individual_texto="Es el movimiento #1 de tu plan para asegurar tu patrimonio inmobiliario libre de deuda.",
            pregunta_mentor="¿Qué impacto tiene en mi plan activar el interruptor de registrar el seguro de mi vivienda de $900,000?",
            active=has_home_ins,
        ),
        DecisionPowerUp(
            id="vti",
            icono="⚖️",
            titulo="Diversificar VTI (39% → 25%) y abrir IRA/HSA",
            accion_corta="Reequilibrar $58,300 y reducir los $3,032/año de fuga fiscal por dividendos",
            esfuerzo="Esfuerzo Medio",
            lifts_a_cap=False,
            etiqueta_candado="+$3,032/año fiscal",
            impacto_individual_texto="Reduce concentración y canaliza ahorro hacia cuentas exentas para tu jubilación.",
            pregunta_mentor="¿Qué cambia en mi factura fiscal y en mi jubilación si activo el interruptor de diversificar VTI y abrir cuentas IRA/HSA?",
            active=has_vti,
        ),
        DecisionPowerUp(
            id="glide",
            icono="🎓",
            titulo="Calibrar cartera al 80% Growth antes de pagos universitarios",
            accion_corta="Mover $17,100 de renta variable para blindar los pagos de Ethan y Ava",
            esfuerzo="Esfuerzo Medio",
            lifts_a_cap=False,
            etiqueta_candado="Estabilidad 2027-2030",
            impacto_individual_texto="Protege tu liquidez ante la universidad (2027/2028) y la compra de casa en 2030.",
            pregunta_mentor="¿Qué cambia frente a los pagos universitarios de Ethan y Ava si activo el interruptor de calibrar mi exposición al 80%?",
            active=has_glide,
        ),
    ]

    score_base = 82
    score_sim = 82 + (2 if has_home_ins else 0) + (1 if has_vti else 0) + (1 if has_glide else 0)
    sinergia = has_home_ins and has_vti and has_glide
    msg_sinergia = (
        f"🏛️ ¡Estrategia Ejecutiva Completa! Score en {score_sim}/100, vivienda de $900k blindada y horizonte de jubilación extendido más allá de los 73 años."
        if (has_home_ins or has_vti or has_glide)
        else "👆 Activa las decisiones estratégicas para eliminar el agotamiento de liquidez a los 73 años."
    )
    pregunta_combo = (
        f"He activado estos interruptores estratégicos subiendo mi Score a {score_sim}. Explícame cómo corrigen el agotamiento de mis ahorros a los 73 años."
        if score_sim > 82
        else "Explícame qué cambia en mi horizonte de jubilación si activo los tres interruptores estratégicos."
    )
    saved = (3032 if has_vti else 0) + (1408 if has_glide else 0)
    timeline = [
        TimelineComparison(
            hito="2027 - 2028 · Universidad de Ethan y Ava",
            icono="🎓",
            sin_cambios="Cartera al 85% en bolsa y solo $750 de margen sobre tu reserva de efectivo.",
            con_decisiones=(
                "Exposición ajustada al 80% y flujo protegido para cubrir las matrículas sin vender en caídas."
                if has_glide
                else "Alta exposición a volatilidad justo durante los pagos universitarios."
            ),
            mejora_destacada="Liquidez blindada" if has_glide else "Expuesta",
        ),
        TimelineComparison(
            hito="Cada Año · Fricción Fiscal en Bróker ($300k)",
            icono="📊",
            sin_cambios="Pierdes $3,032/año en impuestos por dividendos (35.8%) y $0 en cuentas de retiro.",
            con_decisiones=(
                "Concentración en VTI reducida al 25% y ahorro fiscal activado en cuentas IRA/HSA."
                if has_vti
                else "Continúa el drenaje fiscal anual en cuenta sujeta a impuestos."
            ),
            mejora_destacada="+$3,032/año netos" if has_vti else "Sin optimizar",
        ),
        TimelineComparison(
            hito="Edad 73 a 90 · Jubilación Ejecutiva",
            icono="🏛️",
            sin_cambios="Tus ahorros financieros líquidos se agotan a los 73 años (tasa de retiro 12.2%).",
            con_decisiones=(
                "¡Patrimonio inmobiliario asegurado y vida de la cartera extendida hasta los 90 años!"
                if (has_vti and has_home_ins)
                else "Avance parcial en la sostenibilidad de tu retiro."
            ),
            mejora_destacada="+17 años de solvencia" if (has_vti and has_home_ins) else "Agotamiento a los 73",
        ),
    ]

    return SimulatorResponse(
        client_id=case_id,
        short_id=short_id,
        household_name="Samantha Lewis",
        score_base=score_base,
        score_simulado=score_sim,
        score_delta=score_sim - score_base,
        sinergia_detectada=sinergia,
        mensaje_sinergia=msg_sinergia,
        pregunta_combo_mentor=pregunta_combo,
        ahorro_anual_dolares=saved,
        etiqueta_ahorro="Ahorro anual en fricción fiscal y dividendos",
        impacto_tiempo="Horizonte de liquidez extendido de 73 a 90 años" if has_vti else "Liquidez proyectada hasta los 73 años",
        resumen_visual=msg_sinergia,
        confetti=(score_sim >= 85),
        power_ups=power_ups,
        timeline_comparison=timeline,
        pact_cards=[
            PactCard(
                card_id="status_quo_82",
                icono="⚠️",
                titulo="Confiarse en el Score 82 (100% Bróker Sujeto a Impuestos)",
                subtitulo_quien="Seguir ahorrando $60k/año en cuenta normal con 85% acciones y $0 en retiro",
                tranquilidad_pct=50,
                rentabilidad_pct=60,
                score_resultado=82,
                veredicto="Espejismo financiero: pierdes $3,032/año en impuestos sobre dividendos y tu liquidez se agota a los 73 años.",
                pregunta_mentor="¿Qué significa quedarme en mi situación actual confiándome en mi Score de 82 sin abrir cuentas de jubilación?",
                es_recomendado=False,
            ),
            PactCard(
                card_id="ultra_conservative",
                icono="🏦",
                titulo="Refugio Defensivo (Pasar Cartera a Renta Fija)",
                subtitulo_quien="Bajar drásticamente acciones sin corregir la estructura fiscal ni el seguro de hogar",
                tranquilidad_pct=65,
                rentabilidad_pct=35,
                score_resultado=80,
                veredicto="Los bonos en cuenta ordinaria tributan aún más alto (35.8%, como tu fondo JNK) y frenan tu crecimiento.",
                pregunta_mentor="¿Por qué pasar mi cartera a renta fija en una cuenta sujeta a impuestos empeora mi carga fiscal?",
                es_recomendado=False,
            ),
            PactCard(
                card_id="sherpas_executive",
                icono="🏛️",
                titulo="Estrategia Patrimonial Sherpas (Optimización Integral)",
                subtitulo_quien="Póliza de vivienda + diversificar VTI al 25% + abrir cuentas IRA/HSA",
                tranquilidad_pct=97,
                rentabilidad_pct=95,
                score_resultado=86,
                veredicto="¡Blindaje total! Aseguras el activo de $900k, eliminas la fuga fiscal y tu cartera dura hasta los 90 años.",
                pregunta_mentor="Explícame con rigor ejecutivo qué gano aplicando la Estrategia Patrimonial Sherpas en mi jubilación e impuestos.",
                es_recomendado=True,
            ),
        ],
    )


async def get_mentor_insights(client_id: str) -> MentorInsightsResponse:
    """
    Devuelve la notificación proactiva del Mentor IA y las píldoras 'Traductor de Jerga'
    con metáforas visuales adaptadas a cada familia.
    """
    case_id = normalize_case_id(client_id)
    short_id = get_short_id(case_id)
    ctx = await get_compact_client_context(case_id)
    vp = resolve_voice_profile(case_id, ctx)

    cfg = MENTOR_INSIGHTS_BY_CASE.get(case_id, MENTOR_INSIGHTS_BY_CASE["timothy-melanie-weah"])
    return MentorInsightsResponse(
        client_id=case_id,
        short_id=short_id,
        style_key=vp["style_key"],
        style_label=vp["style_label"],
        proactive_nudge=ProactiveInsight(**cfg["proactive_nudge"]),
        jargon_pills=[JargonPill(**p) for p in cfg["jargon_pills"]],
    )


# Datos estructurados para el Vídeo Introductorio ("Your Financial Story") de las 4 familias
STORY_DATA_BY_CASE: Dict[str, Dict[str, Any]] = {
    "timothy-melanie-weah": {
        "main_challenge": "Tenéis $150,800 en efectivo rindiendo un 0.1% mientras arrastráis una tarjeta de $18,000 al 18% de interés.",
        "scenes": [
            {
                "scene_id": 1,
                "chapter": "1 · Vuestro Punto de Partida",
                "headline_figure": "60 / 100",
                "title": "Una base sólida en San Francisco con dos frenos ocultos",
                "subtitle": "Ingresos de $270,000/año y patrimonio neto de $695,500",
                "caption_narration": "Hola Timothy y Melanie. Vuestra salud financiera está en 60 sobre 100. Ahorráis muy bien para la jubilación, pero dos topes os impiden subir a 78.",
            },
            {
                "scene_id": 2,
                "chapter": "2 · La Paradoja de Liquidez",
                "headline_figure": "$150k vs $18k",
                "title": "Mucho efectivo parado y una deuda cara al mismo tiempo",
                "subtitle": "$150,800 en el banco (0.1%) frente a $18,000 en tarjeta Chase (18%)",
                "caption_narration": "Como dice el refrán, tenéis un cubo lleno pero con un agujero debajo: la tarjeta os cuesta $3,240 al año en intereses mientras el efectivo apenas os da $150.",
            },
            {
                "scene_id": 3,
                "chapter": "3 · Proteger a Liam y Josh",
                "headline_figure": "$1.1M",
                "title": "Brecha en el seguro de vida y universidad en 2038",
                "subtitle": "Liam (6) y Josh (3) empiezan la universidad en 2038 y 2041",
                "caption_narration": "Para que Melanie tenga tranquilidad total y Timothy vea crecer el patrimonio sin sustos, toca cubrir la brecha del seguro de vida y el fondo universitario.",
            },
            {
                "scene_id": 4,
                "chapter": "4 · Vuestro Primer Paso",
                "headline_figure": "60 → 73",
                "title": "Usar parte del efectivo excedente y blindar el seguro",
                "subtitle": "+13 puntos de Score inmediatos sin tocar vuestro colchón de emergencia",
                "caption_narration": "Vuestro Nivel 1 está listo: usad $6,800 del efectivo sobrante para quitar el tope de la tarjeta y subid el seguro de vida. Vuestro Score saltará de 60 a 73.",
            },
        ],
    },
    "michael-carter": {
        "main_challenge": "Ahorras unos admirables $43,000 al año; acompasar la compra de tu casa en 2027 con tu retiro a los 58 hará despegar tu Score de 26 a 62.",
        "scenes": [
            {
                "scene_id": 1,
                "chapter": "1 · Tu Gran Motor de Ahorro",
                "headline_figure": "26 → 62",
                "title": "Una gran capacidad de ahorro lista para sincronizarse",
                "subtitle": "Salario de $180,000 en Austin y ahorro de $43,000/año (23.9%)",
                "caption_narration": "Hola Michael. Tienes lo más difícil: ganas muy bien y ahorras $43,000 cada año. Tu puntuación inicial de 26 es solo porque tus dos grandes metas coinciden a la vez.",
            },
            {
                "scene_id": 2,
                "chapter": "2 · Enero de 2027",
                "headline_figure": "$113,300",
                "title": "Preparar con holgura la entrada de tu casa en Austin",
                "subtitle": "Acompasar la liquidez para no restar impulso a tus inversiones",
                "caption_narration": "Para estrenar tu casa en enero de 2027 con total comodidad, nos conviene ordenar de dónde sale la liquidez para que tu cartera siga creciendo con fuerza.",
            },
            {
                "scene_id": 3,
                "chapter": "3 · Libertad a los 58 Años",
                "headline_figure": "Hasta los 91",
                "title": "Alargar el recorrido de tu cartera para disfrutar tu retiro joven",
                "subtitle": "Un ajuste suave de ritmo extiende tu tranquilidad 6 años más",
                "caption_narration": "Con un pequeño ajuste en el ritmo de retiro previsto, tu dinero te acompañará con total holgura desde los 58 hasta los 91 años.",
            },
            {
                "scene_id": 4,
                "chapter": "4 · Tu Primer Paso",
                "headline_figure": "+36 pts",
                "title": "Activar tu paraguas patrimonial y acompasar el ritmo",
                "subtitle": "Un camino sencillo para hacer compatibles tu casa y tu retiro a los 58",
                "caption_narration": "Tu Nivel 1 está listo: con dos ajustes muy sencillos das un salto directo a 62 puntos y pones tus dos metas en marcha.",
            },
        ],
    },
    "daniel-emily-johnson": {
        "main_challenge": "Ahorráis $26,000 al año, pero enviáis $0 a vuestros 401(k) mientras pagáis una tarjeta de $18,000 al 24.9%.",
        "scenes": [
            {
                "scene_id": 1,
                "chapter": "1 · Radiografía Familiar",
                "headline_figure": "52 / 100",
                "title": "Dos grandes sueldos en Denver que necesitan coordinación",
                "subtitle": "Ingresos de $280,000/año, casa de $750,000 y dos hijos (Oliver y Sophia)",
                "caption_narration": "Daniel y Emily, tenéis una puntuación de 52 sobre 100. Las facturas se pagan y sobran $15,032 al año, pero cada uno gestiona su lado por separado.",
            },
            {
                "scene_id": 2,
                "chapter": "2 · El Freno del 24.9%",
                "headline_figure": "24.9% TAE",
                "title": "$18,000 en tarjeta de crédito y solo 1.4 meses de colchón",
                "subtitle": "De los $450/mes que pagáis en la tarjeta, $373.50 se van solo en intereses",
                "caption_narration": "Mientras Emily ahorra $26,000 al año en el bróker y el plan 529 de los niños, la tarjeta a nombre de Daniel os quema casi un 25% anual.",
            },
            {
                "scene_id": 3,
                "chapter": "3 · Impuestos y Protección",
                "headline_figure": "$0 al 401(k)",
                "title": "Desaprovecháis hasta $11,760/año de ahorro fiscal y seguro de vida",
                "subtitle": "Cero puntos sobre 20 en el pilar de seguros y protección familiar",
                "caption_narration": "No estáis metiendo nada en los planes 401(k) de vuestras empresas y vuestro seguro de vida está muy por debajo de lo que necesitan Oliver y Sophia.",
            },
            {
                "scene_id": 4,
                "chapter": "4 · Vuestro Primer Paso",
                "headline_figure": "52 → 60",
                "title": "Subir cobertura de vida, añadir Umbrella y reordenar el ahorro",
                "subtitle": "Un plan conjunto donde ganan tanto la seguridad de Emily como el crecimiento de Daniel",
                "caption_narration": "Completando los tres niveles de vuestro Camino subiréis el Score a 60 y pondréis cada dólar a trabajar en el orden correcto.",
            },
        ],
    },
    "samantha-lewis": {
        "main_challenge": "Tu Score es de 82 (banda Fuerte) y no tienes deudas, pero con $0 en cuentas de jubilación tus ahorros proyectados se agotan a los 73 años.",
        "scenes": [
            {
                "scene_id": 1,
                "chapter": "1 · Visión Patrimonial",
                "headline_figure": "82 / 100",
                "title": "Balance impecable de $1,395,000 con cero deudas en Miami",
                "subtitle": "Ingresos de $250,000/año, vivienda de $900,000 pagada y $415,000 líquidos",
                "caption_narration": "Samantha, tu puntuación de 82 refleja tu excelente disciplina: cero deudas, buena liquidez y $2 millones en cobertura de vida y responsabilidad civil.",
            },
            {
                "scene_id": 2,
                "chapter": "2 · El Riesgo Oculto tras el 82",
                "headline_figure": "73 años",
                "title": "Por qué un Score alto esconde un agotamiento temprano en la jubilación",
                "subtitle": "$0 en cuentas de jubilación y tasa de extracción inicial del 12.2%",
                "caption_narration": "Aquí está el dato estratégico clave: el 65% de tu patrimonio es tu casa ilíquida. Sin cuentas de jubilación, tu cartera financiera se agota a los 73 años.",
            },
            {
                "scene_id": 3,
                "chapter": "3 · Universidad y Eficiencia Fiscal",
                "headline_figure": "$3,032 / año",
                "title": "Fuga fiscal en tu bróker y pagos de universidad de Ethan y Ava",
                "subtitle": "VTI concentra el 39% de tu liquidez y pagas un 35.8% de impuestos sobre dividendos",
                "caption_narration": "Con Ethan ya en la universidad y Ava empezando en 2028, invertir solo en cuenta sujeta a impuestos sin usar un IRA o HSA te resta eficiencia cada año.",
            },
            {
                "scene_id": 4,
                "chapter": "4 · Tu Estrategia Ejecutiva",
                "headline_figure": "82 → 84+",
                "title": "Asegurar el activo inmobiliario, diversificar VTI y abrir vehículos fiscales",
                "subtitle": "Tres movimientos de precisión para blindar tu jubilación hasta los 91 años",
                "caption_narration": "Pasa a tu hoja de ruta para registrar la cobertura de tu vivienda, reequilibrar tu exposición en VTI y hablar con tu mentor ejecutivo.",
            },
        ],
    },
}


async def build_financial_story(client_id: str) -> StorySchema:
    """
    Construye el paquete completo de datos y guion para el reproductor de Vídeo Introductorio
    ('Your Financial Story') para cualquiera de las 4 familias.
    """
    case_id = normalize_case_id(client_id)
    short_id = get_short_id(case_id)

    ctx, path_data = await asyncio.gather(
        get_compact_client_context(case_id),
        build_gamified_path(case_id),
    )
    voice_profile = resolve_voice_profile(case_id, ctx)

    fh_case = ctx.get("household") or {}
    city = fh_case.get("city", "")
    state = fh_case.get("state", "")

    story_cfg = STORY_DATA_BY_CASE.get(case_id, STORY_DATA_BY_CASE["timothy-melanie-weah"])
    scenes = [StoryScene(**s) for s in story_cfg["scenes"]]
    full_script = " ".join(s.caption_narration for s in scenes)

    first_level = path_data.niveles[0] if path_data.niveles else None
    first_step_cta = (
        {
            "nivel_id": first_level.nivel_id,
            "titulo": first_level.titulo,
            "score_impacto": first_level.score_impacto,
            "score_after": first_level.score_after,
            "pregunta_mentor": first_level.pregunta_mentor,
        }
        if first_level
        else {}
    )

    return StorySchema(
        client_id=case_id,
        short_id=short_id,
        household_title=path_data.household_name or case_id,
        city=city,
        state=state,
        is_couple=ctx["is_couple"],
        score=path_data.score_actual,
        band=path_data.banda_salud,
        voice_name=voice_profile["voice_name"],
        style_key=voice_profile["style_key"],
        style_label=voice_profile["style_label"],
        main_challenge=story_cfg["main_challenge"],
        scenes=scenes,
        full_narration_script=full_script,
        first_step_cta=first_step_cta,
    )
