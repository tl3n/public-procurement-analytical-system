"""Pure-Python statistical routines built on pandas / numpy / statsmodels.

These functions operate on raw numeric sequences (after the SQL aggregation
layer has lifted the data out of the database) and exist so callers can ask
"what shape does this distribution have?" rather than "show me the mean".
Each function is total — empty or degenerate input produces a defined,
documented value (typically ``None`` or an empty list) rather than raising.
"""

from collections.abc import Iterable
from typing import TypedDict

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose


class DescriptiveStats(TypedDict):
    n: int
    mean: float | None
    median: float | None
    std: float | None
    min: float | None
    max: float | None
    q1: float | None
    q3: float | None


def _series(values: Iterable[float]) -> pd.Series:
    return pd.Series(list(values), dtype=float).dropna()


def descriptive_stats(values: Iterable[float]) -> DescriptiveStats:
    """Mean / median / quartiles / std / min / max. All ``None`` when empty."""
    s = _series(values)
    if s.empty:
        return DescriptiveStats(
            n=0,
            mean=None,
            median=None,
            std=None,
            min=None,
            max=None,
            q1=None,
            q3=None,
        )
    return DescriptiveStats(
        n=int(s.size),
        mean=float(s.mean()),
        median=float(s.median()),
        std=float(s.std(ddof=1)) if s.size > 1 else 0.0,
        min=float(s.min()),
        max=float(s.max()),
        q1=float(s.quantile(0.25)),
        q3=float(s.quantile(0.75)),
    )


# --- Outlier detection ------------------------------------------------------


def iqr_outliers(values: Iterable[float], multiplier: float = 1.5) -> list[float]:
    """Tukey's IQR rule. Returns the actual outlier values, preserving order.

    The default 1.5×IQR multiplier matches Tukey's original convention. With
    fewer than four samples the rule is not meaningful — we return ``[]``.
    """
    s = _series(values)
    if s.size < 4:
        return []
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    lo = q1 - multiplier * iqr
    hi = q3 + multiplier * iqr
    return [float(v) for v in s if v < lo or v > hi]


def mad_outliers(
    values: Iterable[float], threshold: float = 3.5
) -> list[float]:
    """Modified z-score (median absolute deviation) outlier rule.

    Robust to extreme values that would otherwise inflate the standard
    deviation used by the classical z-score. ``threshold`` of 3.5 is the
    conventional cutoff (Iglewicz & Hoaglin).
    """
    s = _series(values)
    if s.size < 3:
        return []
    median = s.median()
    mad = (s - median).abs().median()
    if mad == 0:
        return []
    # 0.6745 ≈ Φ⁻¹(0.75) — scaling makes the modified z comparable to a
    # classical z-score under a normal distribution.
    modified_z = 0.6745 * (s - median) / mad
    return [
        float(v) for v, z in zip(s, modified_z, strict=True) if abs(z) > threshold
    ]


# --- Concentration ----------------------------------------------------------


def hhi(values: Iterable[float]) -> float:
    """Herfindahl–Hirschman Index — Σ sᵢ² of normalized shares.

    Accepts raw values (which are normalized internally) or already-normalized
    shares — either form yields the same result. Returns 0.0 for empty input
    or a sum of zero.
    """
    arr = np.asarray(list(values), dtype=float)
    arr = arr[~np.isnan(arr)]
    total = arr.sum()
    if arr.size == 0 or total == 0:
        return 0.0
    shares = arr / total
    return float(np.sum(shares**2))


def gini(values: Iterable[float]) -> float:
    """Gini coefficient — 0 = perfect equality, 1 = total concentration.

    Negative inputs are dropped (Gini is defined for non-negative income-like
    quantities); empty input returns 0.0.
    """
    arr = np.asarray(list(values), dtype=float)
    arr = arr[~np.isnan(arr) & (arr >= 0)]
    if arr.size == 0 or arr.sum() == 0:
        return 0.0
    arr = np.sort(arr)
    n = arr.size
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * arr) - (n + 1) * arr.sum()) / (n * arr.sum()))


# --- Correlation ------------------------------------------------------------


def _correlate(
    xs: Iterable[float], ys: Iterable[float], method: str
) -> float | None:
    x = pd.Series(list(xs), dtype=float)
    y = pd.Series(list(ys), dtype=float)
    df = pd.concat([x, y], axis=1).dropna()
    if len(df) < 2:
        return None
    value = df.iloc[:, 0].corr(df.iloc[:, 1], method=method)
    return None if pd.isna(value) else float(value)


def pearson_correlation(
    xs: Iterable[float], ys: Iterable[float]
) -> float | None:
    """Linear correlation. ``None`` when fewer than two paired observations."""
    return _correlate(xs, ys, "pearson")


def spearman_correlation(
    xs: Iterable[float], ys: Iterable[float]
) -> float | None:
    """Rank correlation — robust to non-linear monotone relationships."""
    return _correlate(xs, ys, "spearman")


# --- Time-series decomposition ---------------------------------------------


class DecompositionResult(TypedDict):
    trend: list[float | None]
    seasonal: list[float | None]
    resid: list[float | None]


def decompose_time_series(
    values: Iterable[float], period: int = 12
) -> DecompositionResult:
    """Additive seasonal decomposition (trend + seasonal + residual).

    Returns empty lists when the input is shorter than two full periods — the
    minimum for ``statsmodels.seasonal_decompose``. ``NaN`` values in the
    output (the boundary smoothing leaves a few) are converted to ``None``.
    """
    s = _series(values)
    if s.size < 2 * period:
        return DecompositionResult(trend=[], seasonal=[], resid=[])
    result = seasonal_decompose(
        s, model="additive", period=period, extrapolate_trend="freq"
    )
    return DecompositionResult(
        trend=[None if pd.isna(v) else float(v) for v in result.trend],
        seasonal=[None if pd.isna(v) else float(v) for v in result.seasonal],
        resid=[None if pd.isna(v) else float(v) for v in result.resid],
    )
