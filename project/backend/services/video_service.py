"""
services/video_service.py
-------------------------
Orquesta la generación de vídeos con Remotion (project/video-generator) desde el backend FastAPI.
- Lee los documentos locales de cada familia en cases/<slug>/ (financial-health.json,
  investment-analysis.json, persona.md).
- Reutiliza las claves de backend/.env (TEAM_KEY, LLM_PROXY_URL, ELEVENLABS_API_KEY) y la voz
  asignada a cada familia.
- Ejecuta el render en segundo plano manteniendo una cola secuencial para evitar contención
  de CPU/RAM en Chromium y publica el .mp4 final directamente en project/videos/{short_id}.mp4
  para servirlo al instante en http://localhost:8000/videos/{short_id}.mp4.
"""

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import BASE_URL_V1, ELEVENLABS_API_KEY, TEAM_KEY
from mcp_client import (
    REPO_CASES_DIR,
    SHORT_ID_MAP,
    get_compact_client_context,
    get_short_id,
    normalize_case_id,
)
from services.voice_profiles import resolve_voice_profile

PROJECT_DIR = Path(__file__).resolve().parents[2]
VIDEO_GENERATOR_DIR = PROJECT_DIR / "video-generator"
VIDEOS_DIR = PROJECT_DIR / "videos"
TSX_CLI = VIDEO_GENERATOR_DIR / "node_modules" / "tsx" / "dist" / "cli.mjs"

_VIDEO_JOBS: Dict[str, Dict[str, Any]] = {}
_RENDER_LOCK = asyncio.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_case_files(client_id: str) -> Dict[str, Path]:
    slug = normalize_case_id(client_id)
    case_dir = REPO_CASES_DIR / slug
    fh = case_dir / "financial-health.json"
    ia = case_dir / "investment-analysis.json"
    persona = case_dir / "persona.md"
    missing = [str(p) for p in (fh, ia, persona) if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Faltan archivos del caso '{slug}': {', '.join(missing)}")
    return {"financial_health": fh, "investment_analysis": ia, "persona": persona}


def list_family_videos() -> List[Dict[str, Any]]:
    """Lista el estado de los vídeos MP4 disponibles en project/videos/ para las 4 familias."""
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    items: List[Dict[str, Any]] = []
    for full_id, short_id in SHORT_ID_MAP.items():
        mp4_path = VIDEOS_DIR / f"{short_id}.mp4"
        exists = mp4_path.is_file()
        items.append(
            {
                "client_id": full_id,
                "short_id": short_id,
                "exists": exists,
                "video_url": f"/videos/{short_id}.mp4" if exists else None,
                "size_bytes": mp4_path.stat().st_size if exists else 0,
            }
        )
    return items


def get_video_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Devuelve el estado actual de un trabajo de generación de vídeo."""
    job = _VIDEO_JOBS.get(job_id)
    return dict(job) if job else None


def get_latest_job_for_client(client_id: str) -> Optional[Dict[str, Any]]:
    """Devuelve el último trabajo activo o reciente para una familia."""
    slug = normalize_case_id(client_id)
    matches = [j for j in _VIDEO_JOBS.values() if j["client_id"] == slug]
    if not matches:
        return None
    matches.sort(key=lambda j: j["created_at"], reverse=True)
    return dict(matches[0])


async def _run_video_job(
    job_id: str,
    client_id: str,
    short_id: str,
    files: Dict[str, Path],
    output_path: Path,
    voice_id: str,
    demo_mode: bool,
    audio_mode: str,
) -> None:
    job = _VIDEO_JOBS[job_id]
    node_exe = shutil.which("node")
    if not node_exe:
        job["status"] = "failed"
        job["error"] = "No se encontró 'node' en el PATH del sistema."
        return
    if not TSX_CLI.is_file():
        job["status"] = "failed"
        job["error"] = "Faltan dependencias en project/video-generator (ejecuta npm ci)."
        return

    async with _RENDER_LOCK:
        job["status"] = "starting"
        job["progress"] = 3

        env = os.environ.copy()
        music_asset = VIDEO_GENERATOR_DIR / "assets" / "background-music.mp3"
        env.update(
            {
                "DEMO_MODE": "true" if demo_mode else "false",
                "LLM_BASE_URL": BASE_URL_V1,
                "LLM_API_KEY": TEAM_KEY or "",
                "LLM_MODEL": os.getenv("VIDEO_LLM_MODEL", "deepseek-flash"),
                "LLM_MAX_ATTEMPTS": "2",
                "AUDIO_MODE": "none" if demo_mode else audio_mode,
                "ELEVENLABS_API_KEY": ELEVENLABS_API_KEY or "",
                "ELEVENLABS_VOICE_ID": voice_id,
                "ELEVENLABS_TTS_MODEL": "eleven_multilingual_v2",
                "GENERATE_MUSIC": "true" if (not demo_mode and music_asset.is_file()) else "false",
                "MUSIC_FILE": "assets/background-music.mp3",
                "MAX_VIDEO_SECONDS": "180",
                "VIDEO_FPS": "30",
            }
        )

        cmd = [
            node_exe,
            str(TSX_CLI),
            "src/cli.ts",
            "--financial-health",
            str(files["financial_health"]),
            "--investment-analysis",
            str(files["investment_analysis"]),
            "--persona",
            str(files["persona"]),
            "--output",
            str(output_path),
            "--job-id",
            job_id,
        ]

        def _run_sync_process() -> tuple[int, List[str]]:
            proc = subprocess.Popen(
                cmd,
                cwd=str(VIDEO_GENERATOR_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert proc.stdout is not None
            for raw_line in proc.stdout:
                line = raw_line.strip()
                if line.startswith("PROGRESS:"):
                    try:
                        payload = json.loads(line[len("PROGRESS:") :])
                        if "status" in payload:
                            job["status"] = payload["status"]
                        if "progress" in payload:
                            job["progress"] = int(payload["progress"])
                        if "warnings" in payload and isinstance(payload["warnings"], list):
                            job["warnings"] = payload["warnings"]
                    except json.JSONDecodeError:
                        pass
            stderr_text = proc.stderr.read() if proc.stderr else ""
            rc = proc.wait()
            err_lines = [ln.strip() for ln in stderr_text.splitlines() if ln.strip()]
            return rc, err_lines

        try:
            rc, stderr_lines = await asyncio.to_thread(_run_sync_process)
            if rc == 0 and output_path.is_file():
                job["status"] = "completed"
                job["progress"] = 100
                job["video_url"] = f"/videos/{short_id}.mp4"
                job["size_bytes"] = output_path.stat().st_size
                job["completed_at"] = _utc_now()
            else:
                joined_err = "\n".join(stderr_lines)
                if "ERROR:" in joined_err:
                    err_msg = joined_err.split("ERROR:", 1)[1].strip()
                else:
                    err_msg = " | ".join(stderr_lines[-5:]) if stderr_lines else f"Exit code {rc}"
                job["status"] = "failed"
                job["error"] = err_msg[:500]
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = f"{type(exc).__name__}: {exc}"[:500]


async def start_video_generation(
    client_id: str,
    demo_mode: Optional[bool] = None,
    audio_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Lanza un trabajo asíncrono de generación de vídeo para `client_id`
    y guarda el MP4 resultante en project/videos/{short_id}.mp4.
    """
    slug = normalize_case_id(client_id)
    short_id = get_short_id(slug)
    files = _resolve_case_files(slug)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = VIDEOS_DIR / f"{short_id}.mp4"

    # Si no hay clave LLM configurada, usamos demo_mode automáticamente para no fallar
    effective_demo = (not bool(TEAM_KEY)) if demo_mode is None else bool(demo_mode)
    effective_audio = audio_mode or ("elevenlabs" if ELEVENLABS_API_KEY else "none")

    ctx = await get_compact_client_context(slug)
    vp = resolve_voice_profile(slug, ctx, user_text="Generate my financial story video")
    voice_id = vp.get("en_voice_id") or vp.get("voice_id") or "EXAVITQu4vr4xnSDxMaL"

    job_id = str(uuid.uuid4())
    job: Dict[str, Any] = {
        "job_id": job_id,
        "client_id": slug,
        "short_id": short_id,
        "status": "queued",
        "progress": 0,
        "demo_mode": effective_demo,
        "audio_mode": "none" if effective_demo else effective_audio,
        "video_url": f"/videos/{short_id}.mp4" if output_path.is_file() else None,
        "warnings": [],
        "error": None,
        "created_at": _utc_now(),
    }
    _VIDEO_JOBS[job_id] = job

    asyncio.create_task(
        _run_video_job(
            job_id=job_id,
            client_id=slug,
            short_id=short_id,
            files=files,
            output_path=output_path,
            voice_id=voice_id,
            demo_mode=effective_demo,
            audio_mode=effective_audio,
        )
    )
    return dict(job)
