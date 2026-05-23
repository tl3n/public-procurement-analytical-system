"""Non-competitive procedure indicator.

Flags procedures with restricted access by design — negotiation, the shortened
negotiation, and post-hoc contract reports. Legitimate in some cases, but a
buyer with an unusual share of such procedures warrants attention.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.indicators.base import (
    Indicator,
    IndicatorDescription,
    IndicatorResult,
)
from app.models import Tender

NON_COMPETITIVE_TYPES: frozenset[str] = frozenset(
    {"negotiation", "negotiation.quick", "reporting"}
)


class NonCompetitiveIndicator(Indicator):
    non_competitive_types = NON_COMPETITIVE_TYPES

    def describe(self) -> IndicatorDescription:
        return IndicatorDescription(
            code="risk.non_competitive",
            name="Non-competitive procedure",
            value_type="boolean",
            interpretation=(
                "True for procurement-method types that intrinsically restrict "
                "competition (negotiation, negotiation.quick, reporting)."
            ),
        )

    async def compute(
        self, tender: Tender, session: AsyncSession
    ) -> IndicatorResult:
        code = self.describe().code
        if tender.procurement_method_type is None:
            return IndicatorResult(code)
        return IndicatorResult(
            code,
            value_boolean=(
                tender.procurement_method_type in self.non_competitive_types
            ),
        )
