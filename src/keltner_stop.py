"""
KELTNER BAND REVERSION — does a wider stop make it work?

DK: "Then change the stop loss on the Keltner so that it's wider. Does that
     make it work?"

Doc 48 found outer-band hits revert to the mid 77-86% of the time and DK called
it edge. Doc 65 found the trade LOSES once a stop is attached: -0.094% at 26.7%
win with the stop 1 ATR below the band. The obvious suspect is the stop, because
cost in R and survival both scale with it (doc 51's lesson, in reverse).

So: sweep it. Stop placed k ATR below the lower band, k from 0.5 to 6, plus a
no-stop version holding to the mid or a time cap. Every cell carries:
  - return per trade, net of costs (maker in, maker out on target,
    taker + slippage on the stop)
  - win rate and reward:risk, because a wide stop buys survival with R
  - the hit rate on the mid, to check doc 48's statistic survives in-sample here
  - a time-matched control, so a positive number has to beat doing it randomly

If a plateau of positive cells appears, the trade works and the stop was the
problem. If only isolated cells work, it is a fitted cell and the answer is no.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

DIR = "/home/claude/qlab/data_1h_33"
MAKER, TAKER, SLIP = 2 / 10000, 5 / 10000, 10 / 10000
RNG = np.random.default_rng(4848)


def atr(H, L, C, n=14):
    tr = np.maximum(H - L, np.maximum(np.abs(H - np.roll(C, 1)),
                                      np.abs(L - np.roll(C, 1))))
    tr[0] = H[0] - L[0]
    return pd.Series(tr).rolling(n).mean().bfill().values


def trade(C, H, L, i, stop, tgt, maxh):
    n = len(C)
    e = C[i] * (1 + MAKER)
    if stop >= e:
        return None
    risk = e - stop
    for q in range(i + 1, min(i + 1 + maxh, n)):
        if L[q] <= stop:
            return ((stop * (1 - SLIP - TAKER)) / e - 1, -1.0, False)
        if H[q] >= tgt:
            r = (tgt * (1 - MAKER)) / e - 1
            return (r, r * e / risk, True)
    q = min(i + maxh, n - 1)
    r = (C[q] * (1 - MAKER)) / e - 1
    return (r, r * e / risk, False)


def run(katr, maxh):
    real, ctrl, hits, rr = [], [], [], []
    for f in sorted(glob.glob(f"{DIR}/*.csv")):
        d = pd.read_csv(f)
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna(subset=["date"]).set_index("date").sort_index()
        if len(d) < 2000:
            continue
        C, H, L = d.close.values, d.high.values, d.low.values
        a = atr(H, L, C); n = len(C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        band = ema - 2 * a
        trig = (C <= band) & (np.roll(C, 1) > np.roll(band, 1))
        last = -10 ** 9
        idx = []
        for i in np.flatnonzero(trig):
            if i < 50 or i > n - maxh - 2 or i - last < maxh:
                continue
            last = i; idx.append(i)
        for i in idx:
            t = trade(C, H, L, i, band[i] - katr * a[i], ema[i], maxh)
            if t is None:
                continue
            real.append(t[0]); rr.append(t[1]); hits.append(t[2])
            q = int(RNG.integers(max(50, i - 500), min(n - maxh - 2, i + 500) + 1))
            c = trade(C, H, L, q, C[q] - (C[q] - (band[q] - katr * a[q])),
                      C[q] + (ema[q] - band[q]), maxh)
            if c:
                ctrl.append(c[0])
    return np.array(real), np.array(ctrl), np.array(hits), np.array(rr)


if __name__ == "__main__":
    print("KELTNER LOWER-BAND REVERSION — stop width sweep, 33 perps hourly")
    print("Target = the mid. Costs netted. Time-matched control on every cell.\n")
    print(f"  {'stop':>6}{'hold':>6}{'n':>7}{'net/trade':>12}{'t':>8}"
          f"{'win':>8}{'mid hit':>9}{'control':>10}{'EDGE':>10}")
    cells = []
    for maxh in (48, 120, 240):
        for katr in (0.5, 1, 2, 3, 4, 6):
            r, c, h, rr = run(katr, maxh)
            if len(r) < 100 or len(c) < 100:
                continue
            se = np.sqrt(r.std(ddof=1)**2/len(r) + c.std(ddof=1)**2/len(c))
            edge = r.mean() - c.mean()
            cells.append((edge, katr, maxh, r, c))
            print(f"  {katr:>5}A{maxh:>6}{len(r):>7}{r.mean()*100:>+11.3f}%"
                  f"{r.mean()/(r.std(ddof=1)/np.sqrt(len(r))):>+8.2f}"
                  f"{(r>0).mean()*100:>7.1f}%{h.mean()*100:>8.1f}%"
                  f"{c.mean()*100:>+9.3f}%{edge*100:>+9.3f}%")
    pos = sum(1 for x in cells if x[3].mean() > 0)
    print(f"\n  {pos}/{len(cells)} cells net positive")
    pe = sum(1 for x in cells if x[0] > 0)
    print(f"  {pe}/{len(cells)} cells beat their time-matched control")
    if cells:
        b = max(cells, key=lambda x: x[3].mean())
        r = b[3]
        print(f"  best: stop {b[1]} ATR, hold {b[2]}h -> "
              f"{r.mean()*100:+.3f}%/trade, edge {b[0]*100:+.3f}pp")
