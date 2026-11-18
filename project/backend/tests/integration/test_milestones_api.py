"""The milestone endpoints."""

from __future__ import annotations

from tests.conftest import TEST_CASE_ID


def test_generation_stores_the_milestones(client, fake_provider, digest):
    from tests.conftest import make_payload

    fake_provider._payload = make_payload(digest)
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/generate", json={"force": True}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["milestones"]) == 2
    assert body["meta"]["count"] == 2


def test_listing_returns_the_legacy_contract(client, generated_case):
    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones")
    assert response.status_code == 200
    body = response.json()
    assert "milestones" in body
    milestone = body["milestones"][0]
    for key in ("id", "title", "why", "action", "section", "status", "checkin"):
        assert key in milestone
    assert milestone["section"] in {
        "summary",
        "retirement",
        "assets",
        "debt",
        "savings",
        "protection",
    }
    assert milestone["status"] in {
        "not_started",
        "in_progress",
        "completed",
        "on_hold",
        "cancelled",
    }


def test_listing_can_be_grouped_by_category(client, generated_case):
    response = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones?group_by=category"
    )
    assert response.status_code == 200
    grouped = response.json()["grouped_by_category"]
    assert grouped
    assert all(isinstance(items, list) for items in grouped.values())


def test_listing_can_be_filtered(client, generated_case):
    response = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones?status=not_started"
    )
    assert response.status_code == 200
    assert all(
        milestone["status"] == "not_started"
        for milestone in response.json()["milestones"]
    )


def test_generating_twice_is_a_conflict(client, generated_case):
    response = client.post(f"/api/cases/{TEST_CASE_ID}/milestones/generate", json={})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SYNC_CONFLICT"


def test_getting_a_milestone(client, generated_case):
    milestone_id = generated_case["milestones"][0]["id"]
    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}")
    assert response.status_code == 200
    assert response.json()["id"] == milestone_id


def test_getting_an_unknown_milestone(client, generated_case):
    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones/ms_does_not_exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MILESTONE_NOT_FOUND"


def test_the_client_can_change_the_status(client, generated_case):
    milestone_id = generated_case["milestones"][0]["id"]
    response = client.patch(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}/status",
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_an_invalid_transition_is_refused(client, generated_case):
    milestone_id = generated_case["milestones"][0]["id"]
    response = client.patch(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}/status",
        json={"status": "completed"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_an_unknown_status_is_refused(client, generated_case):
    milestone_id = generated_case["milestones"][0]["id"]
    response = client.patch(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}/status",
        json={"status": "needs_review"},
    )
    assert response.status_code == 422


def test_completing_a_milestone_needs_a_confirmation(client, generated_case):
    milestone_id = generated_case["milestones"][0]["id"]
    client.patch(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}/status",
        json={"status": "in_progress"},
    )
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}/complete",
        json={"confirmed": False},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_completing_a_milestone(client, generated_case):
    milestone_id = generated_case["milestones"][0]["id"]
    client.patch(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}/status",
        json={"status": "in_progress"},
    )
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}/complete",
        json={"confirmed": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None


def test_the_progress_of_a_milestone(client, generated_case):
    milestone_id = generated_case["milestones"][0]["id"]
    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones/{milestone_id}/progress")
    assert response.status_code == 200
    body = response.json()
    assert body["milestone_id"] == milestone_id
    assert body["required_tasks"] == 1
    assert body["completed_required_tasks"] == 0
    assert body["task_progress"] == 0


def test_the_progress_of_a_case(client, generated_case):
    response = client.get(f"/api/cases/{TEST_CASE_ID}/progress")
    assert response.status_code == 200
    body = response.json()
    assert body["milestones_total"] == 2
    assert body["not_started"] == 2
