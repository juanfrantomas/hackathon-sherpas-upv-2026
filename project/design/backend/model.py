from pydantic import BaseModel, Field
from typing import List, Literal

class Nivel(BaseModel):
    nivel_id: int = Field(description="Número secuencial del nivel (1, 2, 3...)")
    titulo: str = Field(description="Título motivador del hito financiero")
    descripcion: str = Field(description="Qué debe hacer el cliente para superar este nivel")
    estado: Literal["completado", "en_progreso", "bloqueado"] = Field(description="Estado actual del nivel")
    progreso_porcentaje: int = Field(ge=0, le=100, description="Porcentaje de avance (0 a 100)")
    recompensa_desbloqueo: str = Field(description="Qué gana al superarlo (ej: Insignia de Bronce, Video educativo)")

class PathSchema(BaseModel):
    niveles: List[Nivel] = Field(description="Lista de hitos financieros gamificados ordenados cronológicamente")