"""Synchronisation with the financial plan."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps import (
    ai_service_dependency,
    case_source_dependency,
    settings_dependency,
)
from app.db.session import get_db
from app.main import create_app
from tests.conftest import CASES_DIR, TEST_CASE_ID, make_payload


class MutableCaseSource:
    """A case source whose plan can be changed between two synchronisations."""

    data_source = "local"
    last_error = None

    def __init__(self, cases_dir: Path) -> None:
        self._cases_dir = cases_dir
        self._mutations: dict[str, dict] = {}
        self.digest_calls = 0

    def _load(self, case_id: str, filename: str) -> dict:
        payload = json.loads(
            (self._cases_dir / case_id / filename).read_text(encoding="utf-8")
        )
        mutation = self._mutations.get(filename)
        if mutation:
            mutation(payload)
        return payload

    async def get_digest(self, case_id: str):
        from app.integration.mcp.normalizer import normalize_plan

        self.digest_calls += 1
        persona = (self._cases_dir / case_id / "persona.md").read_text(encoding="utf-8")
        return normalize_plan(
            case_id,
            financial_health=self._load(case_id, "financial-health.json"),
            investment_analysis=self._load(case_id, "investment-analysis.json"),
            persona=persona,
            data_source="local",
        )

    async def list_cases(self):
        return []

    async def get_case_overview(self, case_id: str):
        return {}

    async def get_part(self, case_id: str, part: str):
        return {}

    async def get_section(self, case_id: str, part: str, section: str):
        return None

    def mutate(self, filename: str, mutation) -> None:
        """Register a change to apply to a part of the plan."""
        self._mutations[filename] = mutation


def _client_with_source(client, settings, session_factory, ai_service, source):
    """Rebuild the test client with a different case source."""
    app = create_app()

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[case_source_dependency] = lambda: source
    app.dependency_overrides[ai_service_dependency] = lambda: ai_service
    return TestClient(app, raise_server_exceptions=False)


def test_the_first_sync_creates_the_milestones(
    client, settings, session_factory, fake_provider, digest
):
    fake_provider._payload = make_payload(digest)
    response = client.post(f"/api/cases/{TEST_CASE_ID}/sync", json={})
    assert response.status_code == 200, response.text
    assert len(response.json()["milestones"]) == 2


def test_a_sync_without_changes_does_not_call_the_ai(
    client, settings, session_factory, fake_provider, digest
):
    fake_provider._payload = make_payload(digest)
    client.post(f"/api/cases/{TEST_CASE_ID}/sync", json={})
    calls_after_first = len(fake_provider.calls)

    response = client.post(f"/api/cases/{TEST_CASE_ID}/sync", json={})
    assert response.status_code == 200
    assert len(fake_provider.calls) == calls_after_first


def test_the_sync_state_is_reported(client, generated_case):
    response = client.get(f"/api/cases/{TEST_CASE_ID}/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == TEST_CASE_ID
    assert body["status"] in {"idle", "success", "running", "error"}
    assert body["plan_fingerprint"]


def test_a_changed_plan_updates_the_milestones(
    settings, session_factory, fake_provider, ai_service, digest
):
    source = MutableCaseSource(CASES_DIR)
    fake_provider._payload = make_payload(digest)

    app = create_app()

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[case_source_dependency] = lambda: source
    app.dependency_overrides[ai_service_dependency] = lambda: ai_service

    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post(f"/api/cases/{TEST_CASE_ID}/sync", json={})
        assert first.status_code == 200
        assert len(first.json()["milestones"]) == 2

        # The plan changes: the score of the household moves.
        def mutation(payload: dict) -> None:
            payload["score"] = {**payload["score"], "published_score": 71}

        source.mutate("financial-health.json", mutation)

        second = client.post(f"/api/cases/{TEST_CASE_ID}/sync", json={})
        assert second.status_code == 200
        assert len(second.json()["milestones"]) == 2
        assert len(fake_provider.calls) == 2


def test_a_sync_keeps_the_progress_of_the_client(
    settings, session_factory, fake_provider, ai_service, digest
):
    source = MutableCaseSource(CASES_DIR)
    fake_provider._payload = make_payload(digest)

    app = create_app()

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[case_source_dependency] = lambda: source
    app.dependency_overrides[ai_service_dependency] = lambda: ai_service

    with TestClient(app, raise_server_exceptions=False) as client:
        client.post(f"/api/cases/{TEST_CASE_ID}/sync", json={})
        milestones = client.get(f"/api/cases/{TEST_CASE_ID}/milestones").json()["milestones"]
        educational = next(m for m in milestones if m["type"] == "educational")
        tasks = client.get(
            f"/api/cases/{TEST_CASE_ID}/milestones/{educational['id']}/tasks"
        ).json()
        required = next(task for task in tasks if task["is_required"])
        client.patch(
            f"/api/cases/{TEST_CASE_ID}/milestones/{educational['id']}/tasks/{required['id']}",
            json={"status": "completed"},
        )

        # The plan changes and the AI proposes the same milestones again.
        def mutation(payload: dict) -> None:
            payload["score"] = {**payload["score"], "published_score": 71}

        source.mutate("financial-health.json", mutation)
        client.post(f"/api/cases/{TEST_CASE_ID}/sync", json={"force": True})

        after = client.get(f"/api/cases/{TEST_CASE_ID}/milestones/{educational['id']}").json()
        assert after["status"] == "completed"
        assert after["task_progress"] == 100
        assert any(task["id"] == required["id"] for task in after["tasks"])
        kept = next(task for task in after["tasks"] if task["id"] == required["id"])
        assert kept["status"] == "completed"


def test_two_synchronisations_at_the_same_time_conflict(
    settings, session_factory, fake_provider, digest
):
    from app.repositories import notification_repository

    fake_provider._payload = make_payload(digest)
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
        # The state says a synchronisation is already running.
        session = session_factory()
        from app.services.case_service import ensure_case_row

        ensure_case_row(session, TEST_CASE_ID)
        session.commit()
        state = notification_repository.get_or_create_sync_state(session, TEST_CASE_ID)
        state.status = "running"
        session.commit()
        session.close()

        response = client.post(f"/api/cases/{TEST_CASE_ID}/sync", json={})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "SYNC_CONFLICT"
