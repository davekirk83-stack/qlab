"""
THE TWO-STAGE SWITCH, and the hold cap that was cutting windows short.

Two things fell out of the anatomy that neither test was built to find.

ONE. The windows are far longer than the book's hold limit. Median window is
63 bars - nearly 16 hours - and the book force-exits everything at 48 bars.
It is being marched out of ranges that are still open and still paying. And
the longer windows are the better ones: over 24 hours they average +3.98%
against +0.39% for the shortest. So the cap is sweeping against the grain.
Caps of 48, 96, 192 and none are tested here.

TWO. Containment finds a range, but it does not say whether the range will
pay. Inside the windows, what separated the profitable ones from the losing
ones was not containment (+5 percentile points) - it was efficiency (+10) and
ADX (+8), the two TREND instruments. Read plainly: containment says price is
behaving itself inside the bands; efficiency and ADX say there is no
directional pressure building underneath. You want both. A range with a trend
forming under it is the one that breaks on you.

So the switch becomes two stages, and the test is whether the second stage
pays for the trades it refuses:

  stage 1  containment above its own median        - a range exists
  stage 2  efficiency AND ADX above their medians  - nothing is pushing

Tested against containment alone and against each single instrument, at each
hold cap. Judged on per-trade return, on the worst single trade, and on total
P&L - because a filter that doubles the per-trade number by refusing nine
trades in ten has not improved anything.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import regime_detect as RD

NAMES = ["contain", "eff", "adx"]


def build(data):
    out = {}
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        flags = {}
        for nm in NAMES:
            v = pd.Series(D[nm])
            flags[nm] = (v > v.expanding(500).median()).values
        out[s] = (d, flags, ema, lo_b, hi_b, a)
    return out


def rule(flags, which):
    f = np.ones(len(flags["contain"]), dtype=bool)
    for nm in which: f &= flags[nm]
    return f


if __name__ == "__main__":
    data = RD.load()
    P = build(data)
    print(f"{len(data)} symbols, 15-minute bars.\n")
    print("THE HOLD CAP — the book force-exits at 48 bars, the median window "
          "runs 63.\n")
    print(f"  {'switch':<28}{'cap':>6}{'trades':>9}{'per trade':>12}{'t':>8}"
          f"{'win':>6}{'worst':>9}{'total P&L':>12}")
    results = []
    for which, lbl in ((("contain",), "contain only"),
                       (("eff",), "efficiency only"),
                       (("adx",), "ADX only"),
                       (("contain", "eff"), "contain + efficiency"),
                       (("contain", "adx"), "contain + ADX"),
                       (("contain", "eff", "adx"), "all three")):
        for cap in (48, 96, 192, 10**6):
            RD.CAP = cap
            res = []
            for s, (d, flags, ema, lo_b, hi_b, a) in P.items():
                res += RD.run_book(d, rule(flags, which), ema, lo_b, hi_b, a)
            if len(res) < 200: continue
            r = np.array(res)
            t = r.mean()/(r.std(ddof=1)/np.sqrt(len(r)))
            capl = "none" if cap > 10**5 else str(cap)
            print(f"  {lbl:<28}{capl:>6}{len(r):>9}{r.mean()*100:>+11.4f}%"
                  f"{t:>+8.2f}{(r>0).mean()*100:>5.0f}%{r.min()*100:>+8.1f}%"
                  f"{r.sum()*100:>+11.0f}%")
            results.append((lbl, capl, len(r), r.mean(), t, r.min(), r.sum()))
    print("\n  'total P&L' is the column that stops a filter looking good purely")
    print("  by refusing trades. A switch has to grow the pot, not just the average.")
    if results:
        best = max(results, key=lambda z: z[6])
        print(f"\n  MOST TOTAL P&L: {best[0]}, cap {best[1]} — {best[2]:,} trades, "
              f"{best[3]*100:+.4f}% each, worst {best[5]*100:+.1f}%")
        bq = max(results, key=lambda z: z[3])
        print(f"  BEST PER TRADE: {bq[0]}, cap {bq[1]} — {bq[2]:,} trades, "
              f"{bq[3]*100:+.4f}% each, worst {bq[5]*100:+.1f}%")
