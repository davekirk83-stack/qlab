"""
NADARAYA-WATSON ENVELOPE — and the repainting trap.

DK: "I think in my own TradingView account I used a Nadaraya Watson envelope
which was pretty damn good."

WHAT IT IS
Nadaraya-Watson is kernel regression: each point of the fitted line is a
weighted average of nearby closes, with a Gaussian kernel giving nearer bars
more weight. Bands are placed at +/- k x the mean absolute residual. The trade
is mean reversion: buy the lower band, sell the upper.

THE PROBLEM, which is the whole point of this file
The widely used TradingView version (LuxAlgo's "Nadaraya-Watson Envelope")
is REPAINTING. For a bar at index i it weights bars on BOTH SIDES of i —
including bars that had not happened yet. The kernel is symmetric in time.

That is not a subtle flaw. It means the line bends toward turns it has already
seen. On a historical chart it looks extraordinary; live it redraws as each new
bar arrives, and the signal you acted on may vanish. LuxAlgo say so themselves
in the script's notes; most users never read that far.

So this file implements BOTH and measures the difference:

    nw_repaint      symmetric kernel, uses future bars   <- the TradingView one
    nw_causal       one-sided kernel, past bars only     <- what is tradeable

If the repainting version scores far better, that difference IS the lookahead,
quantified. It is the honest answer to "it was pretty damn good".

TESTED AS A MEAN-REVERSION SIGNAL
Long when close crosses back up through the lower band. Scored with the
hold-40, stop-only exit that won the target study (doc 44), against matched
random entries with the same stop distance.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
from levels_general import load_universe

RNG = np.random.default_rng(31337)
HOLD = 40


def nw_repaint(close, h=8.0, window=500):
    """Symmetric Gaussian kernel — THE REPAINTING VERSION. Uses future bars.

    Included to measure the lookahead, not to trade."""
    n = len(close)
    out = np.full(n, np.nan)
    w = min(window, n)
    x = close[-w:]
    idx = np.arange(w)
    for i in range(w):
        k = np.exp(-((idx - i) ** 2) / (2 * h * h))
        out[n - w + i] = np.sum(k * x) / np.sum(k)
    return out


def nw_causal(close, h=8.0, span=60):
    """One-sided Gaussian kernel — PAST BARS ONLY. This one is tradeable.

    Each fitted value uses only bars at or before its own index, so it never
    changes once printed."""
    n = len(close)
    out = np.full(n, np.nan)
    off = np.arange(span)
    k = np.exp(-(off ** 2) / (2 * h * h))
    ks = k.sum()
    for i in range(span, n):
        seg = close[i - span + 1:i + 1][::-1]
        out[i] = np.dot(k, seg) / ks
    return out


def bands(close, fit, mult=3.0, win=200):
    resid = pd.Series(np.abs(close - fit))
    mae = resid.rolling(win, min_periods=30).mean().values * mult
    return fit - mae, fit + mae


def signals(close, lower):
    """Close crosses back UP through the lower band."""
    s = np.zeros(len(close), dtype=bool)
    ok = ~np.isnan(lower)
    s[1:] = ok[1:] & ok[:-1] & (close[:-1] <= lower[:-1]) & (close[1:] > lower[1:])
    return np.flatnonzero(s)


def hold_score(df, bar, entry, stop, hold=HOLD):
    H, L, C = df.high.values, df.low.values, df.close.values
    risk = entry - stop
    if risk <= 0:
        return None
    last = bar + hold
    if last > len(C) - 1:
        return None
    for j in range(bar + 1, last + 1):
        if L[j] <= stop:
            return -1.0
    return float((C[last] - entry) / risk)


def run(which, variant, h=8.0, mult=3.0, stop_atr=1.5):
    panel = load_universe(which)
    real, ctrl = [], []
    for s, df in panel.items():
        if len(df) < 800:
            continue
        c = df.close.values
        a = ST.atr(df).bfill().values
        fit = nw_repaint(c, h=h) if variant == "repaint" else nw_causal(c, h=h)
        lo, _ = bands(c, fit, mult=mult)
        sig = signals(c, lo)
        sig = [i for i in sig if 250 < i < len(c) - HOLD - 2]
        # one per episode
        kept, last = [], -10**9
        for i in sig:
            if i - last >= HOLD:
                kept.append(i); last = i
        for i in kept:
            if a[i] <= 0:
                continue
            r = hold_score(df, i, c[i], c[i] - stop_atr * a[i])
            if r is not None:
                real.append(r)
        for _ in range(len(kept)):
            j = int(RNG.integers(250, max(251, len(c) - HOLD - 2)))
            if a[j] <= 0:
                continue
            r = hold_score(df, j, c[j], c[j] - stop_atr * a[j])
            if r is not None:
                ctrl.append(r)
    return np.array(real), np.array(ctrl)


def line(lab, r, base=None):
    if len(r) < 50:
        print(f"  {lab:34s} n={len(r):5d}  too few"); return None
    se = r.std(ddof=1) / np.sqrt(len(r))
    d = f"   vs control {r.mean()-base:+6.3f}R" if base is not None else ""
    print(f"  {lab:34s} n={len(r):5d}  {r.mean():+6.3f}R  t={r.mean()/se:+6.2f}  "
          f"win {float((r>0).mean())*100:5.1f}%{d}")
    return r.mean()


if __name__ == "__main__":
    print("NADARAYA-WATSON ENVELOPE — repainting vs causal\n")
    print("Long on a close crossing back up through the lower band.")
    print("Exit: hold 40 bars, stop 1.5 ATR (the doc 44 exit).\n")
    for which in ("crypto_hourly", "etf"):
        print("=" * 92)
        print(f"  {which.upper()}")
        print("=" * 92)
        res = {}
        for variant in ("repaint", "causal"):
            r, c = run(which, variant)
            cb = line(f"  control ({variant})", c)
            m = line(f"NW {variant.upper()}", r, cb)
            res[variant] = (m, cb)
            print()
        if res["repaint"][0] is not None and res["causal"][0] is not None:
            gap = res["repaint"][0] - res["causal"][0]
            print(f"  LOOKAHEAD = repaint - causal = {gap:+.3f}R per trade")
            print(f"  (that gap is not edge; it is the future leaking in)\n")
