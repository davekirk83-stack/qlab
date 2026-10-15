"""
Liquidation cluster estimator.

Method (ChartPrime-style bands + Alpha Extract-style ATR zone scaling):

  1. Find swing pivots — points where leveraged positions were likely opened.
  2. Weight each pivot by the volume traded there. High-volume pivots mean
     more positions, so a denser cluster.
  3. Project the standard leverage liquidation distances from each pivot:
        10x -> ~10% adverse, 25x -> ~4%, 50x -> ~2%, 100x -> ~1%
     Longs opened at a swing LOW get liquidated BELOW it.
     Shorts opened at a swing HIGH get liquidated ABOVE it.
  4. Give each projected level a zone height scaled by ATR, so zones widen
     in volatile conditions instead of being a fixed percentage.
  5. Sum overlapping zones into a cluster strength at each price.

IMPORTANT — what this is and is not:
  This is an ESTIMATE of where stops and liquidations probably sit, computed
  from price and volume. It is NOT real liquidation data; TradingView does not
  carry liquidation feeds for most instruments and nor do we. Nearly every
  public "liquidation heatmap" is this same arithmetic. It is a model of the
  crowd's position, and it is tested, not trusted.
"""
import numpy as np, pandas as pd

LEVERAGE_BANDS = {10: 0.100, 25: 0.040, 50: 0.020, 100: 0.010}


def _atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def pivots(df, lb=10):
    """Confirmed swing highs and lows. Shifted so they are only known after
    confirmation — no lookahead."""
    w = lb * 2 + 1
    ph = (df.high == df.high.rolling(w, center=True).max())
    pl = (df.low == df.low.rolling(w, center=True).min())
    return ph.shift(lb + 1).fillna(False), pl.shift(lb + 1).fillna(False)


def clusters(df, lb=10, lookback=250, decay=0.995):
    """Returns two series: nearest significant liquidation cluster ABOVE price
    (where short liquidations sit) and BELOW price (long liquidations),
    plus their strengths."""
    ph, pl = pivots(df, lb)
    atr = _atr(df)
    vol = df.volume.replace(0, np.nan).fillna(df.volume.median() if df.volume.sum() else 1.0)
    volw = (vol / vol.rolling(50).mean()).fillna(1.0).clip(0.2, 5.0)

    above_lvl = pd.Series(np.nan, index=df.index)
    above_str = pd.Series(0.0, index=df.index)
    below_lvl = pd.Series(np.nan, index=df.index)
    below_str = pd.Series(0.0, index=df.index)

    hi_idx = np.flatnonzero(ph.values)
    lo_idx = np.flatnonzero(pl.values)
    H, L, Cl = df.high.values, df.low.values, df.close.values
    W = volw.values
    A = atr.values

    for t in range(lookback, len(df)):
        price = Cl[t]
        a = A[t] if A[t] == A[t] else price * 0.01

        # shorts opened at swing highs -> their liquidations sit ABOVE
        best_a, best_as = np.nan, 0.0
        for i in hi_idx[(hi_idx > t - lookback) & (hi_idx <= t)]:
            base = H[i]
            w = W[i] * (decay ** (t - i))
            for lev, d in LEVERAGE_BANDS.items():
                lvl = base * (1 + d)
                if lvl > price:
                    # zone strength: volume weight, decayed, scaled by proximity
                    prox = np.exp(-abs(lvl - price) / max(a * 3, 1e-9))
                    s = w * prox * (lev / 100.0 + 0.3)
                    if s > best_as:
                        best_as, best_a = s, lvl
        above_lvl.iloc[t], above_str.iloc[t] = best_a, best_as

        # longs opened at swing lows -> their liquidations sit BELOW
        best_b, best_bs = np.nan, 0.0
        for i in lo_idx[(lo_idx > t - lookback) & (lo_idx <= t)]:
            base = L[i]
            w = W[i] * (decay ** (t - i))
            for lev, d in LEVERAGE_BANDS.items():
                lvl = base * (1 - d)
                if lvl < price:
                    prox = np.exp(-abs(lvl - price) / max(a * 3, 1e-9))
                    s = w * prox * (lev / 100.0 + 0.3)
                    if s > best_bs:
                        best_bs, best_b = s, lvl
        below_lvl.iloc[t], below_str.iloc[t] = best_b, best_bs

    return dict(above=above_lvl, above_strength=above_str,
                below=below_lvl, below_strength=below_str)


# ---------------------------------------------------------------- signals
def liq_magnet_long(df, lb=10, min_str=0.5):
    """Long when a strong short-liquidation cluster sits above: price is being
    drawn toward it (the squeeze target)."""
    c = clusters(df, lb)
    dist = (c["above"] - df.close) / df.close
    return ((c["above_strength"] > min_str) & (dist < 0.08) & (dist > 0)).astype(float)


def liq_sweep_reversal(df, lb=10, min_str=0.5):
    """Long after a long-liquidation cluster BELOW has been swept and reclaimed:
    the stops are gone, so the supply above is thinner."""
    c = clusters(df, lb)
    swept = (df.low < c["below"]) & (df.close > c["below"])
    return (swept & (c["below_strength"] > min_str)).astype(float)


def liq_targets(df, lb=10):
    """Exit targets: the cluster levels themselves, for the TP engine."""
    return clusters(df, lb)
