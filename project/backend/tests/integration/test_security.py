"""The security guard rails of the prototype."""

from __future__ import annotations

from tests.conftest import TEST_CASE_ID


def test_a_case_outside_the_allowlist_is_refused(client, generated_case):
    response = client.get("/api/cases/some-other-case/milestones")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CASE_NOT_ALLOWED"


def test_a_refused_case_never_reaches_the_case_source(
    settings, session_factory, case_source, ai_service
):
    from fastapi.testclient import TestClient

    from app.api.deps import (
        ai_service_dependency,
        case_source_dependency,
        settings_dependency,
    )
    from app.db.session import get_db
    from app.main import create_app

    calls: list[str] = []

    class SpyCaseSource:
        data_source = "local"
        last_error = None

        async def get_digest(self, case_id: str):  # pragma: no cover - must not run
            calls.append(case_id)
            raise AssertionError("the case source must not be called")

    app = create_app()

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[case_source_dependency] = lambda: SpyCaseSource()
    app.dependency_overrides[ai_service_dependency] = lambda: ai_service

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/cases/not-allowed/milestones")
        assert response.status_code == 403
    assert calls == []


def test_an_empty_allowlist_denies_everything(settings, session_factory):
    from fastapi.testclient import TestClient

    from app.api.deps import settings_dependency
    from app.db.session import get_db
    from app.main import create_app

    settings.allowed_case_ids = ""
    app = create_app()

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[get_db] = override_db

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones")
        assert response.status_code == 403


def test_a_malformed_case_id_is_refused(client):
    response = client.get("/api/cases/..%2Fetc%2Fpasswd/milestones")
    assert response.status_code in (400, 403, 404)


def test_the_secret_is_never_written_to_the_log(caplog):
    from app.logging_config import SecretRedactionFilter

    secret = "hk_V_htmkNNe8c6XSbonvGBx7Zci1M4awbTTqdwIVJNfBg"
    record = __import__("logging").LogRecord(
        name="test",
        level=20,
        pathname=__file__,
        lineno=1,
        msg=f"calling the MCP with {secret}",
        args=(),
        exc_info=None,
    )
    SecretRedactionFilter([secret]).filter(record)
    assert secret not in record.msg
    assert "REDACTED" in record.msg


def test_the_authorization_header_is_redacted():
    from app.logging_config import SecretRedactionFilter

    record = __import__("logging").LogRecord(
        name="test",
        level=20,
        pathname=__file__,
        lineno=1,
        msg="Authorization: Bearer abcdef123456789",
        args=(),
        exc_info=None,
    )
    SecretRedactionFilter().filter(record)
    assert "abcdef123456789" not in record.msg


def test_the_environment_endpoint_does_not_leak_the_credentials(client):
    response = client.get("/api/environment")
    assert response.status_code == 200
    body = response.json()
    assert "mcp_token" not in body
    assert "ai_api_key" not in body
    assert body["environment"] == "test"
