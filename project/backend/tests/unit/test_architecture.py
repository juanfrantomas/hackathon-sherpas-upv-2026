"""The architecture rules, checked on the source code.

The layers of the application point inwards: the domain knows nothing about
the infrastructure, the services know nothing about HTTP and the integration
adapters know nothing about the database.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2] / "app"


def _imported_modules(path: Path) -> set[str]:
    """Every module imported by a file, including the ones inside functions."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import
                continue
            if node.module:
                modules.add(node.module)
    return modules


def _files(folder: str) -> list[Path]:
    return sorted((APP_DIR / folder).rglob("*.py"))


def _imports_folder(folder: str, forbidden: set[str]) -> list[str]:
    problems: list[str] = []
    for path in _files(folder):
        for module in _imported_modules(path):
            root = module.split(".")[0]
            if root in forbidden or module in forbidden:
                problems.append(f"{path.relative_to(APP_DIR)} imports {module}")
    return problems


def test_the_domain_does_not_depend_on_the_infrastructure():
    problems = _imports_folder(
        "domain",
        {"sqlalchemy", "fastapi", "httpx", "httpx2", "mcp", "openai", "pydantic_settings"},
    )
    assert problems == []


def test_the_services_do_not_depend_on_http():
    problems = _imports_folder("services", {"fastapi", "starlette"})
    assert problems == []


def test_the_api_does_not_talk_to_the_database_directly():
    problems = _imports_folder("api", {"sqlalchemy"})
    assert problems == []


def test_the_integration_adapters_do_not_depend_on_the_database_or_the_api():
    problems = _imports_folder(
        "integration", {"sqlalchemy", "fastapi"}
    )
    assert problems == []


def test_the_repositories_do_not_depend_on_the_api():
    problems = _imports_folder("repositories", {"fastapi", "starlette"})
    assert problems == []


def test_only_the_integration_layer_imports_a_provider_sdk():
    offenders: list[str] = []
    for path in APP_DIR.rglob("*.py"):
        relative = path.relative_to(APP_DIR)
        if relative.parts[0] == "integration":
            continue
        for module in _imported_modules(path):
            if module.split(".")[0] in {"openai", "mcp"}:
                offenders.append(f"{relative} imports {module}")
    assert offenders == []


@pytest.mark.parametrize("folder", ["domain", "services", "api", "repositories", "integration"])
def test_every_module_has_a_docstring(folder: str):
    missing = [
        str(path.relative_to(APP_DIR))
        for path in _files(folder)
        if not ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
    ]
    assert missing == []
