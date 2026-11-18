.PHONY: help install dev test lint format typecheck migrate migrate-down revision coverage clean openapi examples docs

VENV := .venv
PY := $(VENV)/bin/python

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

install:  ## Install the dependencies
	uv venv --python 3.12 $(VENV) 2>/dev/null || uv venv $(VENV)
	uv pip install --python $(PY) -e ".[dev]"

dev:  ## Run the development server
	$(VENV)/bin/uvicorn app.main:app --reload --port 8001

test:  ## Run the test suite
	$(VENV)/bin/pytest -q

coverage:  ## Run the test suite with coverage
	$(VENV)/bin/pytest --cov=app --cov-report=term-missing

lint:  ## Check the style
	$(VENV)/bin/ruff check app tests

format:  ## Fix the style
	$(VENV)/bin/ruff check app tests --fix
	$(VENV)/bin/ruff format app tests

typecheck:  ## Check the types
	$(VENV)/bin/mypy app

migrate:  ## Apply the migrations
	$(VENV)/bin/alembic upgrade head

openapi:  ## Regenerate openapi.json from the application
	$(VENV)/bin/python scripts/export_openapi.py

examples:  ## Re-capture the real API answers under docs/examples (calls the AI once)
	$(VENV)/bin/python scripts/capture_examples.py

docs: openapi  ## Refresh the documentation artefacts
	$(VENV)/bin/pytest tests/integration/test_openapi_spec.py -q

migrate-down:  ## Roll the last migration back
	$(VENV)/bin/alembic downgrade -1

revision:  ## Create a migration: make revision m="add something"
	$(VENV)/bin/alembic revision --autogenerate -m "$(m)"

clean:  ## Remove the caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache
