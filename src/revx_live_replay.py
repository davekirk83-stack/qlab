"""Replay check for src/revx_live.py: steps the runner bar by bar through the cached Revolut X candles (dry mode) and compares with
paper book 14 over the same days. Usage: python src/revx_live_replay.py 2026-11-01"""
import os, sys, json, shutil, pandas as pd
sys.argv = [sys.argv[0], "dry"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import revx_live as R, paperbook14 as B
start = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else "2026-11-01", tz="UTC")
out = f"{R.ROOT}/runs/revx_replay"; shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
R.STATE, R.TRADES = f"{out}/state.json", f"{out}/trades.csv"
U = [s for s in json.load(open(f"{R.ROOT}/runs/range_universe.json"))["registered_universe"] if s != "ZECUSD"]
FULL = {s: B.refresh(s) for s in U}
R.time.sleep = lambda x: None
end = min(d.index.max() for d in FULL.values())
json.dump({"start": str(start), "cash0": None, "cash": None, "pos": {}, "orders": [], "cool": {}, "halt": None}, open(R.STATE, "w"))
for t in pd.date_range(start + pd.Timedelta(minutes=15), end + pd.Timedelta(minutes=15), freq="15min"):
    B.refresh = lambda s, t=t: FULL[s][FULL[s].index < t]
    R.now = lambda t=t: t
    R.main()
