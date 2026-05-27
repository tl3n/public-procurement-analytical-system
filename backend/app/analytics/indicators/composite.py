"""Composite Corruption Risk Index (CRI).

A single 0..1 score per tender that summarises the five baseline indicators.
Computed as a weighted sum of normalised per-indicator scores against the
**full** weight basis (Σwᵢ = 1):

    CRI = Σ(wᵢ · sᵢ where sᵢ is defined)

Missing values do not boost the score: an indicator that returns NULL
contributes 0 to the numerator and the denominator stays fixed at 1.
This follows the conservative "absence of signal ≠ signal of low risk"
convention used by indicator-based corruption-risk frameworks in the
public-procurement literature (e.g. Fazekas et al.). The earlier
renormalising formulation inflated tenders with only one measurable
indicator to CRI = 1.0, which was too lax to be useful.

To suppress noise on brand-new tenders where almost nothing is measurable,
CRI is left undefined (NULL) when fewer than ``CRI_MIN_INPUTS`` indicators
returned a usable value.

A tender is flagged ``value_boolean=True`` once CRI ≥ ``CRI_THRESHOLD``.
This boolean is what the dashboard and tender-list filters consume; the
numeric score is exposed in the indicator report so the distribution and
mean can be inspected.

Weights reflect emphasis on hard procedural red flags (single bidding)
over softer structural signals (concentration, price deviation).
"""

from __future__ import annotations

from decimal import Decimal

from app.analytics.indicators.base import IndicatorDescription, IndicatorResult


CRI_CODE = "risk.composite_cri"
# 0.40 flags any tender where two of the heavier-weight red flags fire
# (e.g. single_bidding + non_competitive ⇒ 0.25 + 0.20 = 0.45 ≥ 0.40).
# Empirically this isolates the top quartile of measurable tenders in the
# 2026 Prozorro feed; the literature places defensible cutoffs in the
# 0.3–0.5 range, so anchor at the lower end to surface enough signal for
# subsequent qualitative review.
CRI_THRESHOLD = 0.4

# Weights must sum to exactly 1.0 — the formula uses the full basis as the
# denominator, so missing indicators reduce CRI rather than being elided.
CRI_WEIGHTS: dict[str, float] = {
    "risk.single_bidding": 0.25,
    "risk.non_competitive": 0.20,
    "risk.shortened_period": 0.15,
    "risk.buyer_concentration": 0.20,
    "risk.price_deviation": 0.20,
}

# Minimum number of indicators that must produce a usable value before the
# CRI is considered defined. Below this floor the dispatcher persists no
# composite row, matching the "tried, cannot compute" convention.
CRI_MIN_INPUTS = 2

CRI_DESCRIPTION = IndicatorDescription(
    code=CRI_CODE,
    name="Композитний індекс корупційного ризику (CRI)",
    value_type="numeric",
    interpretation=(
        "Зважена сума нормалізованих значень п’яти базових індикаторів у "
        "діапазоні 0…1 (NULL — менше двох вимірюваних індикаторів). Тендер "
        f"позначається як високоризиковий, коли CRI ≥ {CRI_THRESHOLD:.2f}."
    ),
)


def _score_for(outcome: IndicatorResult) -> float | None:
    """Normalise one indicator's outcome into a 0..1 score.

    Returns ``None`` if the indicator has no usable value, so the caller can
    exclude its weight from both numerator and denominator.
    """
    code = outcome.code

    # price_deviation returns a signed numeric ratio AND an outlier flag.
    # Use the boolean — the flag is already calibrated by the Tukey 1.5×IQR
    # rule and gives a clean 0/1 score without needing further calibration.
    if code == "risk.price_deviation":
        if outcome.value_boolean is None:
            return None
        return 1.0 if outcome.value_boolean else 0.0

    # buyer_concentration is already a share in [0, 1]; clamp defensively.
    if code == "risk.buyer_concentration":
        if outcome.value_numeric is None:
            return None
        v = float(outcome.value_numeric)
        if v < 0.0:
            return 0.0
        if v > 1.0:
            return 1.0
        return v

    # Other baseline indicators are purely boolean.
    if outcome.value_boolean is None:
        return None
    return 1.0 if outcome.value_boolean else 0.0


def compute_composite_cri(
    outcomes: list[IndicatorResult],
) -> IndicatorResult | None:
    """Combine per-indicator outcomes into a CRI ``IndicatorResult``.

    Returns ``None`` when fewer than ``CRI_MIN_INPUTS`` weighted indicators
    produced a usable score — the dispatcher then skips persisting a CRI
    row for that tender, matching the "tried, cannot compute" convention.
    """
    weighted_sum = 0.0
    contributing = 0
    for outcome in outcomes:
        weight = CRI_WEIGHTS.get(outcome.code)
        if weight is None:
            continue
        score = _score_for(outcome)
        if score is None:
            continue
        weighted_sum += weight * score
        contributing += 1

    if contributing < CRI_MIN_INPUTS:
        return None

    # Σ(CRI_WEIGHTS) is 1.0 by construction. Dividing by the full basis
    # means missing indicators behave as zero — they don't inflate a
    # partial signal to a perfect score.
    cri = weighted_sum / sum(CRI_WEIGHTS.values())
    return IndicatorResult(
        code=CRI_CODE,
        value_boolean=cri >= CRI_THRESHOLD,
        # 4 decimal places is enough for display + ranking without bloating
        # the persisted Decimal precision.
        value_numeric=Decimal(f"{cri:.4f}"),
    )
