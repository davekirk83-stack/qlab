"""After a losing episode on a coin, should the book leave that coin alone?
DK: "Do we then leave that instrument for a 24-48 hour period to reassess?"
Registered range book, optimistic fills. For every episode, the gap in hours
since the previous episode on the same coin ended, and whether that previous
one lost (and lost big, < -5% on intended capital). If the 24-48h cooldown is
right, the rows with short gaps after a loss will be the bad ones."""
import warnings; warnings.filterwarnings("ignore")
import os, glob, numpy as np, pandas as pd
import clean_portfolio as CP, regime_detect as RD
from regime_hyst import load
rows = []
for s, d in load().items():
    D, ema, lo, hi, a = RD.detectors(d)
    v = pd.Series(D["contain"]); allow = (v > v.expanding(500).median()).values
    for side in ("L", "S"):
        rows += CP.episodes(d, allow, ema, lo, hi, a, None, "optimistic", side, s)
A = pd.DataFrame(rows, columns=["sym","entry","exit","ret","side"]); A = A[np.isfinite(A.ret)]
A["entry"] = pd.to_datetime(A.entry, utc=True); A["exit"] = pd.to_datetime(A.exit, utc=True)
A = A.sort_values(["sym","entry"])
A["prev_ret"] = A.groupby("sym").ret.shift(); A["prev_exit"] = A.groupby("sym").exit.shift()
A["gap_h"] = (A.entry - A.prev_exit).dt.total_seconds()/3600
A = A.dropna(subset=["prev_ret"])
A["bucket"] = pd.cut(A.gap_h, [-1, 6, 24, 48, 1e9], labels=["<6h","6-24h","24-48h",">48h"])
def tab(lbl, G):
    print(f"\n  {lbl}")
    print(f"  {'gap since prev':<16}{'n':>8}{'per ep':>10}{'t':>7}{'win':>6}{'worst':>8}")
    for b, g in G.groupby("bucket"):
        if len(g) < 100: continue
        t = g.ret.mean()/(g.ret.std(ddof=1)/np.sqrt(len(g)))
        print(f"  {b:<16}{len(g):>8,}{g.ret.mean()*100:>+9.3f}%{t:>+7.1f}{(g.ret>0).mean()*100:>5.0f}%{g.ret.min()*100:>+7.1f}%")
tab("previous episode on this coin WON", A[A.prev_ret > 0])
tab("previous episode LOST", A[A.prev_ret <= 0])
tab("previous episode LOST BIG (< -5%)", A[A.prev_ret < -0.05])
tab("all", A)
