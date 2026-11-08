"""Doc 191 — THESIS STOPS for Ignition v1.1 (Koroush's "is my thesis still valid?", DK 7 Nov).
Ignition's thesis: an expansion bar with one-sided delta starts a move. Evidence it's wrong: no follow-through.
Rule TS(k, x): after k bars, if the best favourable excursion is < x * ATR and the bar closes back past the signal bar's midpoint, exit at that close.
Everything else identical to the live engine (stop max(45, 1.5 ATR), BE at +15, 1-ATR trail, 9-ATR target, 36-bar cap, US hours, no 12-15 NY).
NQ 5-min (Dukascopy, with tick-rule delta), dev Oct 2025-Apr 2026 / hold May-Nov 2026."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); os.environ["QLAB_ROOT"] = os.getcwd()
import paperbook7 as P7
OUT = open("runs/thesis_stop_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
bars = pd.read_csv("data_nq_cache/nq_5m.csv", index_col=0); bars.index = pd.to_datetime(bars.index, utc=True)
d = P7.features(bars); base_manage = P7.manage
SPLIT = "2026-05-01"
def make(k, x):
    def manage(O, H, L, C, cost, atr, i, s, n, stop_pts=None):
        r = base_manage(O, H, L, C, cost, atr, i, s, n, stop_pts)
        if r is None or r[1] <= k: return r
        e = O[i+1] + s*cost[i+1]; mid = (H[i] + L[i]) / 2
        best = max(H[i+1:i+k+1]) if s == 1 else min(L[i+1:i+k+1])
        # thesis check at bar i+k close (only if the trade was still open then, which r[1] > k guarantees)
        if s*(best - e) < x*atr[i] and s*(C[i+k] - mid) < 0:
            return s*(C[i+k] - e) - cost[i+1], k, "thesis"
        return r
    return manage
def res(tr):
    T = pd.DataFrame(tr)
    if T.empty: return "none"
    T["o"] = pd.to_datetime(T.opened); out = []
    for seg, msk in (("dev", T.o < pd.Timestamp(SPLIT, tz="UTC")), ("hold", T.o >= pd.Timestamp(SPLIT, tz="UTC"))):
        x = T[msk]; out.append(f"{seg} n{len(x):3} total {x.pts.sum():+7.0f} pts mean {x.pts.mean():+5.1f} avg loss {x.pts[x.pts<0].mean():+5.1f} win {100*(x.pts>0).mean():3.0f}% thesis-exits {(x.how=='thesis').sum()}")
    return " || ".join(out)
log("IGNITION v1.1 with thesis stops — points per trade after spread")
P7.manage = base_manage; tr, _, _ = P7.replay(d, "2025-10-20", 0, us_hours=True, v11=True); log(f"  baseline           {res(tr)}")
for k in (2, 3, 4, 6):
    for x in (0.0, 0.25, 0.5):
        P7.manage = make(k, x); tr, _, _ = P7.replay(d, "2025-10-20", 0, us_hours=True, v11=True)
        log(f"  TS k={k} x={x:4.2f}    {res(tr)}")
P7.manage = base_manage
