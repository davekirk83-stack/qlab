"""Doc 172: Dukascopy ticks -> 5-minute bars WITH a tick-rule delta (same construction as data_nq: sign of the mid change, a zero change
carries the previous sign; delta = up-ticks - down-ticks), for testing Ignition on other IG indices.
Usage: pull_duka_delta.py INSTR POINT START END WORKERS. Per-day checkpoints in data_ign/<INSTR>/days/; output data_ign/<INSTR>_5m.csv."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab-git/src"); import get_nq_ticks as G
from concurrent.futures import ThreadPoolExecutor
instr, point, start, end, nw = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])
G.INSTR, G.POINT = instr, point
D = f"/home/claude/qlab/data_ign/{instr}/days"; os.makedirs(D, exist_ok=True)
def day(d):
    f = f"{D}/{d}.csv"
    if os.path.exists(f): return f
    parts = [p for p in map(G.fetch_hour, [(d, h) for h in range(24)]) if p is not None]
    if not parts: open(f, "w").write("ts,open,high,low,close,vol,delta,spread\n"); return f
    t = pd.concat(parts).sort_values("ts"); t["mid"] = (t.ask + t.bid) / 2
    sg = np.sign(t.mid.diff().fillna(0).values)
    for i in range(1, len(sg)):
        if sg[i] == 0: sg[i] = sg[i - 1]
    t["sg"] = sg; t = t.set_index("ts"); r = lambda x: x.resample("5min")
    b = pd.DataFrame({"open": r(t.mid).first(), "high": r(t.mid).max(), "low": r(t.mid).min(), "close": r(t.mid).last(), "vol": r(t.mid).count(),
                      "delta": r(t.sg > 0).sum() - r(t.sg < 0).sum(), "spread": r(t.ask - t.bid).mean()}).dropna(subset=["close"])
    b.index.name = "ts"; b.to_csv(f + ".tmp"); os.replace(f + ".tmp", f); return f
days = [x.date() for x in pd.date_range(start, end) if x.weekday() != 5]
with ThreadPoolExecutor(nw) as ex:
    for i, f in enumerate(ex.map(day, days)):
        if i % 10 == 9: print(f"  {instr} {i+1}/{len(days)} days", flush=True)
b = pd.concat([pd.read_csv(f"{D}/{d}.csv", index_col=0, parse_dates=True) for d in days]); b = b[~b.index.duplicated()].sort_index()
b.index = pd.to_datetime(b.index, utc=True); b.to_csv(f"/home/claude/qlab/data_ign/{instr}_5m.csv"); print(instr, "done", len(b), b.index.min(), b.index.max(), "median close", b.close.median(), flush=True)
