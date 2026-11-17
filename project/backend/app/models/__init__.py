"""SQLAlchemy ORM models.

Importing this package registers every model on ``Base.metadata`` which is
what Alembic's autogenerate and the test fixtures rely on.
"""

from app.models.base import Base
from app.models.case import FinancialCase
from app.models.checkin import MilestoneCheckin
from app.models.family_high_five import FamilyHighFive
from app.models.generation import AIGeneration
from app.models.milestone import Milestone
from app.models.notification import Notification
from app.models.observation import FinancialObservation
from app.models.sync_state import SyncState
from app.models.task import MilestoneTask

__all__ = [
    "AIGeneration",
    "Base",
    "FamilyHighFive",
    "FinancialCase",
    "FinancialObservation",
    "Milestone",
    "MilestoneCheckin",
    "MilestoneTask",
    "Notification",
    "SyncState",
]
