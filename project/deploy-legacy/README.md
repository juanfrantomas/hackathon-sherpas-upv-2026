# Consola alternativa en mys.jftp.me

Este despliegue independiente ejecuta `project/backend/main.py` en un único contenedor, separado de `project/deploy`. Sirve la consola en `/`, el prototipo en `/prototype` y la vista móvil en `/mobile`. El estado SQLite tiene su propio volumen; no comparte datos con el otro backend. Este backend crea sus tablas al arrancar y no ejecuta las migraciones Alembic del otro despliegue.

## Antes de arrancar: proteger el dominio

El backend no tiene autenticación. Configura primero la autenticación básica de tu `nginx-proxy` para `mys.jftp.me`: debe existir un archivo htpasswd llamado `mys.jftp.me` dentro de `/etc/nginx/htpasswd/` **del contenedor proxy**. Consulta los montajes del contenedor para encontrar el directorio del servidor correspondiente:

```sh
docker inspect NOMBRE_DEL_PROXY --format '{{json .Mounts}}'
```

Crea el archivo en ese directorio del servidor con `htpasswd -cB RUTA_DEL_DIRECTORIO/mys.jftp.me USUARIO`. Si el directorio no está montado, configúralo en el despliegue del proxy y aplica el cambio antes de continuar. Verifica que el proceso de Nginx puede leer el archivo. Comprueba la configuración generada con `docker exec NOMBRE_DEL_PROXY nginx -T` y confirma que el dominio requiere credenciales; según la configuración del proxy puede ser necesario regenerarla o reiniciar el proxy. No expongas la aplicación hasta que esté protegida.

El proxy debe gestionar HTTPS para el dominio. El archivo Compose incluye variables compatibles con `nginx-proxy/acme-companion`, pero no instala ni configura el companion. Comprueba que el DNS apunta al servidor y que los puertos 80 y 443 son accesibles.

## Configuración

Desde este directorio:

```sh
cp .env.example .env
cp backend.env.example backend.env
```

En `.env`, configura `DOMAIN`, la red Docker real del proxy en `PROXY_NETWORK` y el correo para el certificado si usas acme-companion. En `backend.env`, configura `TEAM_KEY` y, si corresponde, `MCP_TOKEN` y `ELEVENLABS_API_KEY`. Protege ambos archivos:

```sh
chmod 600 .env backend.env
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs -f
```

Comprueba que `https://mys.jftp.me/` responde con 401 sin credenciales y pide usuario y contraseña, antes de usar la consola. Verifica también `/prototype`, `/mobile` y la voz WebSocket. `VOICE_ALLOWED_ORIGIN` limita los WebSockets al origen HTTPS del dominio. La autenticación compartida sirve para una demo limitada, no para datos reales o acceso individual.

## Actualización

Tras actualizar el repositorio, ejecuta `docker compose up -d --build` desde este directorio. Para comprobar los logs usa `docker compose logs -f`. No uses `docker compose down -v` si quieres conservar el volumen SQLite. Haz copias de seguridad coherentes de los datos deteniendo el servicio antes de copiar el volumen.
