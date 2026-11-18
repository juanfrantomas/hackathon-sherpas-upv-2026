from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.deps import settings_dependency
from app.config import Settings
from app.main import create_app


def test_production_websocket_rejects_untrusted_origin():
    app = create_app()
    app.dependency_overrides[settings_dependency] = lambda: Settings(
        environment="production", cors_origins="https://demo.example.com"
    )
    with TestClient(app) as client:
        for headers in ({"origin": "https://evil.example.com"}, {}):
            try:
                with client.websocket_connect("/api/voice/ws/weah", headers=headers):
                    raise AssertionError("connection should be rejected")
            except WebSocketDisconnect as exc:
                assert exc.code == 1008


def test_production_websocket_allows_configured_origin_to_reach_case_check():
    app = create_app()
    app.dependency_overrides[settings_dependency] = lambda: Settings(
        environment="production",
        cors_origins="https://demo.example.com",
        allowed_case_ids="michael-carter",
    )
    with TestClient(app) as client:
        try:
            with client.websocket_connect(
                "/api/voice/ws/weah", headers={"origin": "https://demo.example.com"}
            ):
                raise AssertionError("case should be rejected")
        except WebSocketDisconnect as exc:
            assert exc.code == 1008
            assert exc.reason != "Origin not allowed"
