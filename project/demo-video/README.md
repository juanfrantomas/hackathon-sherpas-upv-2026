# Generador automático de Video Demo (2 min, MP4)

Este directorio genera un video `.mp4` de ~2 minutos que muestra las pantallas reales de **MySherpas** junto con locución neuronal generada por IA (`edge-tts`) y títulos de cada feature.

## Requisitos (una sola vez)

1. Instalar `edge-tts` en Python:
   ```bash
   pip install edge-tts
   ```
2. `ffmpeg` y `ffprobe` ya se detectan automáticamente desde `../video-generator/node_modules/@remotion/compositor-win32-x64-msvc/`.

## Cómo generar el video

1. Arranca el frontend en otra terminal:
   ```bash
   cd ../frontend
   pnpm dev
   ```
2. Ejecuta el script capturando las pantallas reales y montando el MP4:
   ```bash
   cd ../demo-video
   node build_demo_video.mjs --capture http://localhost:5173
   ```

El resultado se guarda en:
- `output/demo-features-2min.mp4`

## Personalizar guion o voz

- Edita textos, títulos o escenas en `scenes.json`.
- Cambia la voz IA con la variable `TTS_VOICE` (por ejemplo `es-ES-ElviraNeural` o `en-US-AndrewNeural`) y vuelve a ejecutar con `--force-tts`:
  ```bash
  node build_demo_video.mjs --force-tts
  ```
