"""The contract the React client already consumes.

The frontend (``project/frontend/src/features/family/types.ts``) declares::

    interface Milestone {
      id: string
      title: string
      why: string
      action: string
      section: PlanSectionId
      status: MilestoneStatus
      checkin?: string
    }

These tests keep the backend compatible with it.
"""

from __future__ import annotations

from tests.conftest import TEST_CASE_ID

PLAN_SECTION_IDS = {"summary", "retirement", "assets", "debt", "savings", "protection"}
MILESTONE_STATUSES = {
    "not_started",
    "in_progress",
    "completed",
    "on_hold",
    "cancelled",
}


def test_the_listing_has_the_shape_the_frontend_expects(client, generated_case):
    response = client.get(f"/api/cases/{TEST_CASE_ID}/milestones")
    assert response.status_code == 200
    body = response.json()

    assert isinstance(body, dict)
    assert isinstance(body["milestones"], list)
    assert body["milestones"], "the fixture must produce milestones"

    for milestone in body["milestones"]:
        assert isinstance(milestone["id"], str) and milestone["id"]
        assert isinstance(milestone["title"], str)
        assert isinstance(milestone["why"], str)
        assert isinstance(milestone["action"], str)
        assert milestone["section"] in PLAN_SECTION_IDS
        assert milestone["status"] in MILESTONE_STATUSES
        assert milestone["checkin"] is None or isinstance(milestone["checkin"], str)


def test_the_checkin_keeps_the_display_format_of_the_prototype(client, generated_case):
    body = client.get(f"/api/cases/{TEST_CASE_ID}/milestones").json()
    milestone = next(m for m in body["milestones"] if m["checkin"])
    # The prototype shows "Dec 14".
    assert milestone["checkin"].split()[0][:3].isalpha()
    assert milestone["checkin"].split()[0].istitle()
    # The precise date comes next to it.
    assert milestone["checkin_date"].count("-") == 2


def test_the_new_fields_come_after_the_legacy_ones(client, generated_case):
    body = client.get(f"/api/cases/{TEST_CASE_ID}/milestones").json()
    keys = list(body["milestones"][0].keys())
    legacy = ["id", "title", "why", "action", "section", "status", "checkin"]
    assert keys[: len(legacy)] == legacy


def test_the_new_fields_are_all_there(client, generated_case):
    body = client.get(f"/api/cases/{TEST_CASE_ID}/milestones").json()
    milestone = body["milestones"][0]
    for key in (
        "case_id",
        "category",
        "type",
        "priority",
        "tasks",
        "task_progress",
        "financial_progress",
        "due_date",
        "checkin_pending",
        "source",
        "created_at",
        "updated_at",
        "completed_at",
        "last_reviewed_at",
    ):
        assert key in milestone, key


def test_a_milestone_is_json_serialisable_without_a_custom_encoder(client, generated_case):
    import json

    body = client.get(f"/api/cases/{TEST_CASE_ID}/milestones").json()
    encoded = json.dumps(body)
    assert "timothy-melanie-weah" in encoded


def test_the_categories_endpoint_matches_the_catalogue(client):
    response = client.get("/api/categories")
    assert response.status_code == 200
    labels = {item["label"] for item in response.json()["categories"]}
    assert labels == {
        "Debt",
        "Savings",
        "Investments",
        "Retirement",
        "Insurance & Protection",
        "Education",
        "Tax Planning",
        "Housing",
        "Estate Planning",
        "Financial Planning",
        "Other",
    }


def test_the_sections_endpoint_matches_the_frontend(client):
    response = client.get("/api/sections")
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["sections"]}
    assert ids == PLAN_SECTION_IDS
