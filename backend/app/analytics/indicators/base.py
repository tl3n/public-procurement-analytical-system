"""Indicator framework — the foundation of the analytics module.

The risk-indicator suite is built around three primitives:

* ``Indicator`` — an abstract base class. Each concrete indicator implements
  ``compute(tender, session)`` and ``describe()``.
* ``IndicatorRegistry`` — a mutable collection of indicators that can be
  enabled or disabled at runtime without changing code, so the system can
  ship a base set of indicators while still allowing operators to toggle
  specific ones for tenant-specific analytics.
* ``compute_for_tender`` — the dispatcher. It loads a tender with all the
  child relations its indicators might need (avoiding N+1), runs every
  enabled indicator, and writes the results to ``risk_indicator_values``
  with replace semantics so re-runs are idempotent.

Indicators that cannot yet be evaluated (e.g. the submission period has not
ended) return a result with both ``value_boolean`` and ``value_numeric``
left ``None``. The row is still persisted so the caller can distinguish
"tried, cannot compute" from "never attempted".
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Award, Bid, Lot, RiskIndicatorValue, Tender

log = logging.getLogger(__name__)

IndicatorValueType = Literal["boolean", "numeric"]


@dataclass(frozen=True)
class IndicatorDescription:
    """Self-describing metadata returned by ``Indicator.describe()``."""

    code: str
    name: str
    value_type: IndicatorValueType
    interpretation: str


@dataclass
class IndicatorResult:
    """The computed value of one indicator on one tender."""

    code: str
    value_boolean: bool | None = None
    value_numeric: Decimal | None = None


class Indicator(ABC):
    """Abstract base for a single risk indicator."""

    @abstractmethod
    def describe(self) -> IndicatorDescription:
        """Return stable metadata about the indicator."""

    @abstractmethod
    async def compute(
        self, tender: Tender, session: AsyncSession
    ) -> IndicatorResult:
        """Compute the indicator value for one tender.

        The tender is loaded with eager relations (see ``_load_tender``) so the
        implementation can traverse lots / bids / awards without triggering
        additional queries. ``session`` is provided for indicators that need
        cross-tender context (e.g. buyer concentration over a time window).
        """


class IndicatorRegistry:
    """Mutable set of indicators with per-code enable/disable toggles."""

    def __init__(self) -> None:
        self._indicators: dict[str, Indicator] = {}
        self._disabled: set[str] = set()

    def register(self, indicator: Indicator) -> Indicator:
        code = indicator.describe().code
        if code in self._indicators:
            raise ValueError(f"indicator already registered: {code}")
        self._indicators[code] = indicator
        return indicator

    def enabled(self) -> list[Indicator]:
        return [
            ind
            for code, ind in self._indicators.items()
            if code not in self._disabled
        ]

    def all(self) -> list[Indicator]:
        return list(self._indicators.values())

    def disable(self, code: str) -> None:
        self._disabled.add(code)

    def enable(self, code: str) -> None:
        self._disabled.discard(code)

    def clear(self) -> None:
        self._indicators.clear()
        self._disabled.clear()


# Module-level singleton registry. The five baseline indicators (commit 10)
# register themselves here on import; tests use a private registry.
registry = IndicatorRegistry()


async def _load_tender(session: AsyncSession, tender_id: str) -> Tender | None:
    """Fetch a tender with every relation indicators might need.

    Using ``selectinload`` issues one extra SELECT per relation rather than a
    cartesian-product join — appropriate for hierarchical data where a single
    tender can fan out into hundreds of bids and documents.
    """
    stmt = (
        select(Tender)
        .options(
            selectinload(Tender.procuring_entity),
            selectinload(Tender.lots).selectinload(Lot.items),
            selectinload(Tender.lots)
            .selectinload(Lot.bids)
            .selectinload(Bid.supplier),
            selectinload(Tender.lots)
            .selectinload(Lot.awards)
            .selectinload(Award.supplier),
            selectinload(Tender.lots)
            .selectinload(Lot.awards)
            .selectinload(Award.contract),
        )
        .where(Tender.id == tender_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def compute_for_tender(
    session: AsyncSession,
    tender_id: str,
    *,
    registry: IndicatorRegistry = registry,
) -> list[RiskIndicatorValue]:
    """Run every enabled indicator on the given tender and persist results.

    Idempotent: any previous ``risk_indicator_values`` rows for this tender
    are deleted before the new ones are inserted.
    """
    # Function-local import to avoid a circular dependency: composite.py
    # imports IndicatorDescription/IndicatorResult from this module.
    from app.analytics.indicators.composite import compute_composite_cri

    tender = await _load_tender(session, tender_id)
    if tender is None:
        return []

    # Replace strategy — clear any previously computed values first. We do not
    # call ``session.expire_all()`` here: that would expire the just-loaded
    # tender, forcing the indicators' first attribute access to trigger a sync
    # lazy reload (MissingGreenlet under the async engine).
    await session.execute(
        delete(RiskIndicatorValue)
        .where(RiskIndicatorValue.tender_id == tender_id)
        .execution_options(synchronize_session=False)
    )

    persisted: list[RiskIndicatorValue] = []
    outcomes: list[IndicatorResult] = []
    now = datetime.now(tz=UTC)
    for indicator in registry.enabled():
        code = indicator.describe().code
        try:
            outcome = await indicator.compute(tender, session)
        except Exception:
            # One faulty indicator must not block the others.
            log.exception("indicator %s failed for tender %s", code, tender_id)
            continue
        outcomes.append(outcome)
        row = RiskIndicatorValue(
            tender_id=tender_id,
            indicator_code=outcome.code,
            value_boolean=outcome.value_boolean,
            value_numeric=outcome.value_numeric,
            computed_at=now,
        )
        session.add(row)
        persisted.append(row)

    # Composite CRI is derived from the in-memory outcomes — no extra DB
    # work. ``None`` means none of the weighted indicators had a usable
    # value (e.g. brand-new tender), in which case we skip persistence and
    # match the "tried, cannot compute" convention of base indicators.
    composite = compute_composite_cri(outcomes)
    if composite is not None:
        cri_row = RiskIndicatorValue(
            tender_id=tender_id,
            indicator_code=composite.code,
            value_boolean=composite.value_boolean,
            value_numeric=composite.value_numeric,
            computed_at=now,
        )
        session.add(cri_row)
        persisted.append(cri_row)

    await session.flush()
    return persisted
