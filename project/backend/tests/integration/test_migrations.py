"""The migrations and the schema they produce."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _run_alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    env = {
        "PATH": "/usr/bin:/bin",
        "DATABASE_URL": url,
        "PYTHONPATH": str(BACKEND_DIR),
        "HOME": str(Path.home()),
    }
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture()
def migrated_database(tmp_path: Path) -> str:
    """A database created by the migrations."""
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    result = _run_alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    return url


def test_the_migrations_create_every_table(migrated_database: str):
    engine = create_engine(migrated_database)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert {
        "financial_case",
        "milestone",
        "milestone_task",
        "financial_observation",
        "milestone_checkin",
        "notification",
        "sync_state",
        "ai_generation",
    } <= tables


def test_the_migrations_match_the_models(migrated_database: str):
    from app.models import Base

    engine = create_engine(migrated_database)
    inspector = inspect(engine)
    migrated = set(inspector.get_table_names())
    declared = set(Base.metadata.tables.keys())
    engine.dispose()
    assert migrated - {"alembic_version"} == declared


def test_the_migration_can_be_rolled_back(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'rollback.db'}"
    assert _run_alembic(url, "upgrade", "head").returncode == 0
    assert _run_alembic(url, "downgrade", "base").returncode == 0
    assert _run_alembic(url, "upgrade", "head").returncode == 0


def test_there_is_no_drift_between_the_models_and_the_migrations(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'drift.db'}"
    assert _run_alembic(url, "upgrade", "head").returncode == 0
    result = _run_alembic(url, "check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_foreign_keys_are_declared(migrated_database: str):
    engine = create_engine(migrated_database)
    inspector = inspect(engine)
    foreign_keys = inspector.get_foreign_keys("milestone_task")
    engine.dispose()
    assert foreign_keys
    assert foreign_keys[0]["referred_table"] == "milestone"


def test_the_money_columns_are_numeric(migrated_database: str):
    engine = create_engine(migrated_database)
    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("financial_observation")}
    engine.dispose()
    assert columns["value"]["type"].__class__.__name__ in {"NUMERIC", "DECIMAL"}
