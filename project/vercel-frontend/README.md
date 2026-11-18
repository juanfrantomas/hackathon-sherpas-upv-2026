# MySherpas Frontend para Vercel

Esta carpeta contiene el frontend estático listo para desplegar en **Vercel** manteniendo intacto `http://localhost:8000/`.

## Contenido
- `index.html` — copia de `../test_voice.html` (vista escritorio).
- `mobile.html` — copia de `../mobile.html` (accesible en `/mobile` gracias a `cleanUrls: true`).
- `vercel.json` — redirige `/api/*` y `/videos/*` hacia tu backend FastAPI.

## Pasos para desplegar

1. **Arranca el backend en local** (si no está ya encendido):
   ```powershell
   cd project\backend
   uvicorn main:app --host 127.0.0.1 --port 8000
   ```

2. **Expón el puerto 8000 por HTTPS** (por ejemplo con Cloudflare Tunnel o ngrok, o súbelo a Railway/Render):
   ```powershell
   cloudflared tunnel --url http://127.0.0.1:8000
   ```
   Copia la URL `https://....trycloudflare.com` que te devuelva.

3. **Actualiza `vercel.json`** cambiando `https://TU-BACKEND-URL.trycloudflare.com` por tu URL real del paso 2.

4. **Despliega en Vercel**:
   - Desde CLI:
     ```powershell
     cd project\vercel-frontend
     npx vercel --prod
     ```
   - O desde el panel web de Vercel: importa el repo y pon **Root Directory** = `project/vercel-frontend`.
