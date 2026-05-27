"""Buyer concentration indicator.

Numeric: the largest share of a single supplier in the buyer's total
contracted spend across every tender the buyer has published up to and
including the one being scored. Approaches 1.0 when one supplier
dominates the buyer's contracting; small values indicate diverse
sourcing. Treated by the literature as a proxy for state-capture risk.

The reference window is the **loaded data period** (all tenders of this
buyer at or before ``tender.date_published``) rather than a fixed
12-month lookback — the Prozorro feed in this deployment starts at
2026-01, so a 365-day window would yield no signal for most tenders.
No-look-ahead is still enforced by capping at the current tender's
publication date.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.indicators.base import (
    Indicator,
    IndicatorDescription,
    IndicatorResult,
)
from app.models import Award, Contract, Lot, Tender


class BuyerConcentrationIndicator(Indicator):
    def describe(self) -> IndicatorDescription:
        return IndicatorDescription(
            code="risk.buyer_concentration",
            name="Buyer concentration",
            value_type="numeric",
            interpretation=(
                "Maximum share of a single supplier in the buyer's contracted "
                "spend across the loaded data period (up to and including "
                "this tender's publication date). 0.0–1.0; values close to "
                "1.0 indicate a captured supplier relationship."
            ),
        )

    async def compute(
        self, tender: Tender, session: AsyncSession
    ) -> IndicatorResult:
        code = self.describe().code
        if tender.date_published is None or tender.procuring_entity_id is None:
            return IndicatorResult(code)

        # Sum contract value per supplier across all tenders of this buyer
        # whose parent tender was published at or before the current one.
        # The parent tender's date_published is the no-look-ahead anchor —
        # contracts.date_signed is unreliable in the Prozorro export
        # (frequently NULL even when value_amount is populated).
        stmt = (
            select(Contract.supplier_id, func.sum(Contract.value_amount).label("total"))
            .join(Award, Award.id == Contract.award_id)
            .join(Lot, Lot.id == Award.lot_id)
            .join(Tender, Tender.id == Lot.tender_id)
            .where(Tender.procuring_entity_id == tender.procuring_entity_id)
            .where(Contract.value_amount.isnot(None))
            .where(Tender.date_published.isnot(None))
            .where(Tender.date_published <= tender.date_published)
            .group_by(Contract.supplier_id)
        )
        rows = (await session.execute(stmt)).all()
        if not rows:
            return IndicatorResult(code)

        totals = [r.total or Decimal(0) for r in rows]
        grand_total = sum(totals, Decimal(0))
        if grand_total == 0:
            return IndicatorResult(code)
        share = max(totals) / grand_total
        return IndicatorResult(code, value_numeric=Decimal(share))
