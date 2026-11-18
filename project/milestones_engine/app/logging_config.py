"""Logging setup with secret redaction.

The backend holds an MCP token and a team AI key.  Neither may ever reach a
log file, a traceback or an HTTP response.  The filter below masks anything
that looks like a credential, plus the literal values of the secrets known to
the process.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

_REDACTED = "***REDACTED***"

_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?[^\s,;'\"]+"),
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)(mcp_token|team_key|api_key|x-api-key)\s*[:=]\s*[^\s,;'\"]+"),
    re.compile(r"\bhk_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b"),
)


class SecretRedactionFilter(logging.Filter):
    """Masks credentials found in log records."""

    def __init__(self, extra_secrets: list[str] | None = None) -> None:
        super().__init__()
        self._extra_secrets = [s for s in (extra_secrets or []) if s]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact(str(a)) for a in record.args)
        return True

    def _redact(self, text: str) -> str:
        for secret in self._extra_secrets:
            if secret and secret in text:
                text = text.replace(secret, _REDACTED)
        for pattern in _PATTERNS:
            text = pattern.sub(lambda m: _REDACTED, text)
        return text


def setup_logging(level: str = "INFO", secrets: list[str] | None = None) -> None:
    """Configure the root logger with the redaction filter."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    )
    handler.addFilter(SecretRedactionFilter(secrets))

    root.addHandler(handler)
    logging.getLogger("uvicorn.access").addFilter(SecretRedactionFilter(secrets))
    # The HTTP client logs one line per request; it is noise here and the
    # installed version formats the status code wrongly.
    for noisy in ("httpx", "httpx2", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Module level logger."""
    return logging.getLogger(name)


def redact(value: Any) -> str:
    """Redact an arbitrary value using the same rules as the log filter."""
    return SecretRedactionFilter()._redact(str(value))
