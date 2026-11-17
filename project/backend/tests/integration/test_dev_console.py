"""The development console."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

CONSOLE = Path(__file__).resolve().parents[2] / "app" / "static" / "dev-console.html"


def test_the_console_exists():
    assert CONSOLE.is_file()


def test_the_console_does_not_speak_of_the_gamified_path():
    html = CONSOLE.read_text(encoding="utf-8")
    assert "/api/path/" not in html
    assert "renderPathAndGoals" not in html
    assert "currentPathData" not in html
    assert ":8000" not in html


def test_the_console_uses_the_new_paths():
    html = CONSOLE.read_text(encoding="utf-8")
    assert "/api/voice/ws/" in html
    assert "/api/cases/${cid}/simulator" in html
    assert "/api/cases/${cid}/couple" in html
    assert "/api/cases/${cid}/mentor/insights" in html
    assert "/api/cases/${cid}/story" in html
    assert "/api/cases" in html


def test_the_console_is_served_while_developing():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/dev/console")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Laboratorio de Decisiones" in response.text


def test_the_console_is_not_served_in_production(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "production")
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/dev/console").status_code == 404
