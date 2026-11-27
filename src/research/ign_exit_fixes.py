"""
DK 27 Nov (winning trades that ended small / lost). Live Ignition/AD NQ: winners kept ~41% of their best open profit and price kept going
after 3 of 4 profitable exits (+217, +71, +85 pts in the next 2h). Exits now: breakeven at +15 pts, then a 1-ATR trail, target 9 ATR, cap 36 bars.
Tests breakeven trigger and trail width on the whole NQ 5-min history (paperbook7 replay, its costs), v1.1 (live) and all-hours variants.
"""
import os, sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("QLAB_ROOT", os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
import paperbook7 as P7

bars = pd.read_csv(f"{os.environ['QLAB_ROOT']}/data_nq_cache/nq_5m.csv", index_col=0); bars.index = pd.to_datetime(bars.index, utc=True)
d = P7.features(bars); start = str(d.index[300].date())
print("NQ bars", d.index[0], "->", d.index[-1])
rows = []
for be, tr, cap in itertools.product((15, 30, 45, 1e9), (1.0, 1.5, 2.0, 3.0), (36, 72)):
    P7.BE, P7.TRAIL_ATR, P7.CAP = be, tr, cap
    for lab, kw in (("v1.1 US hours", dict(us_hours=True, v11=True)), ("all hours", dict())):
        t, _, _ = P7.replay(d, start, 0, **kw); t = pd.DataFrame(t)
        if t.empty: continue
        h = len(t) // 2
        rows.append(dict(variant=lab, be=("none" if be > 1e8 else be), trail_atr=tr, cap=cap, n=len(t), win=(t.pts > 0).mean(), mean=t.pts.mean(),
                         h1=t.pts[:h].mean(), h2=t.pts[h:].mean(), total=t.pts.sum(), worst_dd=(t.pts.cumsum() - t.pts.cumsum().cummax()).min()))
r = pd.DataFrame(rows); os.makedirs("runs/research", exist_ok=True); r.to_csv("runs/research/ign_exit_fixes.csv", index=False)
pd.set_option("display.width", 250)
for lab, g in r.groupby("variant"): print("\n==", lab); print(g.sort_values("mean", ascending=False).round(2).to_string(index=False))
