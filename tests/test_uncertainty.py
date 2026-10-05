"""Tests for the statistical helpers in uncertainty.py. (The script itself
also asserts that its point estimates match the SQL outputs before resampling.)"""
import numpy as np
import pandas as pd
import pytest

from uncertainty import percentile_ci, week_bootstrap, wilson_ci


def test_wilson_matches_known_values():
    lo, hi = wilson_ci(34, 49)
    assert (lo, hi) == pytest.approx((0.5547, 0.8048), abs=1e-3)
    lo, hi = wilson_ci(0, 49)                     # 0 successes: a real upper bound, not 0
    assert lo == pytest.approx(0, abs=1e-12) and hi == pytest.approx(0.0727, abs=1e-3)


def test_week_bootstrap_keeps_weeks_together():
    # Two weeks: one all 1s, one all 0s. Resampling whole weeks means every
    # resample's mean is 0, 0.5 or 1; resampling days would give anything.
    df = pd.DataFrame({"week": ["w1"] * 7 + ["w2"] * 7, "x": [1] * 7 + [0] * 7})
    out = week_bootstrap(df, lambda d: d["x"].mean(), 500, np.random.default_rng(0))
    assert set(np.round(out, 6)) <= {0.0, 0.5, 1.0}
    assert 0.0 in out and 1.0 in out


def test_percentile_ci_ignores_nan():
    lo, hi = percentile_ci(np.array([np.nan] + list(range(101))))
    assert (lo, hi) == pytest.approx((2.5, 97.5))
