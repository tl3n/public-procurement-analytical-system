"""ORM models for the procurement monitoring system.

Importing this package registers every model with the declarative ``Base`` so that
inter-model relationships resolve and Alembic can autogenerate the schema.
"""

from app.models.base import Base
from app.models.cpv import CpvClassification
from app.models.documents import Document
from app.models.organizations import ProcuringEntity, Supplier
from app.models.risk import RiskIndicatorValue
from app.models.sync import SyncState
from app.models.tenders import (
    Award,
    Bid,
    Complaint,
    Contract,
    Item,
    Lot,
    Tender,
)

__all__ = [
    "Award",
    "Base",
    "Bid",
    "Complaint",
    "Contract",
    "CpvClassification",
    "Document",
    "Item",
    "Lot",
    "ProcuringEntity",
    "RiskIndicatorValue",
    "Supplier",
    "SyncState",
    "Tender",
]
