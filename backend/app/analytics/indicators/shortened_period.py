"""Shortened submission period indicator.

Compares the actual business-day window between tender publication and the
submission deadline against the statutory minimum for the procedure type. A
window shorter than the minimum signals a possibly pre-selected winner.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.holidays import working_days_between
from app.analytics.indicators.base import (
    Indicator,
    IndicatorDescription,
    IndicatorResult,
)
from app.models import Tender

# Statutory minimum working-day windows per procurement-method type. Sourced
# from the Public Procurement Law and its 2020/2024 amendments; values used
# here are conservative defaults — operators can override per indicator
# instance if regulations change.
MIN_WORKING_DAYS_BY_TYPE: dict[str, int] = {
    "aboveThresholdUA": 15,
    "aboveThresholdUA.defense": 15,
    "aboveThresholdEU": 30,
    "belowThreshold": 4,
    "simple.defense": 4,
    "priceQuotation": 4,
    "open": 15,
    "closeFrameworkAgreementUA": 15,
    "esco": 15,
    "competitiveDialogueUA": 15,
    "competitiveDialogueEU": 30,
}


class ShortenedPeriodIndicator(Indicator):
    min_working_days_by_type = MIN_WORKING_DAYS_BY_TYPE

    def describe(self) -> IndicatorDescription:
        return IndicatorDescription(
            code="risk.shortened_period",
            name="Shortened submission period",
            value_type="boolean",
            interpretation=(
                "True when the working-day span between publication and the "
                "submission deadline is shorter than the statutory minimum "
                "for the procedure type."
            ),
        )

    async def compute(
        self, tender: Tender, session: AsyncSession
    ) -> IndicatorResult:
        code = self.describe().code
        minimum = self.min_working_days_by_type.get(tender.procurement_method_type)
        if minimum is None:
            return IndicatorResult(code)  # Unknown procedure type.
        if tender.tender_period_start is None or tender.tender_period_end is None:
            return IndicatorResult(code)  # Missing dates — cannot compute.
        actual = working_days_between(
            tender.tender_period_start.date(),
            tender.tender_period_end.date(),
        )
        return IndicatorResult(code, value_boolean=(actual < minimum))
