"""Pydantic schemas for validating Prozorro API responses.

Validation is intentionally permissive (``extra="allow"`` everywhere, almost every
field optional). The Prozorro schema evolves and individual records often omit
optional sections; aborting the sync on every minor schema variance would defeat the
goal of large-scale ingestion. The normalizer is responsible for handling missing
data gracefully — this layer just gives us typed access to the fields we care about.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class _Permissive(BaseModel):
    """Base for all Prozorro DTOs — accepts unknown fields silently."""

    model_config = ConfigDict(extra="allow")


class ValueIn(_Permissive):
    amount: Decimal | None = None
    currency: str | None = None


class IdentifierIn(_Permissive):
    scheme: str | None = None
    id: str | None = None
    legalName: str | None = None


class AddressIn(_Permissive):
    streetAddress: str | None = None
    locality: str | None = None
    region: str | None = None
    postalCode: str | None = None
    countryName: str | None = None


class OrganizationIn(_Permissive):
    name: str | None = None
    identifier: IdentifierIn | None = None
    address: AddressIn | None = None


class ClassificationIn(_Permissive):
    scheme: str | None = None
    id: str | None = None
    description: str | None = None


class UnitIn(_Permissive):
    name: str | None = None
    code: str | None = None


class ItemIn(_Permissive):
    id: str
    description: str | None = None
    quantity: Decimal | None = None
    classification: ClassificationIn | None = None
    unit: UnitIn | None = None
    relatedLot: str | None = None


class LotIn(_Permissive):
    id: str
    title: str | None = None
    description: str | None = None
    status: str | None = None
    value: ValueIn | None = None


class LotValueIn(_Permissive):
    relatedLot: str
    value: ValueIn | None = None


class BidIn(_Permissive):
    id: str
    status: str | None = None
    date: datetime | None = None
    value: ValueIn | None = None
    lotValues: list[LotValueIn] | None = None
    tenderers: list[OrganizationIn] | None = None


class AwardIn(_Permissive):
    id: str
    # The API field really is named ``bid_id`` here (snake_case), unlike the rest.
    bid_id: str | None = None
    lotID: str | None = None
    status: str | None = None
    date: datetime | None = None
    value: ValueIn | None = None
    suppliers: list[OrganizationIn] | None = None


class ContractIn(_Permissive):
    id: str
    awardID: str | None = None
    status: str | None = None
    dateSigned: datetime | None = None
    dateModified: datetime | None = None
    value: ValueIn | None = None
    suppliers: list[OrganizationIn] | None = None


class ComplaintIn(_Permissive):
    id: str
    status: str | None = None
    type: str | None = None
    title: str | None = None
    description: str | None = None
    date: datetime | None = None


class DocumentIn(_Permissive):
    id: str
    title: str | None = None
    url: str | None = None
    format: str | None = None
    datePublished: datetime | None = None


class PeriodIn(_Permissive):
    startDate: datetime | None = None
    endDate: datetime | None = None


class TenderIn(_Permissive):
    id: str
    tenderID: str | None = None
    title: str | None = None
    description: str | None = None
    procurementMethod: str | None = None
    procurementMethodType: str | None = None
    status: str | None = None
    value: ValueIn | None = None
    datePublished: datetime | None = None
    dateModified: datetime | None = None
    tenderPeriod: PeriodIn | None = None
    procuringEntity: OrganizationIn | None = None
    lots: list[LotIn] = []
    items: list[ItemIn] = []
    bids: list[BidIn] = []
    awards: list[AwardIn] = []
    contracts: list[ContractIn] = []
    complaints: list[ComplaintIn] = []
    documents: list[DocumentIn] = []
