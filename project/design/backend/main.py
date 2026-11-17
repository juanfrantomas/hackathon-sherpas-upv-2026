"""
main.py
-------
Punto de entrada principal de la aplicación FastAPI.
Configura middlewares (CORS) y registra las rutas modulares
HTTP (routes.api) y WebSocket (routes.ws).
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.api import router as api_router
from routes.ws import router as ws_router

app = FastAPI(
    title="Sherpas AI Backend",
    version="3.0",
    description="Servicios de voz en tiempo real y gamificación para Sherpas Wealth",
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers desacoplados
app.include_router(api_router)
app.include_router(ws_router)
