"""
CANDLESTICK LIBRARY — written numerically, with the BEARISH ones treated as
bearish rather than quietly tested as longs.

DK: "Also candlestick types and patterns" / "Hanging man and shooting star may
be particularly useful."

Both of those are BEARISH reversal signals and both require a PRIOR UPTREND to
mean anything — a hanging man without the uptrend is just a hammer, the same
shape pointing the other way. Most published candlestick studies ignore the
context requirement and then report that candlesticks do not work. Here every
pattern carries its context condition, and each one declares its direction so
the test measures the move it actually predicts.

ANATOMY, consistent across every definition:
    body        |close - open|
    range       high - low
    upper wick  high - max(open, close)
    lower wick  min(open, close) - low

CONTEXT is volatility-scaled (ATR), not a fixed percent, so one definition works
on BTC hourly and on SPY daily.
"""
import numpy as np, pandas as pd


def parts(df):
    o, h, l, c = df.open, df.high, df.low, df.close
    body = (c - o).abs()
    rng = (h - l).replace(0, np.nan)
    up = h - pd.concat([o, c], axis=1).max(axis=1)
    dn = pd.concat([o, c], axis=1).min(axis=1) - l
    return o, h, l, c, body, rng, up, dn


def atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def uptrend(df, n=10, k=1.0):
    """Price has risen by k x ATR over the last n bars — the context a hanging
    man or shooting star REQUIRES."""
    return (df.close - df.close.shift(n)) / atr(df) > k


def downtrend(df, n=10, k=1.0):
    return (df.close.shift(n) - df.close) / atr(df) > k


# ------------------------------------------------------------ BEARISH
def c_hanging_man(df, wick=2.0, upmax=0.3, trend=1.0):
    """Small body at the TOP of the range, long lower wick, AFTER a rally.
    Same shape as a hammer; the uptrend is what makes it bearish."""
    o, h, l, c, body, rng, up, dn = parts(df)
    shape = (dn > wick * body) & (up < upmax * rng) & (body > 0)
    return (shape & uptrend(df, k=trend)).fillna(False).astype(float)


def c_shooting_star(df, wick=2.0, dnmax=0.3, trend=1.0):
    """Small body at the BOTTOM of the range, long upper wick, AFTER a rally.
    Buyers pushed up and were rejected inside one bar."""
    o, h, l, c, body, rng, up, dn = parts(df)
    shape = (up > wick * body) & (dn < dnmax * rng) & (body > 0)
    return (shape & uptrend(df, k=trend)).fillna(False).astype(float)


def c_bear_engulf(df, trend=1.0):
    prev_green = df.close.shift(1) > df.open.shift(1)
    eng = (df.close < df.open.shift(1)) & (df.open > df.close.shift(1))
    return (prev_green & eng & uptrend(df, k=trend)).fillna(False).astype(float)


def c_evening_star(df, trend=1.0):
    """Big green, small-bodied gap-ish middle, big red closing into the first."""
    o, h, l, c, body, rng, up, dn = parts(df)
    a = atr(df)
    big_green = (c.shift(2) > o.shift(2)) & (body.shift(2) > 0.6 * a)
    small_mid = body.shift(1) < 0.3 * body.shift(2)
    big_red = (c < o) & (body > 0.6 * a) & (c < (o.shift(2) + c.shift(2)) / 2)
    return (big_green & small_mid & big_red & uptrend(df, k=trend)).fillna(False).astype(float)


def c_bear_harami(df, trend=1.0):
    inside = (df.high < df.high.shift(1)) & (df.low > df.low.shift(1))
    prev_green = df.close.shift(1) > df.open.shift(1)
    return (inside & prev_green & uptrend(df, k=trend)).fillna(False).astype(float)


def c_tweezer_top(df, tol=0.1, trend=1.0):
    o, h, l, c, body, rng, up, dn = parts(df)
    a = atr(df)
    same = (df.high - df.high.shift(1)).abs() < tol * a
    return (same & (c < o) & (c.shift(1) > o.shift(1))
            & uptrend(df, k=trend)).fillna(False).astype(float)


def c_bear_marubozu(df, bodyq=0.9):
    o, h, l, c, body, rng, up, dn = parts(df)
    return ((c < o) & (body / rng > bodyq)).fillna(False).astype(float)


# ------------------------------------------------------------ BULLISH
def c_hammer(df, wick=2.0, upmax=0.3, trend=1.0):
    """The hanging man's mirror: same shape, but after a DECLINE."""
    o, h, l, c, body, rng, up, dn = parts(df)
    shape = (dn > wick * body) & (up < upmax * rng) & (body > 0)
    return (shape & downtrend(df, k=trend)).fillna(False).astype(float)


def c_inv_hammer(df, wick=2.0, dnmax=0.3, trend=1.0):
    """Shooting star's mirror, after a decline."""
    o, h, l, c, body, rng, up, dn = parts(df)
    shape = (up > wick * body) & (dn < dnmax * rng) & (body > 0)
    return (shape & downtrend(df, k=trend)).fillna(False).astype(float)


def c_bull_engulf(df, trend=1.0):
    prev_red = df.close.shift(1) < df.open.shift(1)
    eng = (df.close > df.open.shift(1)) & (df.open < df.close.shift(1))
    return (prev_red & eng & downtrend(df, k=trend)).fillna(False).astype(float)


def c_morning_star(df, trend=1.0):
    o, h, l, c, body, rng, up, dn = parts(df)
    a = atr(df)
    big_red = (c.shift(2) < o.shift(2)) & (body.shift(2) > 0.6 * a)
    small_mid = body.shift(1) < 0.3 * body.shift(2)
    big_green = (c > o) & (body > 0.6 * a) & (c > (o.shift(2) + c.shift(2)) / 2)
    return (big_red & small_mid & big_green & downtrend(df, k=trend)).fillna(False).astype(float)


def c_bull_harami(df, trend=1.0):
    inside = (df.high < df.high.shift(1)) & (df.low > df.low.shift(1))
    prev_red = df.close.shift(1) < df.open.shift(1)
    return (inside & prev_red & downtrend(df, k=trend)).fillna(False).astype(float)


def c_tweezer_bottom(df, tol=0.1, trend=1.0):
    o, h, l, c, body, rng, up, dn = parts(df)
    a = atr(df)
    same = (df.low - df.low.shift(1)).abs() < tol * a
    return (same & (c > o) & (c.shift(1) < o.shift(1))
            & downtrend(df, k=trend)).fillna(False).astype(float)


def c_three_soldiers(df):
    o, h, l, c, body, rng, up, dn = parts(df)
    a = atr(df)
    g = (c > o) & (body > 0.4 * a)
    return (g & g.shift(1) & g.shift(2) & (c > c.shift(1))
            & (c.shift(1) > c.shift(2))).fillna(False).astype(float)


def c_bull_marubozu(df, bodyq=0.9):
    o, h, l, c, body, rng, up, dn = parts(df)
    return ((c > o) & (body / rng > bodyq)).fillna(False).astype(float)


# ------------------------------------------------------------ NEUTRAL
def c_doji(df, bodyq=0.05):
    o, h, l, c, body, rng, up, dn = parts(df)
    return ((body / rng < bodyq)).fillna(False).astype(float)


def c_spinning_top(df, bodyq=0.25, wickq=0.3):
    o, h, l, c, body, rng, up, dn = parts(df)
    return ((body / rng < bodyq) & (up / rng > wickq)
            & (dn / rng > wickq)).fillna(False).astype(float)


# direction: +1 = predicts UP, -1 = predicts DOWN, 0 = no direction claimed
CANDLES = {
    # DK's two, at three context strictnesses each
    "hanging_man":       (c_hanging_man,   [(2.0, 0.3, 1.0), (2.0, 0.3, 2.0), (3.0, 0.2, 1.0)], -1),
    "shooting_star":     (c_shooting_star, [(2.0, 0.3, 1.0), (2.0, 0.3, 2.0), (3.0, 0.2, 1.0)], -1),
    # other bearish
    "bear_engulf":       (c_bear_engulf,   [(1.0,), (2.0,)], -1),
    "evening_star":      (c_evening_star,  [(1.0,)], -1),
    "bear_harami":       (c_bear_harami,   [(1.0,)], -1),
    "tweezer_top":       (c_tweezer_top,   [(0.1, 1.0)], -1),
    "bear_marubozu":     (c_bear_marubozu, [(0.9,)], -1),
    # bullish mirrors
    "hammer":            (c_hammer,        [(2.0, 0.3, 1.0), (3.0, 0.2, 1.0)], +1),
    "inv_hammer":        (c_inv_hammer,    [(2.0, 0.3, 1.0)], +1),
    "bull_engulf":       (c_bull_engulf,   [(1.0,), (2.0,)], +1),
    "morning_star":      (c_morning_star,  [(1.0,)], +1),
    "bull_harami":       (c_bull_harami,   [(1.0,)], +1),
    "tweezer_bottom":    (c_tweezer_bottom,[(0.1, 1.0)], +1),
    "three_soldiers":    (c_three_soldiers,[()], +1),
    "bull_marubozu":     (c_bull_marubozu, [(0.9,)], +1),
    # neutral — tested for VOLATILITY, not direction
    "doji":              (c_doji,          [(0.05,), (0.1,)], 0),
    "spinning_top":      (c_spinning_top,  [(0.25, 0.3)], 0),
}
