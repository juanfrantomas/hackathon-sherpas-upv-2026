"""The internal notifications."""

from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import TEST_CASE_ID


def _make_pending(client, db_session, milestone_id: str) -> None:
    from app.models.milestone import Milestone
    from app.repositories import checkin_repository
    from app.services import checkin_service

    milestone = db_session.get(Milestone, milestone_id)
    past = date.today() - timedelta(days=1)
    planned = checkin_repository.get_checkin(session=db_session, milestone_id=milestone_id, scheduled_date=milestone.checkin_next_date)
    if planned is not None:
        planned.scheduled_date = past
    milestone.checkin_next_date = past
    db_session.commit()
    checkin_service.refresh_indicators(db_session, milestone)
    db_session.commit()


def test_a_pending_review_produces_a_notice(client, generated_case, db_session):
    milestone_id = generated_case["milestones"][0]["id"]
    _make_pending(client, db_session, milestone_id)

    response = client.get(f"/api/cases/{TEST_CASE_ID}/notifications")
    assert response.status_code == 200
    body = response.json()
    assert body["notifications"]
    assert body["notifications"][0]["type"] == "checkin_pending"
    assert body["notifications"][0]["milestone_id"] == milestone_id
    assert body["unread_count"] >= 1


def test_the_notices_are_not_duplicated(client, generated_case, db_session):
    milestone_id = generated_case["milestones"][0]["id"]
    _make_pending(client, db_session, milestone_id)

    client.get(f"/api/cases/{TEST_CASE_ID}/notifications")
    client.get(f"/api/cases/{TEST_CASE_ID}/notifications")
    response = client.get(f"/api/cases/{TEST_CASE_ID}/notifications")
    notices = [
        notice
        for notice in response.json()["notifications"]
        if notice["milestone_id"] == milestone_id
    ]
    assert len(notices) == 1


def test_an_overdue_milestone_produces_a_notice(client, generated_case, db_session):
    from app.models.milestone import Milestone
    from app.services import checkin_service

    milestone_id = generated_case["milestones"][0]["id"]
    milestone = db_session.get(Milestone, milestone_id)
    milestone.due_date = date.today() - timedelta(days=3)
    db_session.commit()
    checkin_service.refresh_indicators(db_session, milestone)
    db_session.commit()

    response = client.get(f"/api/cases/{TEST_CASE_ID}/notifications")
    types = {notice["type"] for notice in response.json()["notifications"]}
    assert "overdue" in types


def test_a_notice_can_be_marked_as_read(client, generated_case, db_session):
    milestone_id = generated_case["milestones"][0]["id"]
    _make_pending(client, db_session, milestone_id)

    notices = client.get(f"/api/cases/{TEST_CASE_ID}/notifications").json()["notifications"]
    notice_id = notices[0]["id"]
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/notifications/{notice_id}/read"
    )
    assert response.status_code == 200
    assert response.json()["read_at"] is not None

    unread = client.get(f"/api/cases/{TEST_CASE_ID}/notifications?unread=true").json()
    assert all(item["id"] != notice_id for item in unread["notifications"])


def test_marking_every_notice_as_read(client, generated_case, db_session):
    milestone_id = generated_case["milestones"][0]["id"]
    _make_pending(client, db_session, milestone_id)
    client.get(f"/api/cases/{TEST_CASE_ID}/notifications")

    response = client.post(f"/api/cases/{TEST_CASE_ID}/notifications/read-all")
    assert response.status_code == 200
    assert response.json()["read"] >= 1
    assert client.get(f"/api/cases/{TEST_CASE_ID}/notifications?unread=true").json()[
        "notifications"
    ] == []


def test_the_scheduler_evaluates_the_notices(
    client, generated_case, db_session, session_factory
):
    from app.notifications.scheduler import NotificationScheduler

    milestone_id = generated_case["milestones"][0]["id"]
    _make_pending(client, db_session, milestone_id)

    import asyncio

    scheduler = NotificationScheduler(session_factory, interval_seconds=60)
    asyncio.run(scheduler.run_once())
    response = client.get(f"/api/cases/{TEST_CASE_ID}/notifications")
    assert response.json()["notifications"]
