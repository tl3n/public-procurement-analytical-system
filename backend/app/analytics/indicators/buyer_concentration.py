"""Buyer concentration indicator.

Numeric: the largest share of a single supplier in the buyer's total
contracted spend over the past twelve months. Approaches 1.0 when one
supplier dominates the buyer's contracting; small values indicate diverse
sourcing. Treated by the literature as a proxy for state-capture risk.
"""

from datetime import timedelta
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
    # 12-month window, approximated as 365 days.
    window_days: int = 365

    def describe(self) -> IndicatorDescription:
        return IndicatorDescription(
            code="risk.buyer_concentration",
            name="Buyer concentration",
            value_type="numeric",
            interpretation=(
                "Maximum share of a single supplier in the buyer's contracted "
                "spend over the past 12 months. 0.0–1.0; values close to 1.0 "
                "indicate a captured supplier relationship."
            ),
        )

    async def compute(
        self, tender: Tender, session: AsyncSession
    ) -> IndicatorResult:
        code = self.describe().code
        if tender.date_published is None or tender.procuring_entity_id is None:
            return IndicatorResult(code)
        window_start = tender.date_published - timedelta(days=self.window_days)

        # Sum contract value per supplier, scoped to this buyer in the window.
        stmt = (
            select(Contract.supplier_id, func.sum(Contract.value_amount).label("total"))
            .join(Award, Award.id == Contract.award_id)
            .join(Lot, Lot.id == Award.lot_id)
            .join(Tender, Tender.id == Lot.tender_id)
            .where(Tender.procuring_entity_id == tender.procuring_entity_id)
            .where(Contract.value_amount.isnot(None))
            .where(Contract.date_signed.isnot(None))
            .where(Contract.date_signed >= window_start)
            .where(Contract.date_signed <= tender.date_published)
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
