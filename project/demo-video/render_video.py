"""Script 100% independiente en Python para generar el video MP4 final.

Compone cada escena a 1920x1080 con Pillow (captura + barra de título y subtítulo)
y renderiza con el ffmpeg.exe incluido en Remotion sin usar filtros no soportados.
"""

import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
SHOTS_DIR = OUTPUT_DIR / "shots"
AUDIO_DIR = OUTPUT_DIR / "audio"
SLIDES_DIR = OUTPUT_DIR / "slides"
CLIPS_DIR = OUTPUT_DIR / "clips"
FINAL_VIDEO = OUTPUT_DIR / "demo-features-2min.mp4"
SCENES_FILE = BASE_DIR / "scenes.json"

SLIDES_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

REMOTION_BIN = (
    BASE_DIR.parent
    / "video-generator"
    / "node_modules"
    / "@remotion"
    / "compositor-win32-x64-msvc"
    / "ffmpeg.exe"
)
FFMPEG = str(REMOTION_BIN) if REMOTION_BIN.exists() else "ffmpeg"
FFPROBE = (
    str(REMOTION_BIN.parent / "ffprobe.exe")
    if (REMOTION_BIN.parent / "ffprobe.exe").exists()
    else "ffprobe"
)

WIDTH = 1920
HEIGHT = 1080
BAR_HEIGHT = 170


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
        if bold
        else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]
    )
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def get_duration(audio_file: Path) -> float:
    res = subprocess.run(
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_file),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    val = res.stdout.strip()
    if val:
        try:
            return float(val)
        except ValueError:
            pass

    res2 = subprocess.run(
        [FFMPEG, "-i", str(audio_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res2.stderr)
    if m:
        hours, mins, secs = m.groups()
        return int(hours) * 3600 + int(mins) * 60 + float(secs)

    size_bytes = audio_file.stat().st_size
    return max(3.0, (size_bytes * 8) / 48000)


def compose_slide(
    img_path: Path,
    title: str,
    subtitle: str,
    out_path: Path,
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    sub_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (15, 23, 42))  # #0f172a

    if img_path.exists():
        shot = Image.open(img_path).convert("RGB")
        max_w = WIDTH - 80
        max_h = HEIGHT - BAR_HEIGHT - 40
        shot.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        x = (WIDTH - shot.width) // 2
        y = (HEIGHT - BAR_HEIGHT - shot.height) // 2
        canvas.paste(shot, (x, y))

    draw = ImageDraw.Draw(canvas)
    bar_top = HEIGHT - BAR_HEIGHT
    draw.rectangle([(0, bar_top), (WIDTH, HEIGHT)], fill=(11, 18, 32))
    draw.rectangle([(0, bar_top), (WIDTH, bar_top + 4)], fill=(56, 189, 248))

    draw.text((72, bar_top + 32), title, font=title_font, fill=(255, 255, 255))
    draw.text((72, bar_top + 96), subtitle, font=sub_font, fill=(203, 213, 225))

    canvas.save(out_path, "PNG")


def main() -> None:
    print(f"Usando FFmpeg desde: {FFMPEG}")
    data = json.loads(SCENES_FILE.read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])

    title_font = load_font(40, bold=True)
    sub_font = load_font(26, bold=False)

    clip_paths = []
    total_seconds = 0.0

    for i, scene in enumerate(scenes):
        scene_id = scene["id"]
        audio_path = AUDIO_DIR / f"{scene_id}.mp3"
        img_path = SHOTS_DIR / scene.get("image", "")
        slide_path = SLIDES_DIR / f"{scene_id}.png"
        clip_out = CLIPS_DIR / f"{scene_id}.mp4"
        clip_paths.append(clip_out)

        dur = round(get_duration(audio_path) + 0.6, 2)
        total_seconds += dur
        print(f"[{i+1}/{len(scenes)}] Renderizando {scene_id} ({dur:.1f}s)...")

        compose_slide(
            img_path=img_path,
            title=scene["title"],
            subtitle=scene["subtitle"],
            out_path=slide_path,
            title_font=title_font,
            sub_font=sub_font,
        )

        cmd = [
            FFMPEG,
            "-y",
            "-loop",
            "1",
            "-framerate",
            "30",
            "-i",
            str(slide_path),
            "-i",
            str(audio_path),
            "-t",
            str(dur),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(clip_out),
        ]

        run_res = subprocess.run(cmd, capture_output=True, text=True)
        if run_res.returncode != 0:
            print(f"Error en escena {scene_id} (code {run_res.returncode}):")
            print(run_res.stderr[-600:])
            return

    concat_txt = OUTPUT_DIR / "concat.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{p.as_posix()}'\n")

    print("\nConcatenando todos los clips en el video final...")
    concat_cmd = [
        FFMPEG,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_txt),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(FINAL_VIDEO),
    ]
    subprocess.run(concat_cmd, check=True)
    mins = int(total_seconds // 60)
    secs = int(round(total_seconds % 60))
    print(f"\n¡LISTO! Video disponible en:\n{FINAL_VIDEO}")
    print(f"Duración total: {mins}:{secs:02d} ({total_seconds:.1f}s)")


if __name__ == "__main__":
    main()
