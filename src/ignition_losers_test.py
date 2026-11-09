"""DK 8 Nov: thesis stops should target Ignition's BIG losers, not cut slow winners. What do the big losers look like at the signal bar?
NQ 5-min, Oct 2025 - Nov 2026 (the cache) and Jan 2020 - Aug 2021 (Dukascopy; tick-rule delta built the same way if available).
Trade features at the signal bar (entry bar - 1): ign (range / prior-20 range), dshare (delta share), signal bar close position,
ATR in points, time of day, gap of entry from EMA. Compare full-stop losers vs the rest; then test the simplest rule the data suggests."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); os.environ["QLAB_ROOT"] = os.getcwd()
import paperbook7 as P7
OUT = open("runs/ignition_losers_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
bars = pd.read_csv("data_nq_cache/nq_5m.csv", index_col=0); bars.index = pd.to_datetime(bars.index, utc=True)
d = P7.features(bars); tr, _, _ = P7.replay(d, "2025-10-20", 0, us_hours=True, v11=True); T = pd.DataFrame(tr)
T["o"] = pd.to_datetime(T.opened, utc=True)
idx = d.index.get_indexer(T.o) - 1   # signal bar
f = d.iloc[idx].reset_index(drop=True)
T["ign"] = f.ign.values; T["dshare"] = f.dshare.values * T.side.values; T["atr"] = f.atr.values
T["cpos"] = np.where(T.side == 1, (f.close - f.low) / (f.high - f.low), (f.high - f.close) / (f.high - f.low))
T["hour"] = T.o.dt.tz_convert("America/New_York").dt.hour; T["big"] = T.pts <= -30
log(f"Ignition v1.1 trades {len(T)}: big losers (<= -30 pts) {int(T.big.sum())}, total {T.pts.sum():+.0f} pts")
for c in ("ign", "dshare", "cpos", "atr", "hour"):
    log(f"  {c:7} big losers median {T[T.big][c].median():7.2f} | others median {T[~T.big][c].median():7.2f}")
log("\nBy signal-bar delta share (in the trade's direction):")
for lab, g in T.groupby(pd.qcut(T.dshare, 3, labels=["weakest third", "middle", "strongest third"])):
    log(f"  {lab:16} n{len(g):3} total {g.pts.sum():+6.0f} mean {g.pts.mean():+5.1f} big losers {int(g.big.sum())}")
log("By signal-bar close position:")
for lab, g in T.groupby(pd.cut(T.cpos, [0, .6, .8, 1.01], labels=["<60%", "60-80%", ">=80%"])):
    log(f"  {lab:16} n{len(g):3} total {g.pts.sum():+6.0f} mean {g.pts.mean():+5.1f} big losers {int(g.big.sum())}")
log("By expansion size (ign):")
for lab, g in T.groupby(pd.qcut(T.ign, 3, labels=["smallest third", "middle", "largest third"])):
    log(f"  {lab:16} n{len(g):3} total {g.pts.sum():+6.0f} mean {g.pts.mean():+5.1f} big losers {int(g.big.sum())}")
