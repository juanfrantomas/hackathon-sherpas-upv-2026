"""
main.py
-------
Punto de entrada principal de la aplicación FastAPI.
Configura middlewares (CORS) y registra las rutas modulares
HTTP (routes.api) y WebSocket (routes.ws).
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.api import router as api_router
from routes.ws import router as ws_router

# Routers de la API de hitos persistentes (app.api.routers)
from app.api.routers.milestones import router as milestones_router
from app.api.routers.tasks import router as tasks_router
from app.api.routers.checkins import router as checkins_router
from app.api.routers.sync import router as sync_router
from app.api.errors import register_exception_handlers
from app.models.base import Base
from app.db.session import get_engine
import app.models  # asegura registro de todos los modelos SQLAlchemy


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización de tablas SQLite
    try:
        engine = get_engine()
        Base.metadata.create_all(engine)
    except Exception as e:
        print(f"⚠️ Warning inicializando SQLite: {e}")
    yield


app = FastAPI(
    title="Sherpas AI Backend",
    version="3.0",
    description="Servicios de voz en tiempo real, gamificación y motor de hitos AI para Sherpas Wealth",
    lifespan=lifespan,
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Manejadores de excepciones para el motor de hitos
register_exception_handlers(app)

# Routers principales
app.include_router(api_router)
app.include_router(ws_router)

# Routers REST del motor de hitos oficial
app.include_router(milestones_router)
app.include_router(tasks_router)
app.include_router(checkins_router) 
app.include_router(sync_router) 
 