"""The task endpoints and the completion rules."""

from __future__ import annotations

from tests.conftest import TEST_CASE_ID


def _educational_milestone(generated_case) -> dict:
    for milestone in generated_case["milestones"]:
        if milestone["type"] == "educational":
            return milestone
    raise AssertionError("the fixture must contain an educational milestone")


def _financial_milestone(generated_case) -> dict:
    for milestone in generated_case["milestones"]:
        if milestone["type"] == "financial":
            return milestone
    raise AssertionError("the fixture must contain a financial milestone")


def test_listing_the_tasks(client, generated_case):
    milestone = _educational_milestone(generated_case)
    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    assert tasks[0]["order"] == 0
    assert tasks[0]["status"] == "pending"


def test_completing_a_task_updates_the_progress(client, generated_case):
    milestone = _educational_milestone(generated_case)
    tasks = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks"
    ).json()
    required = next(task for task in tasks if task["is_required"])

    response = client.patch(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks/{required['id']}",
        json={"status": "completed"},
    )
    assert response.status_code == 200
    assert response.json()["task_progress"] == 100


def test_uncompleting_a_task_is_symmetric(client, generated_case):
    milestone = _educational_milestone(generated_case)
    tasks = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks"
    ).json()
    required = next(task for task in tasks if task["is_required"])
    url = f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks/{required['id']}"

    client.patch(url, json={"status": "completed"})
    response = client.patch(url, json={"status": "pending"})
    assert response.status_code == 200
    assert response.json()["task_progress"] == 0


def test_completing_the_same_task_twice_is_idempotent(client, generated_case):
    milestone = _educational_milestone(generated_case)
    tasks = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks"
    ).json()
    required = next(task for task in tasks if task["is_required"])
    url = f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks/{required['id']}"

    client.patch(url, json={"status": "completed"})
    response = client.patch(url, json={"status": "completed"})
    assert response.status_code == 200
    assert response.json()["task_progress"] == 100


def test_an_educational_milestone_closes_when_its_tasks_are_done(client, generated_case):
    milestone = _educational_milestone(generated_case)
    tasks = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks"
    ).json()
    for task in tasks:
        if task["is_required"]:
            client.patch(
                f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks/{task['id']}",
                json={"status": "completed"},
            )
    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}")
    assert response.json()["status"] == "completed"
    assert response.json()["completed_at"] is not None


def test_a_financial_milestone_does_not_close_on_its_own(client, generated_case):
    milestone = _financial_milestone(generated_case)
    tasks = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks"
    ).json()
    for task in tasks:
        client.patch(
            f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks/{task['id']}",
            json={"status": "completed"},
        )
    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}")
    assert response.json()["status"] == "not_started"


def test_a_financial_milestone_needs_an_explicit_confirmation(client, generated_case):
    milestone = _financial_milestone(generated_case)
    client.patch(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/status",
        json={"status": "in_progress"},
    )
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/complete",
        json={"confirmed": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_the_client_can_add_a_task(client, generated_case):
    milestone = _educational_milestone(generated_case)
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks",
        json={"title": "Call the bank on Monday", "is_required": False},
    )
    assert response.status_code == 201
    assert response.json()["origin"] == "client"


def test_the_client_can_delete_a_task(client, generated_case):
    milestone = _educational_milestone(generated_case)
    created = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks",
        json={"title": "Call the bank on Monday"},
    ).json()
    response = client.delete(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks/{created['id']}"
    )
    assert response.status_code == 204


def test_an_unknown_task_is_a_404(client, generated_case):
    milestone = _educational_milestone(generated_case)
    response = client.patch(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/tasks/task_nope",
        json={"status": "completed"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"
