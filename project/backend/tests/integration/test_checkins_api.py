"""Check-ins: scheduling, pending reviews and the monthly recurrence."""

from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import TEST_CASE_ID


def _milestone(generated_case) -> dict:
    return generated_case["milestones"][0]


def test_a_milestone_gets_a_first_review(client, generated_case):
    milestone = _milestone(generated_case)
    response = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/checkins"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["next_review"] is not None
    assert body["pending"] is False


def test_the_reviews_of_a_case_are_listed(client, generated_case):
    response = client.get(f"/api/cases/{TEST_CASE_ID}/checkins")
    assert response.status_code == 200
    checkins = response.json()["checkins"]
    assert checkins
    assert checkins[0]["milestone_id"]


def test_registering_a_review_schedules_the_next_one(client, generated_case):
    milestone = _milestone(generated_case)
    scheduled = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/checkins"
    ).json()["next_review"]

    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/checkins/complete",
        json={"effective_date": date.today().isoformat()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["checkin"]["status"] == "completed"
    assert body["checkin"]["scheduled_date"] == scheduled
    assert body["pending"] is False

    assert body["next_review"] is not None
    assert date.fromisoformat(body["next_review"]) > date.fromisoformat(scheduled)


def test_registering_a_review_twice_is_idempotent(client, generated_case):
    milestone = _milestone(generated_case)
    url = f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/checkins/complete"
    first = client.post(url, json={"effective_date": date.today().isoformat()}).json()
    second = client.post(url, json={"effective_date": date.today().isoformat()}).json()
    assert first["checkin"]["id"] == second["checkin"]["id"]
    assert first["next_review"] == second["next_review"]


def test_a_review_cannot_be_dated_in_the_future(client, generated_case):
    milestone = _milestone(generated_case)
    future = (date.today() + timedelta(days=3)).isoformat()
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/checkins/complete",
        json={"effective_date": future},
    )
    assert response.status_code == 409


def test_a_pending_review_is_reported(client, generated_case, db_session):

    from app.models.milestone import Milestone
    from app.services import checkin_service

    milestone_id = _milestone(generated_case)["id"]
    from app.repositories import checkin_repository

    milestone = db_session.get(Milestone, milestone_id)
    past = date.today() - timedelta(days=2)
    planned = checkin_repository.get_checkin(session=db_session, milestone_id=milestone_id, scheduled_date=milestone.checkin_next_date)
    if planned is not None:
        planned.scheduled_date = past
    milestone.checkin_next_date = past
    db_session.commit()
    checkin_service.refresh_indicators(db_session, milestone)
    db_session.commit()

    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}")
    assert response.json()["checkin_pending"] is True

    pending = client.get(f"/api/cases/{TEST_CASE_ID}/checkins?pending=true")
    assert pending.status_code == 200
    assert any(item["pending"] for item in pending.json()["checkins"])


def test_a_closed_milestone_has_no_pending_review(client, generated_case, db_session):
    from app.models.milestone import Milestone

    milestone_id = _milestone(generated_case)["id"]
    milestone = db_session.get(Milestone, milestone_id)
    milestone.status = "completed"
    milestone.checkin_next_date = date.today() - timedelta(days=5)
    db_session.commit()

    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}")
    assert response.json()["checkin_pending"] is False


def test_an_overdue_milestone_is_flagged(client, generated_case, db_session):
    from app.models.milestone import Milestone
    from app.services import checkin_service

    milestone_id = _milestone(generated_case)["id"]
    milestone = db_session.get(Milestone, milestone_id)
    milestone.due_date = date.today() - timedelta(days=1)
    db_session.commit()
    checkin_service.refresh_indicators(db_session, milestone)
    db_session.commit()

    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}")
    assert response.json()["overdue"] is True
