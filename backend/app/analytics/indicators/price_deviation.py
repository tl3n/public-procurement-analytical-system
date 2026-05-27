"""Price deviation indicator.

Numeric: signed relative deviation of a tender's expected value from the
median expected value of comparable tenders (same CPV) across the loaded
data period. Positive values flag overstatement; negative values flag
understatement that may be designed to slip under a procurement
threshold.

Boolean: True when the tender's price is a statistical outlier in the
reference distribution (Tukey's 1.5×IQR rule applied to comparable
values).

The reference window is every comparable tender published *before* this
one. A fixed 12-month lookback would yield no signal here — the deployed
Prozorro feed starts at 2026-01, so the first months would have zero
comparable history. No-look-ahead is preserved by capping at
``tender.date_published``.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.indicators.base import (
    Indicator,
    IndicatorDescription,
    IndicatorResult,
)
from app.analytics.statistics import iqr_outliers
from app.models import Item, Lot, Tender


class PriceDeviationIndicator(Indicator):
    # Below this many comparable tenders the median is statistically
    # unreliable and the indicator returns NULL.
    min_reference_size: int = 30

    def describe(self) -> IndicatorDescription:
        return IndicatorDescription(
            code="risk.price_deviation",
            name="Price deviation from CPV median",
            value_type="numeric",
            interpretation=(
                "Signed relative deviation of the tender's expected value from "
                "the median expected value of tenders with the same CPV across "
                "the loaded data period (strictly before this tender's "
                "publication date). Boolean True when the price is a "
                "statistical outlier (Tukey 1.5×IQR). NULL when fewer than "
                "30 comparable tenders exist."
            ),
        )

    @staticmethod
    def _primary_cpv(tender: Tender) -> str | None:
        for lot in tender.lots:
            for item in lot.items:
                if item.cpv_code:
                    return item.cpv_code
        return None

    async def compute(
        self, tender: Tender, session: AsyncSession
    ) -> IndicatorResult:
        code = self.describe().code
        if tender.value_amount is None or tender.date_published is None:
            return IndicatorResult(code)
        cpv = self._primary_cpv(tender)
        if cpv is None:
            return IndicatorResult(code)

        # Subquery: distinct comparable tenders (one row each, no fan-out from
        # items). Joining straight to items would multiply tenders with N
        # items by N — wrong both for the median and for the count.
        comparable_ids = (
            select(Lot.tender_id)
            .join(Item, Item.lot_id == Lot.id)
            .where(Item.cpv_code == cpv)
            .distinct()
            .subquery()
        )
        # Every comparable tender published before this one — the reference
        # set scales with whatever has been loaded so far rather than a
        # fixed 12-month window.
        tenders_in_window = (
            select(Tender.id, Tender.value_amount)
            .where(Tender.id.in_(select(comparable_ids.c.tender_id)))
            .where(Tender.id != tender.id)
            .where(Tender.value_amount.isnot(None))
            .where(Tender.date_published.isnot(None))
            .where(Tender.date_published < tender.date_published)
            .subquery()
        )
        stmt = select(
            func.percentile_cont(0.5)
            .within_group(tenders_in_window.c.value_amount.asc())
            .label("median"),
            func.count(tenders_in_window.c.id).label("n"),
        )
        row = (await session.execute(stmt)).one()
        if row.n < self.min_reference_size or row.median in (None, 0):
            return IndicatorResult(code)
        deviation = (tender.value_amount - row.median) / row.median

        # Fetch all comparable values to apply Tukey's IQR outlier test.
        # The tender itself is added to the reference set so the IQR is
        # computed on the full market picture including this procedure.
        values_rows = (
            await session.execute(select(tenders_in_window.c.value_amount))
        ).scalars().all()
        comparable_values = [float(v) for v in values_rows]
        all_values = comparable_values + [float(tender.value_amount)]
        outliers = iqr_outliers(all_values)
        is_outlier = float(tender.value_amount) in outliers

        return IndicatorResult(
            code,
            value_boolean=is_outlier,
            value_numeric=Decimal(deviation),
        )
