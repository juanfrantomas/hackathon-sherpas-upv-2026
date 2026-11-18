"""Background evaluation of the internal notices.

The notices must appear even when nobody has the application open, so a small
asyncio loop evaluates them on its own.  No extra infrastructure (no Celery,
no APScheduler) is needed for this.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timezone

from sqlalchemy import select

from app.logging_config import get_logger
from app.models.case import FinancialCase
from app.services import notification_service

logger = get_logger(__name__)


class NotificationScheduler:
    """Evaluates the notices of every known case on a fixed interval."""

    def __init__(self, session_factory, *, interval_seconds: int = 300) -> None:
        self._session_factory = session_factory
        self._interval = max(15, interval_seconds)
        self._task: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run())
        logger.info("Notification scheduler started (every %ss)", self._interval)

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
            self._task = None
        logger.info("Notification scheduler stopped")

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                return
            try:
                await self.run_once()
            except asyncio.CancelledError:
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("The notification scheduler failed: %s", type(exc).__name__)

    async def run_once(self) -> int:
        """Evaluate the notices of every case once."""
        created = 0
        session = self._session_factory()
        try:
            case_ids = list(
                session.scalars(select(FinancialCase.id).order_by(FinancialCase.id))
            )
            for case_id in case_ids:
                created += notification_service.evaluate(session, case_id)
            if created:
                session.commit()
                logger.info("Created %s notification(s)", created)
        finally:
            session.close()
        return created


def build_scheduler(session_factory, *, interval_seconds: int = 300) -> NotificationScheduler:
    """Build the scheduler used by the application lifespan."""
    return NotificationScheduler(session_factory, interval_seconds=interval_seconds)


__all__ = ["NotificationScheduler", "build_scheduler", "datetime", "timezone"]
