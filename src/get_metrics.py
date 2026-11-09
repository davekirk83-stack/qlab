"""Binance USD-M futures 5-min metrics (open interest, long/short ratios) daily archives -> data_long/metrics/BTCUSDT_metrics.parquet"""
import os, sys, io, zipfile, time, urllib.request, pandas as pd
from concurrent.futures import ThreadPoolExecutor
SYM = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"; OUT = "/home/claude/qlab-git/data_long/metrics"
def get(d):
    f = f"{OUT}/{SYM}_{d}.csv"
    if os.path.exists(f): return f
    u = f"https://data.binance.vision/data/futures/um/daily/metrics/{SYM}/{SYM}-metrics-{d}.zip"
    for a in range(4):
        try:
            z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()))
            open(f, "wb").write(z.read(z.namelist()[0])); return f
        except Exception as e:
            if "404" in str(e): return None
            time.sleep(3 * (a + 1))
    return None
days = [str(x.date()) for x in pd.date_range("2021-12-01", "2026-11-07")]
with ThreadPoolExecutor(8) as ex: fs = [f for f in ex.map(get, days) if f]
m = pd.concat([pd.read_csv(f) for f in fs]); m["t"] = pd.to_datetime(m.create_time, utc=True); m = m.drop_duplicates("t").set_index("t").sort_index()
m.to_parquet(f"{OUT}/{SYM}_metrics.parquet"); print(SYM, len(fs), "days", m.index[0], m.index[-1])
for f in fs: os.remove(f)
