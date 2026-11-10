"""Doc 211 — prior-day close-position fade (from DK's screenshot 10 Nov 07:30, @MrMilkTrading CPI-day rule), tested on ALL days.
Rule: yesterday closed in the top half of its range -> short at yesterday's close, cover at today's close; bottom half -> long. 1-day hold,
stop 2 ATR. Gate checks as doc 208, on the 6 traded markets; costs at the gate rate (0.02%/side indices) and at IG spreads; funding charged."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refine_nearmiss as R, fifty_ideas as F
R.NTRIED = 270; from statistics import NormalDist; R.TSTAR = NormalDist().inv_cdf(1 - (1 - (1 - 0.05) ** (1 / R.NTRIED)) / 2)
TR = ["SPX", "NDX", "DJI", "DAX", "FTSE", "GOLD"]
pos = lambda d: (d.close - d.low) / (d.high - d.low)
def mk(which, band=0.5):
    def f(d):
        p = pos(d)
        e = (p >= band) if which == "short" else (p < 1 - band) if which == "long" else pd.Series(True, index=d.index)
        return e
    return f
def go(kind, mk_, fn, cm=1.0, rnd=None, cost=None):
    out = []
    for k in mk_:
        d = F.D[k]; e = fn(d); e = e if rnd is None else rnd(k, e)
        side = pd.Series(np.where(pos(d) >= 0.5, -1, 1), index=d.index) if kind == "both" else (-1 if kind == "short" else 1)
        old = F.COST[k]; F.COST[k] = (cost[k] if cost else old) * cm
        try: out += F.run(k, e, side, None, 1, stop=2.0)
        finally: F.COST[k] = old
    return pd.DataFrame(out, columns=["t", "R"])
R.go = go
IGC = dict(R.IGC, FTSE=.0001)
if __name__ == "__main__":
    print(f"t* = {R.TSTAR:.2f} ({R.NTRIED} ideas tried)")
    for nm, kind, band in [("both sides, every day", "both", 0.5), ("long only: after a close in the bottom half", "long", 0.5),
                           ("short only: after a close in the top half", "short", 0.5), ("long only: after a close in the bottom 20%", "long", 0.8)]:
        R.report(f"FADE {nm}", kind, TR, mk(kind if kind != "both" else "both", band))
        t = go(kind, TR, mk(kind, band), cost=IGC); print(f"              at IG spreads: mean {t.R.mean():+.3f}  last5y {t.R[t.t.dt.year>=2022].mean():+.3f}")
