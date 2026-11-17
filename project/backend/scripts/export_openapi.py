"""Export the OpenAPI specification of the application.

The result is committed as ``openapi.json`` so the frontend (and any other
client) can read the contract without running the server.

Usage::

    python scripts/export_openapi.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import create_app  # noqa: E402

TARGET = BACKEND_DIR / "openapi.json"


def main() -> int:
    """Write the specification of the running application."""
    specification = create_app().openapi()
    TARGET.write_text(
        json.dumps(specification, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths = len(specification.get("paths", {}))
    schemas = len(specification.get("components", {}).get("schemas", {}))
    print(f"Wrote {TARGET.relative_to(BACKEND_DIR)}: {paths} paths, {schemas} schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
