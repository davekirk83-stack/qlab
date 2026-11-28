"""Doc 284 backup for nq_history_5m.py (half-year jobs risk GitHub's 6h limit and save nothing): ONE MONTH of Dukascopy USATECHIDXUSD
ticks fetched in memory (no per-day tick CSVs) -> 5-min bars in the nq_5m.csv format (mid OHLC, vol = ticks, delta = tick rule, spread).
Usage: python nq_month_5m.py YYYY MM  -> data_nq_cache/nq_5m_YYYY_MM.csv.gz"""
import sys, os, numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("NQ_TICK_OUT", "/tmp/nqt")
import get_nq_ticks as G
Y, M = int(sys.argv[1]), int(sys.argv[2])
days = [x.date() for x in pd.date_range(f"{Y}-{M:02d}-01", pd.Timestamp(f"{Y}-{M:02d}-01") + pd.offsets.MonthEnd(0)) if x.weekday() != 5]
with ThreadPoolExecutor(max_workers=24) as ex: parts = [p for p in ex.map(G.fetch_hour, [(d, h) for d in days for h in range(24)]) if p is not None]
t = pd.concat(parts).sort_values("ts"); t["ts"] = pd.to_datetime(t.ts, utc=True); t["mid"] = (t.ask + t.bid) / 2
sg = pd.Series(np.sign(t.mid.diff().fillna(0).values)).replace(0, np.nan).ffill().fillna(0).values
t["sgn"] = sg; t = t.set_index("ts"); r = t.mid.resample("5min")
b = pd.DataFrame({"open": r.first(), "high": r.max(), "low": r.min(), "close": r.last(), "vol": r.count(),
                  "delta": (t.sgn > 0).resample("5min").sum() - (t.sgn < 0).resample("5min").sum(), "spread": (t.ask - t.bid).resample("5min").mean()}).dropna(subset=["close"])
b.index.name = "ts"; os.makedirs("data_nq_cache", exist_ok=True); b.to_csv(f"data_nq_cache/nq_5m_{Y}_{M:02d}.csv.gz", compression="gzip"); print("wrote", Y, M, len(t), "ticks", len(b), "bars")
