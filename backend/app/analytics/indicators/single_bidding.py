"""Single-bidding indicator.

Fires when a competitive procedure that has cleared the submission stage
attracted exactly one bid. The most widely cited proxy for procurement
corruption — a competitive procedure that, in practice, was not contested.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.indicators.base import (
    Indicator,
    IndicatorDescription,
    IndicatorResult,
)
from app.models import Tender

# Competitive procurement-method types. Anything outside this set is treated as
# non-competitive (the indicator is not applicable → NULL result).
COMPETITIVE_TYPES: frozenset[str] = frozenset(
    {
        "open",
        "aboveThresholdUA",
        "aboveThresholdEU",
        "belowThreshold",
        "aboveThresholdUA.defense",
        "simple.defense",
        "esco",
        "closeFrameworkAgreementUA",
        "priceQuotation",
        "competitiveDialogueUA",
        "competitiveDialogueEU",
    }
)

# Statuses where the submission period has ended; only then can we count bids
# meaningfully. Earlier statuses → indicator returns NULL (cannot compute yet).
POST_SUBMISSION_STATUSES: frozenset[str] = frozenset(
    {"active.qualification", "active.awarded", "complete", "cancelled", "unsuccessful"}
)


class SingleBiddingIndicator(Indicator):
    competitive_types = COMPETITIVE_TYPES
    post_submission_statuses = POST_SUBMISSION_STATUSES

    def describe(self) -> IndicatorDescription:
        return IndicatorDescription(
            code="risk.single_bidding",
            name="Single bidding",
            value_type="boolean",
            interpretation=(
                "True when a competitive procedure received exactly one bid. "
                "NULL when the submission period has not ended or the "
                "procedure is non-competitive (indicator not applicable)."
            ),
        )

    async def compute(
        self, tender: Tender, session: AsyncSession
    ) -> IndicatorResult:
        code = self.describe().code
        if tender.procurement_method_type not in self.competitive_types:
            return IndicatorResult(code)  # Not applicable.
        if tender.status not in self.post_submission_statuses:
            return IndicatorResult(code)  # Too early.
        bid_count = sum(len(lot.bids) for lot in tender.lots)
        return IndicatorResult(code, value_boolean=(bid_count == 1))
