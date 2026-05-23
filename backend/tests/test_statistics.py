"""Tests for pure-Python statistics functions.

Inputs are deterministic, with hand-computed expected outputs so the suite
catches behaviour regressions rather than just shape regressions.
"""

import math

import numpy as np
import pytest

from app.analytics.statistics import (
    decompose_time_series,
    descriptive_stats,
    gini,
    hhi,
    iqr_outliers,
    mad_outliers,
    pearson_correlation,
    spearman_correlation,
)


# --- descriptive_stats ------------------------------------------------------


def test_descriptive_stats_known_values():
    stats = descriptive_stats([1, 2, 3, 4, 5])
    assert stats["n"] == 5
    assert stats["mean"] == pytest.approx(3.0)
    assert stats["median"] == pytest.approx(3.0)
    assert stats["std"] == pytest.approx(math.sqrt(2.5))  # sample std
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0
    assert stats["q1"] == pytest.approx(2.0)
    assert stats["q3"] == pytest.approx(4.0)


def test_descriptive_stats_empty_returns_nones():
    stats = descriptive_stats([])
    assert stats == {
        "n": 0,
        "mean": None,
        "median": None,
        "std": None,
        "min": None,
        "max": None,
        "q1": None,
        "q3": None,
    }


# --- IQR outliers -----------------------------------------------------------


def test_iqr_isolates_a_high_outlier():
    # Q1=3.25, Q3=7.75, IQR=4.5 → fences ≈ −3.5 and 14.5. Only 100 is outside.
    outliers = iqr_outliers([1, 2, 3, 4, 5, 6, 7, 8, 9, 100])
    assert outliers == [100.0]


def test_iqr_returns_empty_when_no_outliers():
    assert iqr_outliers([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == []


def test_iqr_short_input_is_no_op():
    assert iqr_outliers([1, 2, 3]) == []


# --- MAD outliers -----------------------------------------------------------


def test_mad_isolates_extreme_value():
    # median=5, MAD=2 → modified z = 0.6745*(x-5)/2. 100 → ~32, far above 3.5.
    outliers = mad_outliers([1, 3, 5, 7, 9, 100])
    assert outliers == [100.0]


def test_mad_returns_empty_when_no_variation():
    assert mad_outliers([5, 5, 5, 5]) == []


# --- HHI --------------------------------------------------------------------


def test_hhi_three_shares():
    # 50/30/20 → HHI = 0.25 + 0.09 + 0.04 = 0.38.
    assert hhi([50, 30, 20]) == pytest.approx(0.38)


def test_hhi_monopoly_is_one():
    assert hhi([100]) == pytest.approx(1.0)


def test_hhi_perfect_split_is_inverse_of_count():
    # Four equal participants → HHI = 4 * (0.25)² = 0.25.
    assert hhi([1, 1, 1, 1]) == pytest.approx(0.25)


def test_hhi_empty_or_zero_total_is_zero():
    assert hhi([]) == 0.0
    assert hhi([0, 0, 0]) == 0.0


# --- Gini -------------------------------------------------------------------


def test_gini_equal_distribution_is_zero():
    assert gini([1, 1, 1, 1]) == pytest.approx(0.0)


def test_gini_total_concentration_known_value():
    # Sorted [0, 0, 0, 4]. Σi·xᵢ = 16, Σxᵢ = 4, n=4.
    # gini = (2·16 - 5·4) / (4·4) = 12/16 = 0.75.
    assert gini([0, 0, 0, 4]) == pytest.approx(0.75)


def test_gini_empty_or_all_zero_is_zero():
    assert gini([]) == 0.0
    assert gini([0, 0, 0]) == 0.0


# --- Correlation ------------------------------------------------------------


def test_pearson_perfect_positive_and_negative():
    assert pearson_correlation([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == pytest.approx(1.0)
    assert pearson_correlation([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == pytest.approx(-1.0)


def test_pearson_too_short_returns_none():
    assert pearson_correlation([1], [1]) is None


def test_spearman_handles_nonlinear_monotone():
    # y = x² is non-linear but monotone increasing on [1, 5] → Spearman = 1.
    assert spearman_correlation([1, 2, 3, 4, 5], [1, 4, 9, 16, 25]) == pytest.approx(
        1.0
    )


# --- Time-series decomposition ---------------------------------------------


def test_decompose_returns_three_series_of_matching_length():
    # 24 monthly points = two full annual cycles; meets the minimum input size.
    rng = np.random.default_rng(seed=42)
    values = (
        [10 + 3 * math.sin(2 * math.pi * i / 12) + rng.normal() for i in range(24)]
    )
    out = decompose_time_series(values, period=12)
    assert len(out["trend"]) == 24
    assert len(out["seasonal"]) == 24
    assert len(out["resid"]) == 24


def test_decompose_too_short_returns_empty_arrays():
    out = decompose_time_series([1, 2, 3, 4], period=12)
    assert out == {"trend": [], "seasonal": [], "resid": []}
