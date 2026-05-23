"""Indicator registry — concrete indicators self-register on import."""

from app.analytics.indicators.base import registry
from app.analytics.indicators.buyer_concentration import BuyerConcentrationIndicator
from app.analytics.indicators.non_competitive import NonCompetitiveIndicator
from app.analytics.indicators.price_deviation import PriceDeviationIndicator
from app.analytics.indicators.shortened_period import ShortenedPeriodIndicator
from app.analytics.indicators.single_bidding import SingleBiddingIndicator

# Order is purely cosmetic — it controls only the order of dispatcher output.
registry.register(SingleBiddingIndicator())
registry.register(NonCompetitiveIndicator())
registry.register(ShortenedPeriodIndicator())
registry.register(BuyerConcentrationIndicator())
registry.register(PriceDeviationIndicator())

__all__ = [
    "BuyerConcentrationIndicator",
    "NonCompetitiveIndicator",
    "PriceDeviationIndicator",
    "ShortenedPeriodIndicator",
    "SingleBiddingIndicator",
    "registry",
]
