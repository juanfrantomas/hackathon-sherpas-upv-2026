"""
main.py
-------
Punto de entrada principal de la aplicación FastAPI.
Configura middlewares (CORS), monta las carpetas de archivos estáticos
y registra las rutas modulares HTTP (routes.api) y WebSocket (routes.ws).
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes.api import router as api_router
from routes.ws import router as ws_router

# Crear carpeta de assets estáticos
os.makedirs("assets", exist_ok=True)

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

# Archivos estáticos
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Routers desacoplados
app.include_router(api_router)
app.include_router(ws_router)
