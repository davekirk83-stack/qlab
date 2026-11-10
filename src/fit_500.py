"""Doc 213 — can the skipped trades run inside £500 at 2% (£10 risk, IG minimum 0.01/pt)? (DK 10 Nov 08:12)
A: tighter stops (US Tech 100 1 ATR ~ 617 pts -> 0.01/pt risks £6 per ATR; Wall St ~664). B: take the US Tech 100 / Wall St signal on the US 500."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refine_nearmiss as R, fifty_ideas as F, review_ideas_test as V
R.NTRIED = 276; from statistics import NormalDist; R.TSTAR = NormalDist().inv_cdf(1 - (1 - (1 - 0.05) ** (1 / R.NTRIED)) / 2)
up = R.up; r4 = lambda d: F.rsi(d.close, 4)
rsi4 = lambda st: (lambda d: (up(d) & (r4(d) < 25), r4(d) > 55, 10, st))
tom = lambda st: (lambda d: (V.tom(d), None, 3, st))
def proxy(src):   # signal and exit from src index, trade on SPX
    def f(d):
        s = F.D[src]; e = (up(s) & (r4(s) < 25)).reindex(d.index).fillna(False); x = (r4(s) > 55).reindex(d.index).fillna(False)
        own = (up(d) & (r4(d) < 25))
        return (e & ~own, x, 10, 3.0)   # only days the US 500 itself has no signal (the extra trades)
    return f
if __name__ == "__main__":
    print(f"t* = {R.TSTAR:.2f}")
    for st in (3.0, 2.0, 1.5, 1.0): R.report(f"RSI4 US Tech 100 + Wall St, stop {st} ATR", "run", ["NDX", "DJI"], rsi4(st))
    for st in (5.0, 2.0, 1.5): R.report(f"TOM US Tech 100 + Wall St, stop {st} ATR", "run", ["NDX", "DJI"], tom(st))
    R.report("US Tech 100 RSI4 signal traded on US 500 (extra days only)", "run", ["SPX"], proxy("NDX"))
    R.report("Wall St RSI4 signal traded on US 500 (extra days only)", "run", ["SPX"], proxy("DJI"))
