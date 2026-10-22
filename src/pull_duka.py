"""Pull Dukascopy ticks -> 5-min bars for IG-tradeable instruments (doc 114). Usage: pull_duka.py INSTR POINT START END"""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src"); import get_nq_ticks as G
from concurrent.futures import ThreadPoolExecutor
instr, point, start, end = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
G.INSTR, G.POINT = instr, point
out = f"/home/claude/qlab/data_ig_cache/{instr}_5m.csv"
have = pd.read_csv(out, index_col=0, parse_dates=True) if os.path.exists(out) else pd.DataFrame()
days = [x.date() for x in pd.date_range(start, end) if x.weekday() != 5]
if len(have): days = [d for d in days if pd.Timestamp(d, tz="UTC") > have.index.max()]
def day(d):
    parts = [p for p in map(G.fetch_hour, [(d, h) for h in range(24)]) if p is not None]
    if not parts: return None
    t = pd.concat(parts).sort_values("ts"); t["mid"] = (t.ask + t.bid)/2; t = t.set_index("ts"); t.index = t.index.tz_localize("UTC")
    return pd.DataFrame({"open": t.mid.resample("5min").first(), "high": t.mid.resample("5min").max(), "low": t.mid.resample("5min").min(), "close": t.mid.resample("5min").last(),
                         "vol": t.mid.resample("5min").count(), "spread": (t.ask - t.bid).resample("5min").mean()}).dropna(subset=["close"])
new = []
def flush():
    global have, new
    if not new: return
    bars = pd.concat(([have] if len(have) else []) + new); bars = bars[~bars.index.duplicated(keep="last")].sort_index(); bars.to_csv(out)
    have, new = bars, []
    print(f"  {instr} saved {len(bars)} bars to {bars.index.max()}", flush=True)
with ThreadPoolExecutor(max_workers=16) as ex:
    for i, b in enumerate(ex.map(day, days)):
        if b is not None: new.append(b)
        if i % 10 == 9: flush()
flush()
print(instr, "done", len(have), have.index.min() if len(have) else None, "->", have.index.max() if len(have) else None)
