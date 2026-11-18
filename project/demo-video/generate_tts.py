"""Generate AI voiceover MP3 files for each scene in scenes.json using edge-tts."""

import asyncio
import json
import os
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print(
        "ERROR: 'edge-tts' no está instalado. Instálalo con:\n  pip install edge-tts",
        file=sys.stderr,
    )
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent
SCENES_FILE = BASE_DIR / "scenes.json"
AUDIO_DIR = BASE_DIR / "output" / "audio"


async def synthesize_scene(scene: dict, voice: str, rate: str, force: bool) -> Path:
    out_path = AUDIO_DIR / f"{scene['id']}.mp3"
    if out_path.exists() and not force:
        print(f"  [cache] {out_path.name}")
        return out_path

    communicate = edge_tts.Communicate(scene["narration"], voice=voice, rate=rate)
    await communicate.save(str(out_path))
    print(f"  [tts]   {out_path.name}")
    return out_path


async def main() -> None:
    force = "--force" in sys.argv
    config = json.loads(SCENES_FILE.read_text(encoding="utf-8"))
    voice = os.environ.get("TTS_VOICE", config.get("voice", "es-ES-AlvaroNeural"))
    rate = os.environ.get("TTS_RATE", config.get("rate", "+0%"))

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generando locuciones IA ({voice}, rate={rate})...")

    for scene in config["scenes"]:
        await synthesize_scene(scene, voice, rate, force)


if __name__ == "__main__":
    asyncio.run(main())
