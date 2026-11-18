 ## 1. Requisitos previos                                                                                                               
                                                                                                                                         
  • Python 3.11+ (recomendado 3.12) y uv (o pip)                                                                                         
  • Node.js >= 20.11 y pnpm                                                                                                              
  • Docker + Docker Compose (solo si vas a desplegar con project/deploy)                                                                 
  ──────                                                                                                                                 
  ## 2. Ejecutar el Backend (project/backend)                                                                                            
                                                                                                                                         
  Documentación y configuración en hackathon-sherpas-upv-2026/project/backend/README.md,                                                 
  hackathon-sherpas-upv-2026/project/backend/Makefile y hackathon-sherpas-upv-2026/project/backend/.env.example.                         
                                                                                                                                         
  ### En Windows (PowerShell)                                                                                                            
                                                                                                                                         
    cd hackathon-sherpas-upv-2026\project\backend                                                                                        
                                                                                                                                         
    # 1. Crear entorno virtual e instalar dependencias                                                                                   
    uv venv --python 3.12 .venv                                                                                                          
    uv pip install --python .venv\Scripts\python.exe -e ".[dev]"                                                                         
    # (Alternativa sin uv: python -m venv .venv; .\.venv\Scripts\pip.exe install -r requirements.txt)                                    
                                                                                                                                         
    # 2. Configurar variables de entorno (si no existe .env)                                                                             
    Copy-Item .env.example .env                                                                                                          
    # Edita .env y añade tu AI_API_KEY (o TEAM_KEY) y, si usas MCP, MCP_TOKEN.                                                           
    # Con CASE_SOURCE=auto usa los casos locales de ../../cases si el MCP no está disponible.                                            
                                                                                                                                         
    # 3. Crear la base de datos SQLite y aplicar migraciones                                                                             
    .\.venv\Scripts\alembic.exe upgrade head                                                                                             
                                                                                                                                         
    # 4. Arrancar el servidor (puerto 8001)                                                                                              
    .\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8001                                                                        
                                                                                                                                         
  ### En Linux / macOS / WSL                                                                                                             
                                                                                                                                         
    cd hackathon-sherpas-upv-2026/project/backend                                                                                        
    make install                                                                                                                         
    cp .env.example .env   # rellena AI_API_KEY / TEAM_KEY                                                                               
    make migrate                                                                                                                         
    make dev                                                                                                                             
                                                                                                                                         
  • API y Swagger disponibles en: http://127.0.0.1:8001/docs                                                                             
  ──────                                                                                                                                 
  ## 3. Ejecutar el Frontend (project/frontend)                                                                                          
                                                                                                                                         
  Abre otra terminal. Documentación en hackathon-sherpas-upv-2026/project/frontend/README.md y                                           
  hackathon-sherpas-upv-2026/project/frontend/.env.example.                                                                              
                                                                                                                                         
    cd hackathon-sherpas-upv-2026\project\frontend                                                                                       
                                                                                                                                         
    # 1. Instalar dependencias                                                                                                           
    pnpm install                                                                                                                         
                                                                                                                                         
    # 2. Conectar el frontend con el backend local                                                                                       
    Copy-Item .env.example .env.local                                                                                                    
                                                                                                                                         
  Edita project/frontend/.env.local y descomenta/ajusta:                                                                                 
                                                                                                                                         
    VITE_BACKEND_API_URL=http://127.0.0.1:8001                                                                                           
    VITE_MENTOR_FALLBACK=scripted                                                                                                        
                                                                                                                                         
  (Si no configuras VITE_BACKEND_API_URL, el frontend funciona en modo estático de demostración sin hacer peticiones al backend).        
                                                                                                                                         
    # 3. Arrancar en modo desarrollo                                                                                                     
    pnpm dev                                                                                                                             
                                                                                                                                         
  • Aplicación disponible en: http://localhost:5173                                                                                      
  • Otros comandos útiles (hackathon-sherpas-upv-2026/project/frontend/package.json): pnpm build (compilar producción), pnpm preview     
  (servir build), pnpm lint.                                                                                                             
  ──────                                                                                                                                 
  ## 4. Ejecutar el Generador de Vídeo (project/video-generator) (opcional)                                                              
                                                                                                                                         
  Configuración en hackathon-sherpas-upv-2026/project/video-generator/package.json y                                                     
  hackathon-sherpas-upv-2026/project/video-generator/.env.example.                                                                       
                                                                                                                                         
    cd hackathon-sherpas-upv-2026\project\video-generator                                                                                
    npm install                                                                                                                          
    Copy-Item .env.example .env   # configura LLM_BASE_URL y LLM_API_KEY si no usas DEMO_MODE=true                                       
    npm run dev                                                                                                                          
                                                                                                                                         
  • Servidor disponible por defecto en: http://127.0.0.1:3000                                                                            
  ──────                                                                                                                                 
  ## 5. Despliegue completo con Docker (project/deploy)                                                                                  
                                                                                                                                         
  Para levantar frontend (Nginx) + backend (FastAPI) detrás de un nginx-proxy existente                                                  
  (hackathon-sherpas-upv-2026/project/deploy/README.md, hackathon-sherpas-upv-2026/project/deploy/compose.yaml):                         
                                                                                                                                         
    cd hackathon-sherpas-upv-2026/project/deploy                                                                                         
    cp .env.example .env                                                                                                                 
    cp backend.env.example backend.env                                                                                                   
    # Edita .env (DOMAIN, PROXY_NETWORK, LETSENCRYPT_EMAIL)                                                                              
    # Edita backend.env (AI_API_KEY / TEAM_KEY, ALLOWED_CASE_IDS, MCP_TOKEN)                                                             
                                                                                                                                         
    htpasswd -cB htpasswd demo                                                                                                           
    chmod 600 .env backend.env                                                                                                           
    chmod 644 htpasswd                                                                                                                   
    docker compose up -d --build   