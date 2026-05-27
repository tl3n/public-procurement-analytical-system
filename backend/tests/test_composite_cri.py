"""Unit tests for the composite Corruption Risk Index (CRI)."""

from decimal import Decimal

import pytest

from app.analytics.indicators.base import IndicatorResult
from app.analytics.indicators.composite import (
    CRI_CODE,
    CRI_MIN_INPUTS,
    CRI_THRESHOLD,
    CRI_WEIGHTS,
    compute_composite_cri,
)


def _outcome(code: str, *, boolean=None, numeric=None) -> IndicatorResult:
    return IndicatorResult(
        code=code,
        value_boolean=boolean,
        value_numeric=Decimal(str(numeric)) if numeric is not None else None,
    )


def test_no_inputs_yields_none():
    assert compute_composite_cri([]) is None


def test_only_null_inputs_yields_none():
    outcomes = [
        _outcome("risk.single_bidding", boolean=None),
        _outcome("risk.non_competitive", boolean=None),
    ]
    assert compute_composite_cri(outcomes) is None


def test_unknown_indicator_codes_are_ignored():
    outcomes = [_outcome("risk.unknown_code", boolean=True)]
    assert compute_composite_cri(outcomes) is None


def test_below_min_inputs_yields_none():
    # Only one weighted indicator returned a usable value — below the floor.
    assert CRI_MIN_INPUTS >= 2  # guards against accidental relaxation
    outcomes = [_outcome("risk.single_bidding", boolean=True)]
    assert compute_composite_cri(outcomes) is None


def test_all_true_yields_max_score_and_flag():
    outcomes = [
        _outcome("risk.single_bidding", boolean=True),
        _outcome("risk.non_competitive", boolean=True),
        _outcome("risk.shortened_period", boolean=True),
        _outcome("risk.buyer_concentration", numeric=1.0),
        # price_deviation uses the boolean outlier flag for scoring.
        _outcome("risk.price_deviation", boolean=True, numeric=2.0),
    ]
    result = compute_composite_cri(outcomes)
    assert result is not None
    assert result.code == CRI_CODE
    assert result.value_boolean is True
    assert float(result.value_numeric) == pytest.approx(1.0)


def test_all_false_yields_zero_and_unflagged():
    outcomes = [
        _outcome("risk.single_bidding", boolean=False),
        _outcome("risk.non_competitive", boolean=False),
        _outcome("risk.shortened_period", boolean=False),
        _outcome("risk.buyer_concentration", numeric=0.0),
        _outcome("risk.price_deviation", boolean=False, numeric=0.1),
    ]
    result = compute_composite_cri(outcomes)
    assert result is not None
    assert result.value_boolean is False
    assert float(result.value_numeric) == pytest.approx(0.0)


def test_weighted_partial_signal():
    # single_bidding (w=0.25) fires True, others measurable but False/zero.
    # CRI = 0.25 against the full 1.0 basis → below threshold.
    outcomes = [
        _outcome("risk.single_bidding", boolean=True),
        _outcome("risk.non_competitive", boolean=False),
        _outcome("risk.shortened_period", boolean=False),
        _outcome("risk.buyer_concentration", numeric=0.0),
        _outcome("risk.price_deviation", boolean=False, numeric=0.0),
    ]
    result = compute_composite_cri(outcomes)
    assert result is not None
    expected = CRI_WEIGHTS["risk.single_bidding"]
    assert float(result.value_numeric) == pytest.approx(expected, abs=1e-4)
    assert result.value_boolean is False


def test_null_indicators_count_as_zero_not_renormalised():
    # Only two indicators usable, both True. CRI = 0.25 + 0.20 = 0.45 — that
    # crosses the 0.40 threshold, demonstrating that NULL indicators must
    # not be elided (under the old renormalising formula this would have
    # been 1.0, also flagged, but indistinguishable from a fully-True case).
    outcomes = [
        _outcome("risk.single_bidding", boolean=True),
        _outcome("risk.non_competitive", boolean=True),
        _outcome("risk.shortened_period", boolean=None),
        _outcome("risk.buyer_concentration", numeric=None),
        _outcome("risk.price_deviation", boolean=None, numeric=None),
    ]
    result = compute_composite_cri(outcomes)
    assert result is not None
    expected = (
        CRI_WEIGHTS["risk.single_bidding"] + CRI_WEIGHTS["risk.non_competitive"]
    )
    assert float(result.value_numeric) == pytest.approx(expected, abs=1e-4)
    assert result.value_boolean is True


def test_buyer_concentration_numeric_is_used_directly():
    outcomes = [
        _outcome("risk.buyer_concentration", numeric=0.5),
        _outcome("risk.non_competitive", boolean=False),
    ]
    result = compute_composite_cri(outcomes)
    assert result is not None
    # buyer_concentration (w=0.20) × 0.5 = 0.10 plus non_competitive contributing 0
    expected = CRI_WEIGHTS["risk.buyer_concentration"] * 0.5
    assert float(result.value_numeric) == pytest.approx(expected, abs=1e-4)


def test_buyer_concentration_clamped_to_unit_interval():
    outcomes = [
        _outcome("risk.buyer_concentration", numeric=1.7),
        _outcome("risk.non_competitive", boolean=False),
    ]
    result = compute_composite_cri(outcomes)
    assert result is not None
    expected = CRI_WEIGHTS["risk.buyer_concentration"] * 1.0
    assert float(result.value_numeric) == pytest.approx(expected, abs=1e-4)


def test_three_high_risk_indicators_cross_threshold():
    # Three of the heavier weights fire — sum 0.25 + 0.20 + 0.20 = 0.65 ≥ 0.5.
    outcomes = [
        _outcome("risk.single_bidding", boolean=True),
        _outcome("risk.non_competitive", boolean=True),
        _outcome("risk.buyer_concentration", numeric=1.0),
        _outcome("risk.shortened_period", boolean=False),
        _outcome("risk.price_deviation", boolean=False, numeric=0.0),
    ]
    result = compute_composite_cri(outcomes)
    assert result is not None
    assert float(result.value_numeric) >= CRI_THRESHOLD
    assert result.value_boolean is True
