"""
config.py
---------
Configuración central del backend.
Carga las variables de entorno (.env), normaliza las URLs del proxy de IA
tanto para HTTP (REST) como para WebSocket (Realtime), e inicializa el cliente
asíncrono de OpenAI (llm_client) que utiliza el token del equipo.
"""

import os
import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
load_dotenv()

# Normalizamos LLM_PROXY_URL para HTTP (/v1) y para WebSocket (wss://.../v1/realtime)
raw_proxy_url = (os.getenv("LLM_PROXY_URL") or "https://llm-hackathon.sherpaswealth.com").rstrip("/")
BASE_URL_V1 = raw_proxy_url if raw_proxy_url.endswith("/v1") else f"{raw_proxy_url}/v1"
WS_BASE_URL = BASE_URL_V1.replace("https://", "wss://").replace("http://", "ws://")

TEAM_KEY = os.getenv("TEAM_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Desactivar keep-alive evita bloqueos de sockets TLS en Windows/Python 3.14 con Cloudflare
_openai_http_client = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=0, max_connections=20),
    headers={"Connection": "close"},
    timeout=httpx.Timeout(12.0, connect=3.0),
)

llm_client = AsyncOpenAI(
    base_url=BASE_URL_V1,
    api_key=TEAM_KEY,
    http_client=_openai_http_client,
    max_retries=1,
)

VALID_REALTIME_MODELS = {"gpt-realtime-2.1-mini", "gpt-realtime-2.1", "gemini-3.8-live"}
