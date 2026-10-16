"""
BOUNDING THE LAST SOFT ASSUMPTION — what does chasing cost in price?

Doc 121 measured the chase fill RATE at 83-98%, so that number is no longer a
guess. What remains unmeasured is the chase fill PRICE. The model charges a
flat 0.05 ATR premium for filling at the touch rather than at the deep ladder
rung it was aiming for, and 0.05 was chosen because one tick inside the best
bid is a small fraction of an ATR. Reasonable, but asserted.

It matters because it is the last thing standing between doc 120's 24.8% CAGR
and the 1.5% floor. An earlier sweep in chase.py covered 0.05 to 0.40 ATR but
ran on the accounting doc 119 later found to be broken - returns were not
size-weighted and a poor fill bought a cheaper entry - so those numbers are
void.

This reruns the sweep on the clean portfolio: one position per episode,
size-weighted, each rung attempted once, unfilled size lost.

WHAT A LARGE PREMIUM MEANS physically. The ladder's deepest rung sits 0.55 ATR
below the band. A chase order that fills 0.40 ATR above its target has given
up most of the depth the ladder existed to capture - at that point it is
simply a market order wearing a limit order's clothes, and the laddering
work becomes pointless. So the sweep also answers whether the ladder survives
being chased, not only whether the book does.

Reported as CAGR, drawdown and Sharpe at 1x and 3x, against the queued floor
and the optimistic ceiling, so the whole range is visible at once.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import clean_portfolio as CP
import regime_detect as RD


if __name__ == "__main__":
    depth = CP.load_depth()
    data = RD.load()
    common = sorted([s for s in data if s in depth])
    P = {}
    for s in common:
        d = data[s]
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        P[s] = (d, (v > v.expanding(500).median()).values, ema, lo_b, hi_b, a)
    print(f"{len(common)} symbols, $2,000, 40 slots, both sides, one position")
    print("per episode. The ladder's deepest rung is 0.55 ATR below the band —")
    print("a chase filling 0.40 above its target has surrendered most of that.\n")
    print(f"  {'fill regime':<38}{'per ep':>10}{'CAGR 1x':>10}{'maxDD':>9}"
          f"{'Sharpe':>8}{'CAGR 3x':>10}{'maxDD':>9}{'final 3x':>11}")

    def row(mode, prem, lbl):
        CP.PREM = prem
        rows = []
        for s in common:
            d, al, ema, lo_b, hi_b, a = P[s]
            rows += CP.episodes(d, al, ema, lo_b, hi_b, a, depth.get(s), mode, "L", s)
            rows += CP.episodes(d, al, ema, lo_b, hi_b, a, depth.get(s), mode, "S", s)
        S = pd.DataFrame(rows, columns=["sym", "entry", "exit", "ret", "side"])
        S = S[np.isfinite(S.ret)]
        if len(S) < 100: return None
        r1, _, _ = CP.simulate(S, 40, 1)
        r3, _, _ = CP.simulate(S, 40, 3)
        if r1 is None: return None
        c3 = f"{r3['cagr']*100:.1f}%" if r3 else "wiped"
        d3 = f"{r3['dd']*100:.1f}%" if r3 else "-"
        f3 = f"{r3['final']:,.0f}" if r3 else "0"
        print(f"  {lbl:<38}{S.ret.mean()*100:>+9.4f}%{r1['cagr']*100:>9.1f}%"
              f"{r1['dd']*100:>8.1f}%{r1['sharpe']:>8.2f}{c3:>10}{d3:>9}{f3:>11}")
        return r1["cagr"]

    opt = row("optimistic", 0.0, "ceiling: every touched rung fills")
    for prem in (0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.55):
        row("chase", prem, f"chase, +{prem:.2f} ATR worse entry")
    flo = row("queued", 0.0, "floor: resting bids must queue")

    print("\n  The book is somewhere on this ladder, and which rung depends only")
    print("  on how much worse a touch fill is than the rung it replaced.")
    if opt is not None and flo is not None:
        print(f"  Ceiling {opt*100:.1f}% CAGR, floor {flo*100:.1f}%. Anything in")
        print("  between is an execution-quality question, not a strategy question.")
