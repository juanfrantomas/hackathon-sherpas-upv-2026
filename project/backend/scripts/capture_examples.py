"""Capture real API responses as examples for the documentation.

The examples are not written by hand: the application answers them, so the
frontend agent sees exactly what it will receive.

The script generates the milestones of one case with the real AI provider,
puts the household in a realistic state (a completed task, a declared value
that disagrees with the plan, a registered review, an overdue milestone) and
then records the answers of every endpoint.

Usage::

    AI_API_KEY=... python scripts/capture_examples.py

The MCP is not needed: the offline case files are read instead.  A call to the
AI provider is made once (a few cents).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

EXAMPLES_DIR = BACKEND_DIR / "docs" / "examples"
CASE_ID = "timothy-melanie-weah"


def _prepare_environment() -> Path:
    """Point the application at a throwaway database."""
    workdir = Path(tempfile.mkdtemp(prefix="milestone-examples-"))
    os.environ["DATABASE_URL"] = f"sqlite:///{workdir / 'examples.db'}"
    os.environ["CASE_SOURCE"] = "local"
    os.environ["ALLOWED_CASE_IDS"] = CASE_ID
    os.environ["AUTO_GENERATE_ON_FIRST_ACCESS"] = "false"
    os.environ["AI_PROVIDER"] = "openai_compatible"
    return workdir


async def _capture() -> dict[str, object]:
    """Run the application and record the answers of every endpoint."""
    import httpx

    from app.db.session import get_engine, get_session_factory
    from app.main import create_app
    from app.models import Base
    from app.services.case_service import ensure_case_row

    engine = get_engine()
    Base.metadata.create_all(engine)

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    captured: dict[str, object] = {}

    async with httpx.AsyncClient(transport=transport, base_url="http://examples") as client:

        async def record(name: str, method: str, path: str, body: dict | None = None):
            response = await client.request(method, path, json=body)
            try:
                payload = response.json()
            except ValueError:
                payload = {"status_code": response.status_code}
            captured[name] = {"status_code": response.status_code, "body": payload}
            return response

        # --- a household with milestones -----------------------------------
        await record(
            "milestones-generate",
            "POST",
            f"/api/cases/{CASE_ID}/milestones/generate",
            {"force": True},
        )
        await record("milestones-list", "GET", f"/api/cases/{CASE_ID}/milestones")
        listing = captured["milestones-list"]["body"]
        milestones = listing["milestones"]

        educational = next(m for m in milestones if m["type"] == "educational")
        financial = next(m for m in milestones if m["type"] == "financial")

        # --- the household works on the milestones --------------------------
        tasks = await record(
            "tasks-list",
            "GET",
            f"/api/cases/{CASE_ID}/milestones/{educational['id']}/tasks",
        )
        first_task = tasks.json()[0]
        await record(
            "task-completed",
            "PATCH",
            f"/api/cases/{CASE_ID}/milestones/{educational['id']}"
            f"/tasks/{first_task['id']}",
            {"status": "completed"},
        )
        await record(
            "milestone-status-changed",
            "PATCH",
            f"/api/cases/{CASE_ID}/milestones/{educational['id']}/status",
            {"status": "in_progress"},
        )

        # --- a value the household declares that disagrees with the plan ----
        await record(
            "observation-created",
            "POST",
            f"/api/cases/{CASE_ID}/milestones/{financial['id']}/observations",
            {
                "metric_key": financial.get("financial_metric_key") or "liability_chase_cc",
                "metric_type": "balance",
                "value": "12000",
                "unit": "USD",
                "currency": "USD",
                "note": "Paid down with the year end bonus.",
            },
        )
        await record(
            "observations-list",
            "GET",
            f"/api/cases/{CASE_ID}/milestones/{financial['id']}/observations",
        )
        await record(
            "financial-progress",
            "GET",
            f"/api/cases/{CASE_ID}/milestones/{financial['id']}/financial-progress",
        )

        # --- a review happens -----------------------------------------------
        await record(
            "review-completed",
            "POST",
            f"/api/cases/{CASE_ID}/milestones/{educational['id']}/checkins/complete",
            {"effective_date": date.today().isoformat()},
        )
        await record(
            "checkins-list",
            "GET",
            f"/api/cases/{CASE_ID}/checkins",
        )
        await record(
            "milestone-checkins",
            "GET",
            f"/api/cases/{CASE_ID}/milestones/{educational['id']}/checkins",
        )

        # --- one milestone is overdue and one review is waiting -------------
        session = get_session_factory()()
        try:
            from sqlalchemy import select

            from app.models.milestone import Milestone
            from app.services import checkin_service

            for milestone in session.scalars(select(Milestone)).all():
                if milestone.id == financial["id"]:
                    milestone.due_date = date.today() - timedelta(days=9)
                    milestone.checkin_next_date = date.today() - timedelta(days=4)
            session.commit()
            for milestone in session.scalars(select(Milestone)).all():
                checkin_service.refresh_indicators(session, milestone)
            session.commit()
        finally:
            session.close()

        await record(
            "milestone-detail",
            "GET",
            f"/api/cases/{CASE_ID}/milestones/{financial['id']}",
        )
        await record(
            "milestones-list",
            "GET",
            f"/api/cases/{CASE_ID}/milestones",
        )
        await record(
            "notifications-list",
            "GET",
            f"/api/cases/{CASE_ID}/notifications",
        )
        await record("case-progress", "GET", f"/api/cases/{CASE_ID}/progress")
        await record("sync-state", "GET", f"/api/cases/{CASE_ID}/sync")
        await record("categories", "GET", "/api/categories")
        await record("sections", "GET", "/api/sections")
        await record("cases", "GET", "/api/cases")
        await record(
            "simulator",
            "POST",
            f"/api/cases/{CASE_ID}/simulator",
            {"active_ids": ["pay-down-revolving-card", "add-life-cover"]},
        )
        await record("mentor-insights", "GET", f"/api/cases/{CASE_ID}/mentor/insights")
        await record("couple", "GET", f"/api/cases/{CASE_ID}/couple")
        await record("story", "GET", f"/api/cases/{CASE_ID}/story")
        await record(
            "mentor-ask",
            "POST",
            "/api/voice/ask",
            {
                "case_id": CASE_ID,
                "question": "¿Cuánto me cuesta al año la tarjeta de crédito?",
                "style": "auto",
                "partner": "both",
            },
        )

        # --- the errors ------------------------------------------------------
        await record(
            "error-case-not-allowed",
            "GET",
            "/api/cases/some-other-household/milestones",
        )
        await record(
            "error-milestone-not-found",
            "GET",
            f"/api/cases/{CASE_ID}/milestones/ms_does_not_exist",
        )
        await record(
            "error-invalid-transition",
            "PATCH",
            f"/api/cases/{CASE_ID}/milestones/{educational['id']}/status",
            {"status": "not_started"},
        )
        await record(
            "error-invalid-observation",
            "POST",
            f"/api/cases/{CASE_ID}/milestones/{financial['id']}/observations",
            {"metric_key": "liability_chase_cc", "metric_type": "balance", "value": "-1", "unit": "USD"},
        )

        # The case row has to exist for the foreign keys of the examples.
        session = get_session_factory()()
        try:
            ensure_case_row(session, CASE_ID)
            session.commit()
        finally:
            session.close()

    return captured


def main() -> int:
    """Capture the examples and write them to ``docs/examples``."""
    workdir = _prepare_environment()
    try:
        captured = asyncio.run(_capture())
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in captured.items():
        target = EXAMPLES_DIR / f"{name}.json"
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Wrote {target.relative_to(BACKEND_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
