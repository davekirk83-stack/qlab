"""Doc 191 — the chosen CONT engine (from NQ 2020-21 dev) run unchanged on US 500 and FTSE 100 (Nov 2025-Nov 2026): pure out-of-sample."""
import numpy as np, pandas as pd, io, contextlib
src = open("src/spike_engine_iter.py").read().split("for kind, grid in")[0].replace("runs/spike_engine_iter.txt", "runs/spike_cont_other.txt")
with contextlib.redirect_stdout(io.StringIO()): exec(src)
OUT.seek(0); OUT.truncate()
def prep2(d, tz, o, c):
    lt = d.index.tz_convert(tz); mins = lt.hour * 60 + lt.minute
    d = d[(mins >= o) & (mins < c)].copy()
    q = d.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    q["day"] = q.index.tz_convert(tz).date; q["rng"] = q.high - q.low
    dm = q.groupby("day").rng.mean(); q["ref"] = q.day.map(dm.shift(1).rolling(5).mean())
    tp = (q.high + q.low + q.close) / 3; q["vwap"] = tp.groupby(q.day).cumsum() / q.groupby("day").cumcount().add(1)
    q["min"] = q.index.tz_convert(tz).hour * 60 + q.index.tz_convert(tz).minute - o
    return q
for name, f, cost, tz, o, c in (("US 500", "data_ig_cache/USA500IDXUSD_5m.csv", 0.4, "America/New_York", 570, 960), ("FTSE 100", "data_ig_cache/GBRIDXGBP_5m.csv", 1.0, "Europe/London", 480, 990)):
    COST = cost; q = prep2(load(f, "2025-10-15"), tz, o, c)
    with contextlib.redirect_stdout(io.StringIO()): S = study(q, name)
    X = run(q, S, "cont", (0.25, "nextbar", 1.0)); log(f"{name:9} CONT (0.25, next-bar stop, 1x target): {fmt(X)}")
    X = run(q, S, "cont", (0.25, "mid", 1.0)); log(f"{name:9} CONT (0.25, midpoint stop, 1x target): {fmt(X)}")
