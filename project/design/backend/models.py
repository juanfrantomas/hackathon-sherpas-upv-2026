"""
models.py
---------
Modelos de datos y esquemas Pydantic del backend.
Define la estructura del mapa financiero gamificado (Nivel y PathSchema)
para validar las respuestas JSON enviadas al Frontend.
"""

from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Nivel(BaseModel):
    nivel_id: int = Field(description="Número secuencial del nivel (1, 2, 3...)")
    titulo: str = Field(description="Título motivador del hito financiero")
    descripcion: str = Field(description="Qué debe hacer el cliente para superar este nivel")
    estado: Literal["completado", "en_progreso", "bloqueado"] = Field(description="Estado actual del nivel")
    progreso_porcentaje: int = Field(ge=0, le=100, description="Porcentaje de avance (0 a 100)")
    esfuerzo: Optional[str] = Field(default="medium", description="Nivel de esfuerzo estimado: low, medium, high")
    score_impacto: Optional[int] = Field(default=0, description="Puntos que suma a la salud financiera al superarlo")
    recompensa_desbloqueo: str = Field(description="Qué gana al superarlo (ej: +5 Puntos de Score, Insignia de Protección)")

class PathSchema(BaseModel):
    client_id: str = Field(description="Identificador del cliente")
    score_actual: int = Field(description="Puntuación actual de salud financiera (0-100)")
    banda_salud: str = Field(description="Banda actual: critical, vulnerable, stable, strong")
    total_niveles: int = Field(description="Número total de hitos en su camino")
    niveles: List[Nivel] = Field(description="Lista de hitos financieros gamificados ordenados cronológicamente")