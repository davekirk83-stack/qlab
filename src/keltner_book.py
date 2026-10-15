"""
KELTNER BAND REVERSION, REBUILT — applying everything learned today.

DK: "Then change the stop loss on the Keltner so that it's wider. Does that
     make it work?"  ... "You're not problem solving enough. When there is a
     failure - ask yourself why? and what can be improved? what am I missing?"

WHAT THE STOP SWEEP SHOWED (keltner_stop.py)
  18/18 cells beat their time-matched control. Every one.
  Return rises monotonically with stop width: -0.121% at 1 ATR -> +0.158% at 6.
  Win rate rises with it too: 23.3% -> 69.8%.

So the entry was never the problem. Two things were, and both are fixable:

  1. THE STOP WAS FAR TOO TIGHT. A band touch is a volatility event; a stop
     1 ATR below a 2-ATR band sits inside the noise that produced the signal.
     It was still improving at 6 ATR, the edge of the sweep, so the sweep is
     extended here to 8, 10 and no-stop.

  2. THE TARGET IS NOW THE BINDING CONSTRAINT. 69.8% win for +0.158% means
     the winners are tiny: the mid is only 2 ATR from the band. Doc 63 found
     exactly this on the cascade book — the mean is the high-probability
     target and the WRONG one to use alone, and the fix was DK's taper:
     half at the mean, half at the opposing band.

  3. FILLS. Doc 65: laddering into the entry beat a single fill on both event
     sets tested, best with weight increasing toward the extreme. A band touch
     is exactly a "price approaching my level" situation, so the rungs go
     between the band and the stop.

This is three of today's findings composed onto one trade rather than tested
in isolation, which is the point: none of them is a strategy on its own.

Every cell still carries a time-matched control, costs are netted throughout
(maker in on the ladder, maker out on targets, taker + slippage on the stop),
and the whole grid is printed so a lucky cell shows up as a lucky cell.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

DIR = "/home/claude/qlab/data_1h_33"
MAKER, TAKER, SLIP = 2 / 10000, 5 / 10000, 10 / 10000
RNG = np.random.default_rng(1148)


def atr(H, L, C, n=14):
    tr = np.maximum(H - L, np.maximum(np.abs(H - np.roll(C, 1)),
                                      np.abs(L - np.roll(C, 1))))
    tr[0] = H[0] - L[0]
    return pd.Series(tr).rolling(n).mean().bfill().values


def play(C, H, L, i, stop, t1, t2, maxh, rungs, weights):
    """Ladder in between C[i] and the stop; half out at t1, half at t2."""
    n = len(C)
    top = C[i]
    if stop >= top * 0.999:
        return None
    px = [top] if rungs == 1 else list(np.linspace(top, stop * 1.002, rungs))
    w = np.array(weights[:len(px)], float); w = w / w.sum()
    filled, half_done, pnl = [], False, 0.0
    for q in range(i + 1, min(i + 1 + maxh, n)):
        for p, ww in zip(px, w):
            if L[q] <= p and not any(abs(p - fp) < 1e-12 for fp, _ in filled):
                filled.append((p, ww))
        if not filled:
            continue
        dep = sum(x for _, x in filled)
        e = (sum(p * x for p, x in filled) / dep) * (1 + MAKER)
        if stop is not None and L[q] <= stop:
            rest = 1.0 if not half_done else 0.5
            return pnl + rest * ((stop * (1 - SLIP - TAKER)) / e - 1) * dep, dep
        if not half_done and H[q] >= t1:
            pnl += 0.5 * ((t1 * (1 - MAKER)) / e - 1) * dep
            half_done = True
            continue
        if half_done and H[q] >= t2:
            return pnl + 0.5 * ((t2 * (1 - MAKER)) / e - 1) * dep, dep
    if not filled:
        return 0.0, 0.0
    dep = sum(x for _, x in filled)
    e = (sum(p * x for p, x in filled) / dep) * (1 + MAKER)
    q = min(i + maxh, n - 1)
    rest = 1.0 if not half_done else 0.5
    return pnl + rest * ((C[q] * (1 - MAKER)) / e - 1) * dep, dep


def run(katr, maxh, rungs, weights, taper):
    real, ctrl, dep = [], [], []
    for f in sorted(glob.glob(f"{DIR}/*.csv")):
        d = pd.read_csv(f)
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna(subset=["date"]).set_index("date").sort_index()
        if len(d) < 2000: continue
        C, H, L = d.close.values, d.high.values, d.low.values
        a = atr(H, L, C); n = len(C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        band = ema - 2 * a; upper = ema + 2 * a
        trig = (C <= band) & (np.roll(C, 1) > np.roll(band, 1))
        last = -10 ** 9
        for i in np.flatnonzero(trig):
            if i < 50 or i > n - maxh - 2 or i - last < maxh: continue
            last = i
            st = band[i] - katr * a[i] if katr < 90 else C[i] * 0.01
            t1 = ema[i]
            t2 = upper[i] if taper else ema[i]
            r = play(C, H, L, i, st, t1, t2, maxh, rungs, weights)
            if r is None: continue
            real.append(r[0]); dep.append(r[1])
            q = int(RNG.integers(max(50, i-500), min(n-maxh-2, i+500)+1))
            span = C[i] - st
            c = play(C, H, L, q, C[q]-span, C[q]+(t1-C[i]), C[q]+(t2-C[i]),
                     maxh, rungs, weights)
            if c: ctrl.append(c[0])
    return np.array(real), np.array(ctrl), np.array(dep)


if __name__ == "__main__":
    print("KELTNER BAND REVERSION, REBUILT — wider stop + taper + ladder\n")
    print(f"  {'stop':>6}{'hold':>6}{'exit':>8}{'entry':>9}{'n':>7}"
          f"{'net':>10}{'t':>8}{'ctrl':>9}{'EDGE':>9}{'dep':>7}")
    cells = []
    for katr, klab in ((6, "6A"), (8, "8A"), (10, "10A"), (99, "none")):
        for maxh in (120, 240):
            for taper, tlab in ((False, "mid"), (True, "mid+band")):
                for rungs, w, elab in ((1, [1], "single"), (4, [1,2,3,4], "ladder4")):
                    r, c, dp = run(katr, maxh, rungs, w, taper)
                    if len(r) < 100 or len(c) < 100: continue
                    se = np.sqrt(r.std(ddof=1)**2/len(r)+c.std(ddof=1)**2/len(c))
                    edge = r.mean()-c.mean()
                    cells.append((r.mean(), edge, klab, maxh, tlab, elab, r, c))
                    print(f"  {klab:>6}{maxh:>6}{tlab:>8}{elab:>9}{len(r):>7}"
                          f"{r.mean()*100:>+9.3f}%"
                          f"{r.mean()/(r.std(ddof=1)/np.sqrt(len(r))):>+8.2f}"
                          f"{c.mean()*100:>+8.3f}%{edge*100:>+8.3f}%"
                          f"{dp.mean()*100:>6.0f}%")
    pos = sum(1 for x in cells if x[0] > 0)
    bc = sum(1 for x in cells if x[1] > 0)
    print(f"\n  {pos}/{len(cells)} cells net positive · "
          f"{bc}/{len(cells)} beat their control")
    t_req = float(np.sqrt(2*np.log(max(len(cells), 2))))
    b = max(cells, key=lambda x: x[0])
    r = b[6]; t = r.mean()/(r.std(ddof=1)/np.sqrt(len(r)))
    print(f"  corrected t threshold for {len(cells)} cells: {t_req:.2f}")
    print(f"  BEST: stop {b[2]}, hold {b[3]}h, exit {b[4]}, entry {b[5]}")
    print(f"        {r.mean()*100:+.3f}%/trade  t={t:+.2f}  "
          f"{'CLEARS' if t>=t_req else 'below'} the corrected bar")
