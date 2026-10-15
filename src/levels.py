"""
Major price levels and breaks — higher-timeframe structure.

A rolling N-day high is NOT the same as last month's high: market participants
watch calendar levels, prior-period extremes, round numbers and swing pivots.
These are the levels people actually mark on charts.
"""
import numpy as np, pandas as pd


def _prior_period(df, rule, how):
    g = getattr(df.resample(rule), how)()
    return g.shift(1).reindex(df.index, method="ffill")


def l_break_prior_week_high(df):
    return (df.close > _prior_period(df[["high"]], "W", "max").high).astype(float)

def l_break_prior_month_high(df):
    return (df.close > _prior_period(df[["high"]], "ME", "max").high).astype(float)

def l_break_prior_quarter_high(df):
    return (df.close > _prior_period(df[["high"]], "QE", "max").high).astype(float)

def l_break_prior_year_high(df):
    return (df.close > _prior_period(df[["high"]], "YE", "max").high).astype(float)

def l_hold_prior_month_low(df):
    lo = _prior_period(df[["low"]], "ME", "min").low
    return ((df.low <= lo * 1.01) & (df.close > lo)).astype(float)

def l_at_all_time_high(df, tol=0.02):
    ath = df.high.cummax().shift(1)
    return (df.close > ath * (1 - tol)).astype(float)

def l_round_number(df, tol=0.005):
    """Close within tol of a psychological round level (1/2/5 x power of ten)."""
    p = df.close.replace(0, np.nan)
    mag = 10 ** np.floor(np.log10(p))
    out = pd.Series(False, index=df.index)
    for mult in (1.0, 2.0, 5.0):
        step = mag * mult
        near = ((p % step) / p < tol) | ((step - (p % step)) / p < tol)
        out = out | near.fillna(False)
    return out.astype(float)

def l_swing_break(df, lb=20):
    """Break of the last confirmed swing high (a pivot, not a rolling max)."""
    piv = (df.high == df.high.rolling(lb * 2 + 1, center=True).max())
    lvl = df.high.where(piv).shift(lb + 1).ffill()
    return (df.close > lvl).astype(float)

def l_dist_from_year_high(df, q=0.95):
    """Continuous: close is in the top q of its trailing 1-year range."""
    hi = df.high.rolling(252).max(); lo = df.low.rolling(252).min()
    return (((df.close - lo) / (hi - lo)) > q).astype(float)

def l_retest_prior_month_high(df, tol=0.015):
    h = _prior_period(df[["high"]], "ME", "max").high
    broke = (df.close > h).rolling(10).max().astype(bool)
    return (broke & (((df.low - h) / h).abs() < tol) & (df.close > df.open)).astype(float)


LEVELS = {
    "brk_wk_hi":   (l_break_prior_week_high,    [()]),
    "brk_mo_hi":   (l_break_prior_month_high,   [()]),
    "brk_qt_hi":   (l_break_prior_quarter_high, [()]),
    "brk_yr_hi":   (l_break_prior_year_high,    [()]),
    "hold_mo_lo":  (l_hold_prior_month_low,     [()]),
    "ath":         (l_at_all_time_high,         [(0.02,), (0.05,)]),
    "roundnum":    (l_round_number,             [(0.005,), (0.01,)]),
    "swingbrk":    (l_swing_break,              [(10,), (20,), (40,)]),
    "topofyear":   (l_dist_from_year_high,      [(0.90,), (0.95,)]),
    "retest_mo":   (l_retest_prior_month_high,  [(0.015,)]),
}
