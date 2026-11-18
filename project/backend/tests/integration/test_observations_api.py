"""Financial observations and the financial progress."""

from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import TEST_CASE_ID


def _financial_milestone(generated_case) -> dict:
    for milestone in generated_case["milestones"]:
        if milestone["type"] == "financial":
            return milestone
    raise AssertionError("the fixture must contain a financial milestone")


def _metric(generated_case) -> str:
    return generated_case["milestones"][-1].get("id") and ""


def test_an_observation_can_be_recorded(client, generated_case):
    milestone = _financial_milestone(generated_case)
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/observations",
        json={
            "metric_key": "liability_chase_cc",
            "metric_type": "balance",
            "value": "9000",
            "unit": "USD",
            "currency": "USD",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source"] == "client"
    assert float(body["value"]) == 9000.0


def test_a_negative_observation_is_refused(client, generated_case):
    milestone = _financial_milestone(generated_case)
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/observations",
        json={
            "metric_key": "liability_chase_cc",
            "metric_type": "balance",
            "value": "-1",
            "unit": "USD",
        },
    )
    assert response.status_code == 422


def test_a_future_observation_is_refused(client, generated_case):
    milestone = _financial_milestone(generated_case)
    future = (date.today() + timedelta(days=5)).isoformat()
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/observations",
        json={
            "metric_key": "liability_chase_cc",
            "metric_type": "balance",
            "value": "9000",
            "unit": "USD",
            "observed_at": future,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FINANCIAL_OBSERVATION"


def test_an_observation_needs_a_unit(client, generated_case):
    milestone = _financial_milestone(generated_case)
    response = client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/observations",
        json={"metric_key": "x", "metric_type": "balance", "value": "1", "unit": ""},
    )
    assert response.status_code == 422


def test_the_client_value_does_not_overwrite_the_plan_value(client, generated_case):
    milestone = _financial_milestone(generated_case)
    client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/observations",
        json={
            "metric_key": "liability_chase_cc",
            "metric_type": "balance",
            "value": "9000",
            "unit": "USD",
        },
    )
    response = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/observations"
    )
    assert response.status_code == 200
    sources = {observation["source"] for observation in response.json()["observations"]}
    assert sources == {"mcp", "client"}


def test_a_conflict_keeps_the_financial_progress_empty(client, generated_case):
    milestone = _financial_milestone(generated_case)
    client.post(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/observations",
        json={
            "metric_key": "liability_chase_cc",
            "metric_type": "balance",
            "value": "1",
            "unit": "USD",
        },
    )
    response = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/financial-progress"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["progress"] is None
    assert body["state"] == "conflicting"
    assert body["conflict"] is not None


def test_the_progress_is_computed_when_the_sources_agree(client, generated_case):
    milestone = _financial_milestone(generated_case)
    metric = milestone.get("financial_metric_key")
    progress = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{milestone['id']}/financial-progress"
    ).json()
    assert progress["state"] in {"on_track", "achieved", "not_quantifiable"}
    assert metric is None or progress["metric_key"] == metric


def test_a_milestone_without_a_metric_has_no_financial_progress(client, generated_case):
    educational = next(
        milestone
        for milestone in generated_case["milestones"]
        if milestone["type"] == "educational"
    )
    response = client.get(
        f"/api/cases/{TEST_CASE_ID}/milestones/{educational['id']}/financial-progress"
    )
    assert response.status_code == 200
    assert response.json()["progress"] is None
    assert response.json()["state"] == "not_quantifiable"
