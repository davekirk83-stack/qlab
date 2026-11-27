"""Doc 277 (independent checker, 27 Nov: intraday NQ tests used only ~13 months; years more exist): Dukascopy USATECHIDXUSD ticks for one
year -> 5-minute bars in exactly the format of data_nq_cache/nq_5m.csv (open/high/low/close mid, vol = tick count, delta = tick-rule
up - down ticks, spread = mean ask-bid), so every NQ research script can run on the long history. Data only. Usage: python nq_history_5m.py YEAR"""
import sys, os, numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["NQ_TICK_OUT"] = f"/tmp/nqticks_{sys.argv[1]}"
import get_nq_ticks as G
Y = int(sys.argv[1]); G.OUT = f"/tmp/nqticks_{Y}"; os.makedirs(f"{G.OUT}/days", exist_ok=True)
out = []; last = 0.0
for m in range(1, 13):
    days = [x.date() for x in pd.date_range(f"{Y}-{m:02d}-01", pd.Timestamp(f"{Y}-{m:02d}-01") + pd.offsets.MonthEnd(0)) if x.weekday() != 5]
    days = [d for d in days if pd.Timestamp(d) <= pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta("2D")]
    if not days: break
    with ThreadPoolExecutor(max_workers=12) as ex: fs = list(ex.map(G.fetch_day, days))
    parts = [pd.read_csv(f) for f in fs]; t = pd.concat([p for p in parts if len(p)])
    if t.empty: continue
    t["ts"] = pd.to_datetime(t.ts, utc=True); t = t.sort_values("ts"); t["mid"] = (t.ask + t.bid) / 2
    d = np.sign(t.mid.diff().fillna(0).values)
    if len(d) and d[0] == 0: d[0] = last
    for i in range(1, len(d)):
        if d[i] == 0: d[i] = d[i - 1]
    last = d[-1] if len(d) else last
    t["sgn"] = d; t = t.set_index("ts"); r = t.mid.resample("5min")
    b = pd.DataFrame({"open": r.first(), "high": r.max(), "low": r.min(), "close": r.last(), "vol": r.count(),
                      "delta": (t.sgn > 0).resample("5min").sum() - (t.sgn < 0).resample("5min").sum(),
                      "spread": (t.ask - t.bid).resample("5min").mean()}).dropna(subset=["close"])
    out.append(b); print(Y, m, len(t), "ticks ->", len(b), "bars", flush=True)
    for f in fs: os.remove(f)
B = pd.concat(out); B.index.name = "ts"; os.makedirs("data_nq_cache", exist_ok=True)
B.to_csv(f"data_nq_cache/nq_5m_{Y}.csv.gz", compression="gzip"); print("wrote", len(B), "bars", B.index[0], B.index[-1])
