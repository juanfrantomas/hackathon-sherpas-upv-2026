import os
import httpx
from dotenv import load_dotenv

# Cargamos el archivo .env
load_dotenv()

MCP_URL = os.getenv("MCP_URL")
MCP_TOKEN = os.getenv("MCP_TOKEN")

async def get_mcp_data(client_id: str, keys: list[str]) -> dict:
    """
    Se conecta al MCP de Sherpas para pedir solo los fragmentos necesarios del JSON.
    client_id: ej. "timothy-melanie-weah"
    keys: ej. ["liabilities", "goals"]
    """
    if not MCP_URL or not MCP_TOKEN:
        print("⚠️ ADVERTENCIA: Faltan las credenciales del MCP en el archivo .env")
        return {"error": "Credenciales faltantes"}

    headers = {
        "Authorization": f"Bearer {MCP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # El payload exacto dependerá de la documentación que os haya dado Sherpas, 
    # pero normalmente pedir fragmentos a un MCP por HTTP luce así:
    payload = {
        "client_id": client_id,
        "keys": keys 
    }

    # Usamos httpx para hacer una petición asíncrona rápida
    async with httpx.AsyncClient() as client:
        try:
            # Hacemos la llamada POST (Ajusta el "/extract" o "/query" según os indique Sherpas)
            response = await client.post(f"{MCP_URL}/query", json=payload, headers=headers, timeout=10.0)
            response.raise_for_status() # Lanza error si el status no es 200 OK
            return response.json()
            
        except httpx.HTTPError as e:
            print(f"🚨 Error conectando al MCP de Sherpas: {e}")
            
            # --- HACKATHON PRO-TIP (El salvavidas) ---
            # Si el wifi falla en el evento o el servidor de Sherpas se cae en vuestra demo,
            # nunca dejes que la app pete. Devuelve un fragmento "falso" para sobrevivir.
            return {
                "liabilities": "El cliente tiene un préstamo de un Tesla por 10.000$ al 4.5% y una deuda de tarjeta de 18.000$ al 18%.",
                "warning": "Datos de fallback porque el MCP real falló"
            }