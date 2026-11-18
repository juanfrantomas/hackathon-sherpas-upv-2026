# Despliegue de la demo con nginx-proxy

Docker Compose crea dos contenedores: el frontend con Nginx (autenticación y proxy interno) y FastAPI. El nginx-proxy existente termina HTTPS y envía el tráfico al frontend. El backend no publica puertos. La autenticación compartida es solo para una demo; no sustituye a la autenticación por usuario ni a una revisión de seguridad para datos reales.

## Requisitos

- Docker con Compose y el nginx-proxy existente en ejecución, en una red Docker compartida. Averigua su nombre con `docker network ls` e inspecciona el proxy con `docker inspect`.
- Un registro DNS del dominio que apunte a la IP pública del servidor y certificados HTTPS gestionados por el proxy existente. `LETSENCRYPT_HOST` y `LETSENCRYPT_EMAIL` son compatibles con acme-companion; si usáis otro gestor, configurad el certificado en ese sistema.
- Acceso saliente a los servicios de IA y MCP. El token MCP puede caducar; con `CASE_SOURCE=auto` se usan los casos locales como respaldo.

## Configuración y arranque

Ejecuta desde `project/deploy`:

```sh
cp .env.example .env
cp backend.env.example backend.env
```

Edita `.env`: indica `DOMAIN`, el nombre real de `PROXY_NETWORK` y, si corresponde, `LETSENCRYPT_EMAIL`. Edita `backend.env`: fija una lista explícita de `ALLOWED_CASE_IDS` y la clave `AI_API_KEY` (o `TEAM_KEY`); configura `MCP_TOKEN` si usas MCP. La lista vacía permite los casos de demostración por defecto. No publiques estos archivos.

Crea el archivo de autenticación sin escribir la contraseña en el historial de comandos. Instala `htpasswd` en el servidor (paquete `apache2-utils` en Debian/Ubuntu) y sustituye `demo` por el usuario deseado:

```sh
htpasswd -cB htpasswd demo
chmod 600 .env backend.env
chmod 644 htpasswd
docker compose config --quiet
docker compose up -d --build
```

El archivo `htpasswd` debe ser legible por los procesos del contenedor Nginx. Si el servidor usa remapeo de usuarios o SELinux, ajusta los permisos y etiquetas del montaje a su configuración. El comando interactivo debe finalizar antes de arrancar; un archivo vacío impedirá el acceso. No montes un directorio como `htpasswd`.

Comprueba `docker compose ps` y `docker compose logs -f`. Abre `https://TU_DOMINIO/`, autentícate y comprueba `/api/health`. Prueba los casos, cambios persistentes y el mentor con micrófono; la voz necesita credenciales y conectividad con el proveedor. El frontend puede mostrar respuestas de respaldo si la voz falla, por lo que hay que comprobar también el WebSocket en el navegador.

## Actualización y recuperación

Tras actualizar el código, ejecuta `docker compose up -d --build`. Si cambias `DOMAIN`, reconstruye el frontend: la URL de la API se incorpora en compilación. La migración se ejecuta al arrancar el backend y, si falla, el servicio no se inicia; revisa sus logs.

Para respaldar SQLite de manera consistente, detén el backend y copia el volumen con un contenedor temporal. El volumen incluye también el audio. Desde `project/deploy`:

```sh
docker compose stop backend
docker compose run --rm --no-deps --user root -v "$PWD:/backup" --entrypoint sh backend -c 'tar czf /backup/backend-data-backup.tar.gz -C /app/data .'
docker compose start backend
```

Guarda el archivo fuera del servidor y protege su acceso: contiene datos de la demo. Para restaurar una copia verificada en un volumen vacío, detén ambos servicios, conserva una copia del volumen actual y usa un contenedor temporal con el mismo montaje para extraer el archivo en `/app/data`; vuelve a iniciar con `docker compose up -d`. No uses `docker compose down -v` si deseas conservar los datos.
