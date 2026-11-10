"""Doc 218 — Claude's own candidates (DK 10:51 "If you could create a new book of your own..."). All through src/standard_test.py.
1 RSI(4) by VIX band at the signal (a SIZING question, not a new book): is the edge per trade bigger when VIX is high?
2 Bear-market dip: RSI(4) < 20 BELOW the 200-day, exit RSI(4) > 50 or 5 days, stop 2 ATR, next-open in/out.
3 Pre-FOMC drift (Lucca & Moench 2015): buy US indices at the close 2 days before a scheduled decision day... here: at the close of the day
  before, sell at the close of the decision day (known in advance; 214 scheduled dates 2000-26, runs/fomc_dates.txt).
4 Gold flight to safety: US 500 falls >= 2% on the day -> buy gold at the next open, hold 3 days (exit next open), stop 2 ATR."""
import warnings; warnings.filterwarnings("ignore")
import os, re, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, review2_fixes as RF, std_books as B, standard_test as S
IX8, US = F.IXG, ["SPX", "NDX", "DJI", "RUT"]
up = B.up; r4 = B.r4; vix = F.D["VIX"].close
fomc = pd.to_datetime([m.group(0) for x in open("runs/fomc_dates.txt") if not x.startswith("#") and "(U)" not in x for m in [re.search(r"\d{4}-\d{2}-\d{2}", x)] if m])
def bear(cm=1.0, rnd=None):
    with B.cost(cm): return B.mk([(t, R, k) for k in IX8 for t, R in RF.run_o(k, (rnd or (lambda k, e: e))(k, ~up(F.D[k]) & (r4(F.D[k]) < 20)), r4(F.D[k]) > 50, 5, 2.0)])
def prefomc(cm=1.0, rnd=None):
    rows = []
    with B.cost(cm):
        for k in US:
            d = F.D[k]; pos = d.index.get_indexer(fomc); pos = pos[pos > 0]
            e = pd.Series(False, index=d.index); e.iloc[pos - 1] = True          # close of the day before the decision day
            rows += [(t, R, k) for t, R in F.run(k, (rnd or (lambda k, e: e))(k, e), 1, None, 1, stop=3.0)]
    return B.mk(rows)
def goldsafe(cm=1.0, rnd=None):
    s = F.D["SPX"]; drop = (s.close / s.close.shift(1) - 1 <= -0.02)
    with B.cost(cm): return B.mk([(t, R, "GOLD") for t, R in RF.run_o("GOLD", (rnd or (lambda k, e: e))("GOLD", drop.reindex(F.D["GOLD"].index).fillna(False)), None, 3, 2.0)])
if __name__ == "__main__":
    print("== 1. RSI(4) dip: result per trade by VIX at the signal (next-open in/out)")
    t = B.rsi4(); v = vix.shift(0).reindex(t.t.dt.normalize()).ffill().values
    t["band"] = pd.cut(v, [0, 15, 20, 25, 30, 300], labels=["<15", "15-20", "20-25", "25-30", ">30"])
    for b, g in t.groupby("band"):
        y = g.groupby(g.t.dt.year).R.mean(); print(f"   VIX {b:6s} n{len(g):4d} mean {g.R.mean():+.3f} ATR t {g.R.mean() / g.R.std() * np.sqrt(len(g)):+.2f} | years + {(y > 0).sum()}/{len(y)} | worst trade {g.R.min():+.2f}")
    h = t[t.t.dt.year < 2014]; f = t[t.t.dt.year >= 2014]
    for nm, g in (("2000-13", h), ("2014-26", f)):
        print(f"   {nm}: VIX >= 20 {g.R[v[g.index] >= 20].mean():+.3f} (n{(v[g.index] >= 20).sum()}) vs VIX < 20 {g.R[v[g.index] < 20].mean():+.3f} (n{(v[g.index] < 20).sum()})")
    C = B.core(); print()
    S.judge("Bear-market dip: RSI(4)<20 below 200-day, 5 days", "dip-bear", IX8, bear, core=C)
    S.judge("Pre-FOMC drift: US indices, close day before -> close decision day", "calendar-event", US, prefomc, core=C)
    S.judge("Gold flight to safety: US 500 -2% day -> gold 3 days", "cross-asset", ["GOLD"], goldsafe, core=C)
