"""
Classical chart patterns, written numerically.

Every pattern here is defined so it is detected identically every time —
no discretion, no "it looked like a flag". If a pattern cannot be written
with numbers it does not belong in the engine.

These get NO special status. They enter the same gates as everything else,
and they increment the same trial ledger. The previous programme's own
pattern setup (a swing-failure/confluence rule) tested at no edge in one
mode and significantly worse than random in the other; that is the
expected prior here, not an exception.
"""
import numpy as np, pandas as pd


def _atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


# -------------------------------------------------- continuation patterns
def p_flag(df, imp=2.0, impn=10, consol=5, maxrange=0.5):
    """Impulse of `imp` ATR over `impn` bars, then a tight consolidation,
    then a close above the consolidation high."""
    a = _atr(df)
    impulse = (df.close - df.close.shift(impn)) / a > imp
    hi = df.high.rolling(consol).max()
    lo = df.low.rolling(consol).min()
    tight = (hi - lo) / a < maxrange * consol
    return (impulse.shift(consol).fillna(False) & tight.shift(1).fillna(False)
            & (df.close > hi.shift(1))).astype(float)


def p_pennant(df, imp=2.0, impn=10, consol=8):
    """Impulse then contracting range (each half narrower than the last), then break."""
    a = _atr(df)
    impulse = (df.close - df.close.shift(impn)) / a > imp
    h = df.high.rolling(consol).max(); l = df.low.rolling(consol).min()
    h2 = df.high.rolling(consol // 2).max(); l2 = df.low.rolling(consol // 2).min()
    contracting = (h2 - l2) < 0.6 * (h - l)
    return (impulse.shift(consol).fillna(False) & contracting
            & (df.close > h2.shift(1))).astype(float)


# -------------------------------------------------- reversal patterns
def p_double_bottom(df, lb=40, tol=0.03):
    """Two lows within `tol` of each other inside `lb` bars, then close above
    the intervening high."""
    lo = df.low.rolling(lb).min()
    recent_lo = df.low.rolling(lb // 4).min()
    near = ((recent_lo - lo) / lo).abs() < tol
    mid_hi = df.high.rolling(lb).max()
    return (near & (df.close > mid_hi.shift(1) * 0.98)).astype(float)


def p_head_shoulders_inv(df, lb=60):
    """Inverse H&S proxy: middle trough is the lowest of three windows,
    then a close above the neckline (max of the two shoulder windows)."""
    w = lb // 3
    left = df.low.rolling(w).min().shift(2 * w)
    head = df.low.rolling(w).min().shift(w)
    right = df.low.rolling(w).min()
    neck = pd.concat([df.high.rolling(w).max().shift(2 * w),
                      df.high.rolling(w).max()], axis=1).min(axis=1)
    shape = (head < left) & (head < right)
    return (shape & (df.close > neck.shift(1))).astype(float)


# -------------------------------------------------- trendline / S-R
def p_trendline_break(df, lb=50):
    """Break of a fitted descending trendline through the rolling highs."""
    def slope(x):
        n = len(x); t = np.arange(n)
        return np.polyfit(t, x, 1)[0] if n > 2 else 0.0
    sl = df.high.rolling(lb).apply(slope, raw=True)
    return ((sl < 0) & (df.close > df.high.rolling(lb // 2).max().shift(1))).astype(float)


def p_support_retest(df, lb=50, tol=0.02):
    """Break above resistance, then a retest that holds it as support."""
    res = df.high.rolling(lb).max().shift(1)
    broke = (df.close > res).rolling(10).max().astype(bool)
    retest = ((df.low - res) / res).abs() < tol
    return (broke & retest & (df.close > df.open)).astype(float)


# -------------------------------------------------- candlesticks
def p_engulfing(df):
    prev_red = df.close.shift(1) < df.open.shift(1)
    engulf = (df.close > df.open.shift(1)) & (df.open < df.close.shift(1))
    return (prev_red & engulf).astype(float)


def p_pinbar(df, wick=2.0):
    body = (df.close - df.open).abs()
    lower = pd.concat([df.close, df.open], axis=1).min(axis=1) - df.low
    return ((lower > wick * body) & (df.close > df.open)).astype(float)


def p_inside_break(df):
    inside = (df.high < df.high.shift(1)) & (df.low > df.low.shift(1))
    return (inside.shift(1).fillna(False) & (df.close > df.high.shift(1))).astype(float)


# -------------------------------------------------- confirmation wrappers
def confirm_volume(df, mult=1.5):
    v = df.volume.replace(0, np.nan)
    return (v > v.rolling(20).mean() * mult).fillna(True).astype(float)


def confirm_close_strength(df, q=0.6):
    rng = (df.high - df.low).replace(0, np.nan)
    return (((df.close - df.low) / rng) > q).fillna(False).astype(float)


def confirm_followthrough(df):
    return (df.close > df.close.shift(1)).astype(float)


PATTERNS = {
    "flag":      (p_flag,              [(2.0, 10, 5, 0.5), (1.5, 20, 8, 0.6), (3.0, 10, 5, 0.4)]),
    "pennant":   (p_pennant,           [(2.0, 10, 8), (1.5, 20, 12)]),
    "dblbottom": (p_double_bottom,     [(40, 0.03), (60, 0.05)]),
    "invhs":     (p_head_shoulders_inv,[(60,), (90,)]),
    "tlbreak":   (p_trendline_break,   [(50,), (100,)]),
    "sretest":   (p_support_retest,    [(50, 0.02), (100, 0.03)]),
    "engulf":    (p_engulfing,         [()]),
    "pinbar":    (p_pinbar,            [(2.0,), (3.0,)]),
    "insidebrk": (p_inside_break,      [()]),
}

CONFIRMS = {
    "noconf":  lambda df: pd.Series(1.0, index=df.index),
    "vol":     confirm_volume,
    "strong":  confirm_close_strength,
    "follow":  confirm_followthrough,
}
