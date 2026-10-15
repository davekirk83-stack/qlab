"""
USING THE CONTAINMENT FACT — a volatility-normalised cascade trigger.

DK: "Can we use that fact in our own way? I'm just shooting ideas."

The useful half of doc 45 is not the 95% inside the envelope — that is a
tautology. It is the 5% OUTSIDE. A bar below the lower band is, by
construction, a volatility-normalised outlier: it is far from the local mean
RELATIVE TO HOW FAR THIS INSTRUMENT USUALLY TRAVELS.

That is exactly what the cascade trade is hunting, and it is exactly what the
current trigger does badly. The registered cascade spec fires on a FIXED 3%
fall in 5 minutes. That threshold is arbitrary and does not scale:
  - SPY's normal 5-minute SD is 0.067%, so 3% is a 45-sigma event (doc 36) —
    it simply never fires, which is why the universe is only 18 symbols
  - a wild alt can print 3% in five minutes on an ordinary afternoon
So the same number means "once a decade" on one chart and "twice a day" on
another. The universe had to be hand-screened on absolute volatility to work
around it — a screen that would not be needed if the trigger scaled itself.

THE PROPOSAL
    fixed      close falls >= 3% over 5 bars          (the registered spec)
    envelope   close falls below the CAUSAL lower band by >= k x band width
    sigma      close falls >= k x the trailing SD of 5-bar returns
The second and third are both self-scaling; the envelope version additionally
knows where the local mean is, which the sigma version does not.

Entry and exit are held identical to the registered cascade spec so that only
the TRIGGER varies:
    entry   first bar whose low exceeds the prior bar's low; buy the next open
    exit    TP +1.5%, SL -2.0%, abandon after 60 bars
Plus a random-entry control, and the count of instruments on which each trigger
actually fires — because a trigger that works but only on four charts is not
an improvement.

Run on hourly data (not 1-minute) so the comparison spans all 33 perps rather
than the 18 with minute data. The question here is whether the TRIGGER FORM is
better, which is a question about scaling, not about timeframe.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
import nadaraya as NW
from levels_general import load_universe

RNG = np.random.default_rng(2222)
WIN = 5
TP, SL, MAXBARS, SLIP = 0.015, 0.020, 60, 0.0004


def triggers(df, h=8.0, mult=3.0):
    """Return {name: array of signal indices} for each trigger form."""
    c = df.close.values
    n = len(c)
    out = {}
    mv = np.full(n, np.nan)
    mv[WIN:] = c[WIN:] / c[:-WIN] - 1

    out["fixed_3pct"] = np.flatnonzero(mv <= -0.03)

    fit = NW.nw_causal(c, h=h)
    lo, hi = NW.bands(c, fit, mult=mult)
    width = hi - lo
    with np.errstate(invalid="ignore"):
        depth = (lo - c) / np.where(width > 0, width, np.nan)
    for k in (0.25, 0.5, 1.0):
        out[f"envelope_{k}"] = np.flatnonzero(depth >= k)

    sd = pd.Series(mv).rolling(500, min_periods=200).std().values
    for k in (3.0, 4.0, 5.0):
        with np.errstate(invalid="ignore"):
            out[f"sigma_{k}"] = np.flatnonzero(mv <= -k * sd)
    return out


def trade(df, i):
    """The registered cascade entry and exit, unchanged."""
    C, L, H, O = (df.close.values, df.low.values,
                  df.high.values, df.open.values)
    n = len(C)
    e = None
    for j in range(i, min(i + 30, n - 1)):
        if L[j] > L[j - 1]:
            e = j; break
    if e is None or e + 1 >= n:
        return None
    px = O[e + 1] * (1 + SLIP)
    if px <= 0:
        return None
    T, S = px * (1 + TP), px * (1 - SL)
    for k in range(e + 1, min(e + 1 + MAXBARS, n)):
        if L[k] <= S:
            return (S * (1 - SLIP)) / px - 1, e, k
        if H[k] >= T:
            return (T * (1 - SLIP)) / px - 1, e, k
    k = min(e + MAXBARS, n - 1)
    return (C[k] * (1 - SLIP)) / px - 1, e, k


def run(which):
    panel = load_universe(which)
    res = {}
    fired = {}
    ctrl = []
    for s, df in panel.items():
        if len(df) < 1200:
            continue
        try:
            T = triggers(df)
        except Exception:
            continue
        n = len(df)
        for name, idx in T.items():
            idx = [i for i in idx if 550 < i < n - MAXBARS - 5]
            kept, last = [], -10**9
            for i in idx:
                if i - last >= MAXBARS:
                    kept.append(i); last = i
            got = []
            for i in kept:
                r = trade(df, i)
                if r:
                    got.append(r[0])
            if got:
                res.setdefault(name, []).extend(got)
                fired.setdefault(name, set()).add(s)
        for _ in range(12):
            j = int(RNG.integers(550, max(551, n - MAXBARS - 5)))
            r = trade(df, j)
            if r:
                ctrl.append(r[0])
    return res, fired, np.array(ctrl)


def line(lab, r, base=None, pad=20):
    r = np.asarray(r, dtype=float); r = r[np.isfinite(r)]
    if len(r) < 40:
        print(f"  {lab:{pad}s} n={len(r):5d}  too few"); return None
    se = r.std(ddof=1) / np.sqrt(len(r))
    d = f"  vs control {(r.mean()-base)*100:+6.3f}pp" if base is not None else ""
    print(f"  {lab:{pad}s} n={len(r):5d}  {r.mean()*100:+7.3f}%  t={r.mean()/se:+6.2f}  "
          f"win {float((r>0).mean())*100:5.1f}%{d}")
    return r.mean()


if __name__ == "__main__":
    print("CASCADE TRIGGER — fixed 3% vs volatility-normalised forms")
    print("Entry and exit identical to the registered spec; only the trigger varies.\n")
    for which in ("crypto_hourly", "etf"):
        print("=" * 96)
        print(f"  {which.upper()}")
        print("=" * 96)
        res, fired, ctrl = run(which)
        base = line("control (random)", ctrl)
        print()
        order = (["fixed_3pct"] + [f"envelope_{k}" for k in (0.25, 0.5, 1.0)]
                 + [f"sigma_{k}" for k in (3.0, 4.0, 5.0)])
        for name in order:
            if name not in res:
                print(f"  {name:20s} never fired"); continue
            m = line(name, res[name], base)
            if m is not None:
                print(f"  {'':20s} fired on {len(fired[name])} instruments")
        print()
