"""
KELTNER BAND REVERSION BY REGIME — bull, bear, ranging.

DK: "We also need to distinguish between bull, bear and ranging market
     conditions perhaps."

Almost certainly the missing variable, and the reason is mechanical rather
than statistical. Buying the lower band is three different trades:

    in a RANGE   the band is the edge of the range. Reversion is the whole
                 mechanism and it should work.
    in a BULL    the band is a pullback inside an uptrend. Reversion and trend
                 point the same way, so it should work BEST.
    in a BEAR    the band is just where a downtrend currently is. There is
                 nothing to revert to; the mid is falling toward price rather
                 than price rising toward the mid. It should lose.

Pooling all three averages a good trade with a bad one and yields the weak,
ambiguous number the rebuild produced: +0.281%/trade at t=+2.33, below the
corrected bar of 2.63, with 26/32 cells beating their control. That pattern —
broad, consistent, but never decisive — is the signature of a conditional edge
measured unconditionally.

REGIME, DEFINED CAUSALLY
Per symbol, from trailing data only, on the bar before entry:

  direction   sign and slope of the 200-bar EMA
  efficiency  |net move| / sum|bar moves| over 100 bars (the Kaufman ratio).
              High = the market is going somewhere. Low = it is churning.

    BULL   price > EMA200, EMA200 rising, efficiency >= 0.25
    BEAR   price < EMA200, EMA200 falling, efficiency >= 0.25
    RANGE  efficiency < 0.25, either side

Thresholds are a judgement, so the efficiency cut is swept rather than picked.

Every regime keeps its own time-matched control drawn from the SAME regime,
which matters: a bull-market control is not a bear-market control, and doc 50
is the worked example of what happens when controls are drawn from the wrong
population.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

DIR = "/home/claude/qlab/data_1h_33"
MAKER, TAKER = 2 / 10000, 5 / 10000
RNG = np.random.default_rng(3311)
MAXH = 120


def atr(H, L, C, n=14):
    tr = np.maximum(H - L, np.maximum(np.abs(H - np.roll(C, 1)),
                                      np.abs(L - np.roll(C, 1))))
    tr[0] = H[0] - L[0]
    return pd.Series(tr).rolling(n).mean().bfill().values


def efficiency(C, w=100):
    net = np.abs(pd.Series(C).diff(w)).values
    gross = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(w).sum().values
    return net / np.where(gross > 0, gross, np.nan)


def hold_to_target(C, H, i, tgt, maxh=MAXH):
    n = len(C)
    e = C[i] * (1 + MAKER)
    for q in range(i + 1, min(i + 1 + maxh, n)):
        if H[q] >= tgt:
            return (tgt * (1 - MAKER)) / e - 1
    q = min(i + maxh, n - 1)
    return (C[q] * (1 - TAKER)) / e - 1


def run(eff_cut):
    rows = []
    for f in sorted(glob.glob(f"{DIR}/*.csv")):
        d = pd.read_csv(f)
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna(subset=["date"]).set_index("date").sort_index()
        if len(d) < 2000: continue
        C, H, L = d.close.values, d.high.values, d.low.values
        a = atr(H, L, C); n = len(C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        e200 = pd.Series(C).ewm(span=200, adjust=False).mean().values
        slope = np.concatenate([[np.nan]*50, e200[50:] - e200[:-50]])
        eff = efficiency(C)
        band = ema - 2 * a
        trig = (C <= band) & (np.roll(C, 1) > np.roll(band, 1))
        last = -10 ** 9
        for i in np.flatnonzero(trig):
            if i < 250 or i > n - MAXH - 2 or i - last < MAXH: continue
            if not np.isfinite(eff[i]) or not np.isfinite(slope[i]): continue
            last = i
            if eff[i] < eff_cut:
                reg = "RANGE"
            elif C[i] > e200[i] and slope[i] > 0:
                reg = "BULL"
            elif C[i] < e200[i] and slope[i] < 0:
                reg = "BEAR"
            else:
                reg = "MIXED"
            r = hold_to_target(C, H, i, ema[i])
            # control: same regime, same instrument, nearby in time
            q = None
            for _ in range(30):
                cand = int(RNG.integers(max(250, i-800), min(n-MAXH-2, i+800)+1))
                if not np.isfinite(eff[cand]) or not np.isfinite(slope[cand]): continue
                if eff[cand] < eff_cut: cr = "RANGE"
                elif C[cand] > e200[cand] and slope[cand] > 0: cr = "BULL"
                elif C[cand] < e200[cand] and slope[cand] < 0: cr = "BEAR"
                else: cr = "MIXED"
                if cr == reg: q = cand; break
            cR = hold_to_target(C, H, q, C[q] + (ema[i] - C[i])) if q else np.nan
            rows.append(dict(sym=d.index[i], regime=reg, R=r, CTRL=cR))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("KELTNER LOWER-BAND REVERSION BY REGIME")
    print("No stop, hold 120h, exit at the mid. Controls drawn from the SAME regime.\n")
    for cut in (0.20, 0.25, 0.30):
        T = run(cut)
        print(f"  efficiency cut {cut:.2f}   n={len(T)}")
        print(f"    {'regime':<8}{'n':>7}{'net/trade':>12}{'t':>8}"
              f"{'win':>8}{'control':>10}{'EDGE':>10}")
        for reg in ("BULL", "RANGE", "MIXED", "BEAR"):
            S = T[T.regime == reg]
            if len(S) < 80: continue
            r = S.R.values; c = S.CTRL.values; c = c[np.isfinite(c)]
            se = r.std(ddof=1)/np.sqrt(len(r))
            edge = r.mean() - c.mean() if len(c) > 30 else np.nan
            print(f"    {reg:<8}{len(r):>7}{r.mean()*100:>+11.3f}%"
                  f"{r.mean()/se:>+8.2f}{(r>0).mean()*100:>7.1f}%"
                  f"{c.mean()*100:>+9.3f}%{edge*100:>+9.3f}%")
        print()
