"""Binance Vision futures-metrics ingest: open interest, trader positioning, taker flow.
Public archive (data.binance.vision) — the REST API is geo-blocked but the archive is not.
15-minute resolution, one zip per symbol per day."""
import sys, os, io, zipfile, urllib.request, datetime as dt, pandas as pd

BASE = "https://data.binance.vision/data/futures/um/daily/metrics"
OUT = "/home/claude/qlab/data_oi"

def fetch_day(sym, day):
    url = f"{BASE}/{sym}/{sym}-metrics-{day}.zip"
    try:
        with urllib.request.urlopen(url, timeout=45) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
            return pd.read_csv(z.open(z.namelist()[0]))
    except Exception:
        return None

def build(sym, days=400):
    rows, got, miss = [], 0, 0
    today = dt.date.today()
    for i in range(2, days + 2):
        d = (today - dt.timedelta(days=i)).isoformat()
        df = fetch_day(sym, d)
        if df is None:
            miss += 1
            if miss > 25 and got == 0: break
            continue
        rows.append(df); got += 1
    if not rows: return None
    out = pd.concat(rows, ignore_index=True)
    out["create_time"] = pd.to_datetime(out["create_time"])
    out = out.sort_values("create_time").drop_duplicates("create_time")
    p = f"{OUT}/{sym}.csv"; out.to_csv(p, index=False)
    print(f"{sym}: {len(out)} rows ({got} days) {out.create_time.min()} -> {out.create_time.max()}", flush=True)
    return p

if __name__ == "__main__":
    for s in sys.argv[1:]:
        build(s)
