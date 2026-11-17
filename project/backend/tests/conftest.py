"""Shared test fixtures.

The suite never touches the network: the MCP is replaced by the offline case
files and the AI by a deterministic fake provider.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import (
    ai_service_dependency,
    case_source_dependency,
    settings_dependency,
)
from app.config import Settings
from app.db.session import get_db
from app.integration.ai.ai_service import AIService
from app.integration.ai.fake import FakeProvider
from app.integration.mcp.case_source import LocalCaseSource
from app.main import create_app
from app.models import Base

REPO_ROOT = Path(__file__).resolve().parents[3]
CASES_DIR = REPO_ROOT / "cases"
TEST_CASE_ID = "timothy-melanie-weah"
OTHER_CASE_ID = "michael-carter"


@pytest.fixture(scope="session")
def cases_dir() -> Path:
    """The offline case files."""
    return CASES_DIR


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    """Settings for the tests: local cases, fake AI, one allowed case."""
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        case_source="local",
        cases_dir=str(CASES_DIR),
        ai_provider="fake",
        ai_model="fake-model",
        allowed_case_ids=f"{TEST_CASE_ID},{OTHER_CASE_ID}",
        auto_generate_on_first_access=False,
        ai_generation_enabled=True,
        sync_min_interval_minutes=1440,
        notification_interval_seconds=3600,
        environment="test",
    )


@pytest.fixture()
def engine(settings: Settings):
    """An in-memory database shared by every session of the test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _pragma(dbapi_connection, _record):  # pragma: no cover - trivial
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(engine) -> sessionmaker[Session]:
    """A session factory bound to the test database."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session(session_factory) -> Iterator[Session]:
    """A session for direct database assertions."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def case_source(settings: Settings) -> LocalCaseSource:
    """The offline case source."""
    return LocalCaseSource(CASES_DIR, max_chars=settings.digest_max_chars)


@pytest.fixture()
def fake_provider() -> FakeProvider:
    """The deterministic AI provider."""
    return FakeProvider()


@pytest.fixture()
def ai_service(fake_provider: FakeProvider) -> AIService:
    """The AI service backed by the fake provider."""
    return AIService(fake_provider, model="fake-model")


@pytest.fixture()
def client(
    settings: Settings,
    session_factory,
    case_source: LocalCaseSource,
    ai_service: AIService,
) -> Iterator[TestClient]:
    """A test client with every dependency replaced."""
    app = create_app()

    def override_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[settings_dependency] = lambda: settings
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[case_source_dependency] = lambda: case_source
    app.dependency_overrides[ai_service_dependency] = lambda: ai_service

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def make_payload(
    digest: Any,
    *,
    milestones: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a valid generation payload for a digest."""
    if milestones is not None:
        return {"milestones": milestones}

    concern = digest.concerns[0] if digest.concerns else None
    metric = digest.metrics[0] if digest.metrics else None

    proposals: list[dict[str, Any]] = []
    if concern is not None:
        proposals.append(
            {
                "title": f"Understand {concern.title.lower()}",
                "why": "The plan flags this as a gap that lowers the financial health score.",
                "action": "Read the relevant section of your plan and talk it over.",
                "type": "educational",
                "category": "Debt",
                "priority": "high",
                "section": "debt",
                "anchor_key": f"concern:{concern.code}",
                "source_refs": [
                    {
                        "part": "persona",
                        "section": "objective_concerns",
                        "json_path": "persona",
                        "quote": concern.title,
                    }
                ],
                "tasks": [
                    {
                        "title": "Read the debt section of the plan",
                        "description": "Fifteen minutes with the numbers in front of you.",
                        "is_required": True,
                        "order": 0,
                    },
                    {
                        "title": "Write down what you understood",
                        "description": None,
                        "is_required": False,
                        "order": 1,
                    },
                ],
                "checkin_offset_days": 7,
                "due_offset_days": None,
                "financial_target": None,
            }
        )
    if metric is not None:
        proposals.append(
            {
                "title": f"Work on {metric.label.lower()}",
                "why": "The plan states this figure, so it can be tracked.",
                "action": "Decide what to do about it and record the decision.",
                "type": "financial",
                "category": "Savings",
                "priority": "medium",
                "section": "savings",
                "anchor_key": f"metric:{metric.metric_key}",
                "source_refs": [
                    {
                        "part": metric.source_ref.part,
                        "section": metric.source_ref.section,
                        "json_path": metric.source_ref.json_path,
                        "quote": metric.label,
                    }
                ],
                "tasks": [
                    {
                        "title": "Decide the target for this figure",
                        "description": None,
                        "is_required": True,
                        "order": 0,
                    }
                ],
                "checkin_offset_days": 14,
                "due_offset_days": 60,
                "financial_target": {
                    "metric_key": metric.metric_key,
                    "metric_type": metric.metric_type,
                    "direction": "decrease",
                    "start_value": float(metric.value),
                    "target_value": float(metric.value) / 2,
                    "unit": metric.unit,
                    "currency": metric.currency,
                    "source_ref": {
                        "part": metric.source_ref.part,
                        "section": metric.source_ref.section,
                        "json_path": metric.source_ref.json_path,
                        "quote": metric.label,
                    },
                },
            }
        )
    return {"milestones": proposals}


def payload_json(digest: Any, **kwargs: Any) -> str:
    """The payload as the fake provider would answer it."""
    return json.dumps(make_payload(digest, **kwargs))


@pytest.fixture()
def digest(case_source: LocalCaseSource):
    """The digest of the test case."""
    import asyncio

    return asyncio.run(case_source.get_digest(TEST_CASE_ID))


@pytest.fixture()
def generated_case(client, fake_provider, digest):
    """A case that already has its milestones."""
    fake_provider._payload = make_payload(digest)
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/generate", json={"force": True}
    )
    assert response.status_code == 200, response.text
    return response.json()
