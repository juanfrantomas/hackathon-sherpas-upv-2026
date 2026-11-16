import os
import json
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

load_dotenv()

MCP_URL = os.getenv("MCP_URL")
MCP_TOKEN = os.getenv("MCP_TOKEN")

async def get_section(case_id: str, part: str, section: str = None):
    if not MCP_URL or not MCP_TOKEN:
        print("⚠️ ADVERTENCIA: Faltan las credenciales del MCP en el archivo .env")
        return "Faltan credenciales" if part == "persona" else {"error": "Credenciales faltantes"}

    try:
        http = create_mcp_http_client(headers={"Authorization": f"Bearer {MCP_TOKEN}"})
        
        async with streamable_http_client(MCP_URL, http_client=http) as (read, write, *_):
            async with ClientSession(read, write) as mcp:
                await mcp.initialize()
                
                argumentos = {"caseId": case_id, "part": part}
                if section:
                    argumentos["section"] = section
                    
                r = await mcp.call_tool("get_case", argumentos)
                texto_respuesta = r.content[0].text
                
                # Adaptación para main.py: persona es texto Markdown, el resto es JSON
                if part == "persona":
                    return texto_respuesta
                    
                return json.loads(texto_respuesta)["value"]
                
    except BaseException as e: # BaseException atrapa ExceptionGroups y TaskGroups
        print(f"🚨 Error conectando al MCP de Sherpas: {e}")
        
        # Salvavidas adaptado al tipo de dato que espera main.py
        if part == "persona":
            return "Perfil genérico de respaldo. El cliente asume riesgos moderados y busca tranquilidad financiera."
            
        return {
            "liabilities": "El cliente tiene un préstamo de un Tesla por 10.000$ al 4.5% y una deuda de tarjeta de 18.000$ al 18%.",
            "score": "Su salud financiera es de 60 sobre 100.",
            "warning": "Datos de fallback porque el MCP real falló"
        }   