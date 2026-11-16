import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Importamos la librería del LLM (usando el estándar de OpenAI)
from openai import AsyncOpenAI

# Importamos nuestros propios archivos
from model import PathSchema
from mcp_client import get_mcp_data

# Cargamos variables de entorno
load_dotenv()

app = FastAPI(title="Sherpas AI Backend", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializamos el cliente de IA apuntando al proxy del Hackathon
llm_client = AsyncOpenAI(
    base_url=os.getenv("LLM_PROXY_URL"),
    api_key=os.getenv("TEAM_KEY")
)

# --- MODELOS ---
class VoiceQuery(BaseModel):
    client_id: str
    question: str

# --- ENDPOINTS ---

@app.get("/api/path/{client_id}", response_model=PathSchema)
async def get_client_path(client_id: str):
    """
    Ruta 1: Genera el mapa visual (Path Gamificado) para el Frontend.
    """
    # Pedimos al MCP solo la salud y los objetivos para armar el mapa (ahorro brutal de tokens)
    datos_basicos = await get_mcp_data(client_id, ["score", "goals"])
    
    prompt = f"""
    Eres el motor de gamificación de Sherpas. Analiza estos datos: {datos_basicos}
    Crea 3 hitos financieros exactos para este cliente (ej: Fondo de Emergencia, Pagar Deuda, etc.).
    Devuelve estrictamente un JSON válido que encaje con nuestro PathSchema. Nada de texto extra.
    """

    response = await llm_client.chat.completions.create(
        model="gpt-4o-mini", # O el modelo que os haya indicado Sherpas
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"} 
    )
    
    # Transformamos el texto de la IA en nuestro formato de diccionario
    resultado_json = json.loads(response.choices[0].message.content)
    return resultado_json


@app.post("/api/voice/ask")
async def ask_voice_agent(query: VoiceQuery):
    """
    Ruta 2: El Agente de Voz ultrarrápido con Function Calling.
    """
    # 1. Definimos el "Menú" de herramientas para la IA (Function Calling)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "consultar_mcp",
                "description": "Obtiene datos del plan financiero del cliente. Úsala SIEMPRE antes de responder con números.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Usa 'liabilities' para deudas/préstamos. Usa 'goals' para universidad/casas. Usa 'insurance' para seguros. Usa 'accounts' para saldos y liquidez."
                        }
                    },
                    "required": ["categoria"]
                }
            }
        }
    ]

    # 2. Le pasamos la pregunta del cliente a la IA con las herramientas
    messages = [
        {"role": "system", "content": "Eres el asistente de voz de Sherpas. Eres breve, directo y profesional. Nunca inventes datos, usa tu herramienta de consultar_mcp."},
        {"role": "user", "content": query.question}
    ]

    response = await llm_client.chat.completions.create(
        model="gpt-4o-mini", # Cambiadlo por el modelo de Sherpas si hace falta
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    mensaje_ia = response.choices[0].message

    # 3. Comprobamos si la IA ha decidido usar la herramienta (¡Aquí ocurre la magia!)
    if mensaje_ia.tool_calls:
        tool_call = mensaje_ia.tool_calls[0]
        argumentos = json.loads(tool_call.function.arguments)
        categoria_pedida = argumentos.get("categoria") # Ej: "liabilities"
        
        # Llamamos a TU función del MCP solo con la clave pedida
        datos_mcp = await get_mcp_data(query.client_id, [categoria_pedida])
        
        # Le devolvemos el pequeño bloque de datos a la IA para que formule la respuesta final
        messages.append(mensaje_ia)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(datos_mcp)
        })
        
        respuesta_final = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        
        texto_final = respuesta_final.choices[0].message.content
        
        return {
            "status": "success",
            "mcp_usado": True,
            "categoria_extraida": categoria_pedida,
            "respuesta_ia": texto_final
        }
    
    # Si la IA decide responder sin usar la herramienta (para saludos o cosas genéricas)
    return {
        "status": "success",
        "mcp_usado": False,
        "respuesta_ia": mensaje_ia.content
    }