"""
models.py
---------
Modelos de datos y esquemas Pydantic del backend:
- Nivel, GoalStop y PathSchema: Mapa de Viaje financiero gamificado con paradas de metas vitales y micro-victorias.
- DecisionPowerUp, TimelineComparison, SimulatorRequest y SimulatorResponse: Laboratorio de Decisiones (Power-Ups combinables + Máquina del Tiempo Antes/Después, sin sliders).
- ProactiveInsight, JargonPill y MentorInsightsResponse: Mentor IA Proactivo y Traductor de Jerga con metáforas.
- CoupleMember, KidsGoalItem, HighFiveItem y CoupleOverview: Modo Multijugador Familiar (Pareja + Vista Hijos).
- StoryScene y StorySchema: Estructura del vídeo introductorio ('Your Financial Story').
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


class GoalStop(BaseModel):
    goal_id: str
    icono: str
    titulo: str
    anio_objetivo: str
    importe_objetivo: str
    progreso_porcentaje: int
    mensaje_familiar: str


class CelebrationInfo(BaseModel):
    confetti: bool = False
    titulo_victoria: str = ""
    mensaje_motivador: str = ""
    proximo_paso_unico: str = ""


class Nivel(BaseModel):
    nivel_id: int = Field(description="Número secuencial del nivel (1, 2, 3...)")
    id: Optional[str] = Field(default="", description="ID persistido en base de datos (ms_xxx)")
    move_key: Optional[str] = Field(default="", description="Identificador original del hito en el plan o anchor")
    category: Optional[str] = Field(default="Debt", description="Categoría temática del hito (Debt, Savings, Investments...)")
    type: Optional[str] = Field(default="educational", description="Tipo de hito: educational o financial")
    priority: Optional[str] = Field(default="high", description="Prioridad: high, medium o low")
    titulo: str = Field(description="Título motivador del hito financiero en español")
    descripcion: str = Field(description="Qué debe hacer el cliente para superar este nivel")
    por_que_importa: Optional[str] = Field(default="", description="Explicación clara del impacto en su vida familiar")
    estado: Literal["completado", "en_progreso", "bloqueado", "needs_review", "not_started", "cancelled"] = Field(description="Estado actual del nivel")
    progreso_porcentaje: int = Field(ge=0, le=100, description="Porcentaje de avance (0 a 100)")
    task_progress: Optional[int] = Field(default=None, description="Avance porcentual de las tareas asociadas")
    financial_progress: Optional[float] = Field(default=None, description="Avance financiero medible")
    tasks: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Lista de tareas del hito")
    esfuerzo: Optional[str] = Field(default="medium", description="Nivel de esfuerzo estimado: low, medium, high")
    score_before: Optional[int] = Field(default=0, description="Score antes de aplicar el hito")
    score_after: Optional[int] = Field(default=0, description="Score proyectado al superar el hito")
    score_impacto: Optional[int] = Field(default=0, description="Puntos que suma a la salud financiera al superarlo")
    lifts_a_cap: Optional[bool] = Field(default=False, description="Indica si este paso elimina una penalización/tope del Score")
    recompensa_desbloqueo: str = Field(description="Qué gana al superarlo (ej: +11 Puntos de Score, Insignia de Protección)")
    pregunta_mentor: Optional[str] = Field(default="", description="Pregunta contextual para abrir el Mentor de voz desde este hito")


class CoupleMember(BaseModel):
    key: str
    name: str
    role: str
    age: int
    retirement_age: Optional[int] = None
    risk_profile: str
    personal_focus: str


class KidsGoalItem(BaseModel):
    id: str
    icono: str
    titulo_amigable: str
    meta_visual: str
    progreso_porcentaje: int
    explicacion_ninos: str


class HighFiveItem(BaseModel):
    id: str
    from_member: str
    to_member: str
    milestone_title: str
    message: str
    timestamp: str


class CoupleOverview(BaseModel):
    is_couple: bool
    members: List[CoupleMember]
    consensus_bridge: str
    kids_safe_view: Optional[List[KidsGoalItem]] = Field(default_factory=list)
    high_fives: Optional[List[HighFiveItem]] = Field(default_factory=list)


class PathSchema(BaseModel):
    client_id: str = Field(description="Identificador oficial del cliente")
    short_id: Optional[str] = Field(default="", description="ID corto para el frontend (weah, carter, johnson, lewis)")
    household_name: Optional[str] = Field(default="", description="Nombre de la familia")
    indicador_actual: Optional[str] = Field(default="", description="Frase estilo GPS: 'Estáis aquí. Siguiente parada: ...'")
    score_inicial: Optional[int] = Field(default=0, description="Puntuación original antes de completar hitos")
    score_actual: int = Field(description="Puntuación actual de salud financiera (0-100), sube al completar niveles")
    score_potencial_maximo: Optional[int] = Field(default=0, description="Score máximo alcanzable al completar todos los niveles")
    banda_salud: str = Field(description="Banda actual: critical, vulnerable, stable, strong")
    total_niveles: int = Field(description="Número total de hitos en su camino")
    niveles_completados: Optional[int] = Field(default=0, description="Número de niveles superados")
    niveles: List[Nivel] = Field(description="Lista de hitos financieros gamificados ordenados cronológicamente")
    paradas_metas: Optional[List[GoalStop]] = Field(default_factory=list, description="Metas vitales de la familia como paradas del viaje")
    celebration: Optional[CelebrationInfo] = Field(default=None, description="Datos de micro-victoria y confeti al completar un paso")
    prompts_sugeridos: Optional[List[str]] = Field(default_factory=list, description="Preguntas sugeridas para el Mentor de voz")
    couple_info: Optional[CoupleOverview] = Field(default=None, description="Información del Modo Multijugador Familiar")


class MilestoneUpdateRequest(BaseModel):
    nivel_id: int = Field(description="ID del nivel a actualizar (1, 2, 3...)")
    estado: Literal["completado", "en_progreso", "bloqueado", "needs_review"] = Field(default="completado")
    completed_by: Optional[str] = Field(default=None, description="Nombre del miembro de la pareja que completó el paso")


class HighFiveRequest(BaseModel):
    from_member: str
    to_member: str
    milestone_title: str
    message: Optional[str] = "¡Choca esos cinco! Un paso más cerca de nuestra meta familiar 👋"


class DecisionPowerUp(BaseModel):
    id: str
    icono: str
    titulo: str
    accion_corta: str
    esfuerzo: str
    lifts_a_cap: bool = False
    etiqueta_candado: str = ""
    impacto_individual_texto: str
    pregunta_mentor: str = ""
    active: bool = False


class TimelineComparison(BaseModel):
    hito: str
    icono: str
    sin_cambios: str
    con_decisiones: str
    mejora_destacada: str


class PactCard(BaseModel):
    card_id: str
    icono: str
    titulo: str
    subtitulo_quien: str
    tranquilidad_pct: int
    rentabilidad_pct: int
    score_resultado: int
    veredicto: str
    pregunta_mentor: str = ""
    es_recomendado: bool = False


class SimulatorRequest(BaseModel):
    active_ids: List[str] = Field(default_factory=list, description="IDs de las tarjetas Power-Up activadas por el usuario")
    preset: Optional[str] = Field(default=None, description="Preset opcional de escenario")


class SimulatorResponse(BaseModel):
    client_id: str = Field(description="ID del caso")
    short_id: str
    household_name: str
    score_base: int
    score_simulado: int
    score_delta: int
    sinergia_detectada: bool
    mensaje_sinergia: str
    pregunta_combo_mentor: str = ""
    ahorro_anual_dolares: int
    etiqueta_ahorro: str
    impacto_tiempo: str
    resumen_visual: str
    confetti: bool
    power_ups: List[DecisionPowerUp]
    timeline_comparison: List[TimelineComparison]
    pact_cards: Optional[List[PactCard]] = Field(default_factory=list)


class JargonPill(BaseModel):
    term: str
    short_tag: str
    metaphor_title: str
    metaphor_explanation: str
    family_impact: str
    voice_question: str


class ProactiveInsight(BaseModel):
    badge: str
    greeting: str
    message: str
    cta_label: str
    voice_question: str


class MentorInsightsResponse(BaseModel):
    client_id: str
    short_id: str
    style_key: str
    style_label: str
    proactive_nudge: ProactiveInsight
    jargon_pills: List[JargonPill]


class StoryScene(BaseModel):
    scene_id: int
    chapter: str
    headline_figure: str
    title: str
    subtitle: str
    caption_narration: str


class StorySchema(BaseModel):
    client_id: str
    short_id: str
    household_title: str
    city: str
    state: str
    is_couple: bool
    score: int
    band: str
    voice_name: str
    style_key: str
    style_label: str
    main_challenge: str
    scenes: List[StoryScene]
    full_narration_script: str
    first_step_cta: Dict[str, Any]
