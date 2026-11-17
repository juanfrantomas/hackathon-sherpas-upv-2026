"""The documentation must not drift away from the application.

Three checks:

* the committed ``openapi.json`` is the specification of the running app,
* every example under ``docs/examples`` is a valid JSON file,
* every endpoint of the specification is mentioned in ``docs/api-contract.md``.

Without them the guide would quietly become wrong, which is worse than not
having one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = BACKEND_DIR / "docs"
EXAMPLES_DIR = DOCS_DIR / "examples"
CONTRACT_PATH = DOCS_DIR / "api-contract.md"
OPENAPI_PATH = BACKEND_DIR / "openapi.json"
TYPES_PATH = DOCS_DIR / "milestones.types.ts"


def test_the_committed_specification_matches_the_application():
    """``openapi.json`` is the specification of the running application."""
    assert OPENAPI_PATH.is_file(), "openapi.json is missing; run `make openapi`"

    committed = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    current = create_app().openapi()
    assert committed == current, (
        "openapi.json is out of date; run `make openapi` and commit the result"
    )


def test_every_example_is_valid_json():
    """The examples under ``docs/examples`` are readable."""
    files = sorted(EXAMPLES_DIR.glob("*.json"))
    assert files, "there are no examples"
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict), path.name
        assert "status_code" in payload, path.name
        assert "body" in payload, path.name


def test_every_endpoint_is_documented():
    """Every endpoint of the specification appears in the guide."""
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    specification = create_app().openapi()

    missing: list[str] = []
    for path, operations in specification["paths"].items():
        for method in operations:
            if method.upper() not in {"GET", "POST", "PATCH", "DELETE", "PUT"}:
                continue
            pattern = rf"{method.upper()}\s+{re.escape(path)}(?![A-Za-z0-9_/])"
            if not re.search(pattern, contract):
                missing.append(f"{method.upper()} {path}")

    assert not missing, "undocumented endpoints: " + ", ".join(missing)


def test_the_types_file_declares_the_milestone():
    """The TypeScript types cover the milestone and the legacy contract."""
    types = TYPES_PATH.read_text(encoding="utf-8")
    for fragment in (
        "export interface Milestone {",
        "export interface Task {",
        "export interface Observation {",
        "export interface Checkin {",
        "export interface Notification {",
        "export type MilestoneStatus =",
        "export type Category =",
        "export type PlanSection =",
        "LEGACY_MILESTONE_FIELDS",
    ):
        assert fragment in types, fragment


def test_the_legacy_contract_is_still_documented():
    """The guide names the seven fields the prototype already used."""
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    for field in ("id", "title", "why", "action", "section", "status", "checkin"):
        assert f'"{field}"' in contract, field


def test_the_links_of_the_guide_resolve():
    """Every link of the guide points at a file that exists."""
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    broken: list[str] = []
    for target in re.findall(r"\]\((\.[^)]+)\)", contract):
        path = (DOCS_DIR / target).resolve()
        if not path.exists():
            broken.append(target)
    assert not broken, "broken links: " + ", ".join(broken)


@pytest.mark.parametrize(
    "example",
    [
        "milestones-list",
        "milestone-detail",
        "tasks-list",
        "observations-list",
        "financial-progress",
        "checkins-list",
        "notifications-list",
        "sync-state",
        "categories",
        "error-case-not-allowed",
        "error-milestone-not-found",
        "error-invalid-transition",
    ],
)
def test_the_important_examples_exist(example: str):
    """The examples the guide links to are there."""
    assert (EXAMPLES_DIR / f"{example}.json").is_file(), example
