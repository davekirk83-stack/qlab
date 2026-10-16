"""
THE RANGE BOOK ON INDIVIDUAL STOCKS — 79 names, daily bars, 20+ years.

Identical machinery and accounting to etf_range20.py (doc 133) so the two
results sit side by side: EMA20, 2-ATR Keltner, containment above its own
expanding median, four laddered entries each side, scaled exits, break exit at
the worst tick, both sides, 2bp a side, one row per episode, return on
intended capital.

Three things are reported beyond the headline:
  by sector        does the edge come from everywhere or from one corner?
  by era           2001-2012 vs 2013-2026 - a stock edge that existed only
                   before decimalisation/HFT would be a dead one
  decliners only   the known fallen names. If the book earns on them too the
                   survivorship worry about longs is contained.

A stock gaps on earnings four times a year. The break exit at the worst tick
absorbs the gap honestly, so a stock result that is WORSE than the ETF result
is the expected outcome, and the question is only whether it is still above
zero with a t-stat that survives.
"""
import warnings; warnings.filterwarnings("ignore")
import glob, os
import numpy as np, pandas as pd
import clean_portfolio as CP
import regime_detect as RD
from ingest_stocks import UNIVERSE

CP.MK = 2/10000; CP.TAKER = 3/10000; CP.SLIP = 2/10000
DECLINERS = ["INTC","F","GE","C","BAC","WBA","M","X","AAL","PARA","KSS","VZ","T","HPQ","IBM","CSCO"]

data = {}
for f in sorted(glob.glob("/home/claude/qlab/data_stocks20/*.csv")):
    s = os.path.basename(f)[:-4]
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
    data[s] = d
print(f"{len(data)} stocks, daily bars.\n")

rows = []; per = {}
for s, d in data.items():
    D, ema, lo, hi, a = RD.detectors(d)
    v = pd.Series(D["contain"])
    allow = (v > v.expanding(500).median()).values
    r = CP.episodes(d, allow, ema, lo, hi, a, None, "optimistic", "L", s) + \
        CP.episodes(d, allow, ema, lo, hi, a, None, "optimistic", "S", s)
    S = pd.DataFrame(r, columns=["sym","entry","exit","ret","side"]); S = S[np.isfinite(S.ret)]
    per[s] = S; rows.append(S)
A = pd.concat(rows, ignore_index=True)
A["entry"] = pd.to_datetime(A.entry, utc=True)


def line(lbl, G):
    if len(G) < 20: return
    t = G.ret.mean()/(G.ret.std(ddof=1)/np.sqrt(len(G)))
    L = G[G.side=="L"].ret.mean()*100; Sh = G[G.side=="S"].ret.mean()*100
    print(f"  {lbl:<14}{len(G):>9,}{G.ret.mean()*100:>+10.4f}%{t:>+7.2f}{(G.ret>0).mean()*100:>5.0f}%"
          f"{L:>+9.3f}%{Sh:>+9.3f}%{G.ret.min()*100:>+8.1f}%")

hdr = f"  {'':<14}{'episodes':>9}{'per ep':>11}{'t':>7}{'win':>6}{'long':>10}{'short':>10}{'worst':>9}"
print("BY SECTOR"); print(hdr)
for g, syms in UNIVERSE.items():
    line(g, pd.concat([per[s] for s in syms if s in per], ignore_index=True))
line("ALL STOCKS", A)

print("\nBY ERA"); print(hdr)
line("2001-2012", A[A.entry < "2013-01-01"])
line("2013-2026", A[A.entry >= "2013-01-01"])

print("\nSURVIVORSHIP CHECK"); print(hdr)
line("decliners", pd.concat([per[s] for s in DECLINERS if s in per], ignore_index=True))
line("the rest", pd.concat([per[s] for s in per if s not in DECLINERS], ignore_index=True))

print("\nPER-STOCK SPREAD")
m = A.groupby("sym").ret.mean()*100
print(f"  {len(m)} stocks: {(m>0).mean()*100:.0f}% positive, median {m.median():+.3f}%, "
      f"worst {m.idxmin()} {m.min():+.3f}%, best {m.idxmax()} {m.max():+.3f}%")

print("\nCOMPARISON  (same accounting)")
print("  ETFs, doc 133:            +0.28% an episode")
print("  crypto 15m, doc 123:      +0.11% an episode")
for lev in (1, 2):
    r, tk, sk = CP.simulate(A, 20, lev)
    if r: print(f"  stocks equity {lev}x, 20 slots: CAGR {r['cagr']*100:5.1f}%  maxDD {r['dd']*100:5.1f}%  Sharpe {r['sharpe']:4.2f}  {tk:,} taken")
