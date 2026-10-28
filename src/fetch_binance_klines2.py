import os, io, zipfile, urllib.request, pandas as pd
from concurrent.futures import ThreadPoolExecutor
OUT = "/home/claude/qlab/data_bnb"; import sys; SYM = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
def get(kind, tag):
    base = "https://data.binance.vision/data/" + ("spot" if kind == "spot" else "futures/um")
    per = "daily" if len(tag) == 10 else "monthly"
    url = f"{base}/{per}/klines/{SYM}/15m/{SYM}-15m-{tag}.zip"
    try:
        z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url, timeout=60).read()))
        d = pd.read_csv(z.open(z.namelist()[0]), header=None)
        if not str(d.iloc[0, 0]).isdigit(): d = d.iloc[1:]
        return d.iloc[:, [0, 1, 2, 3, 4, 5, 9]].astype(float)
    except Exception: return None
tags = [f"{y}-{m:02d}" for y in range(2020, 2027) for m in range(1, 13) if (y, m) < (2026, 10)] + [f"2026-10-{d:02d}" for d in range(1, 28)]
for kind in ("spot", "perp"):
    with ThreadPoolExecutor(8) as ex: parts = [p for p in ex.map(lambda t: get(kind, t), tags) if p is not None]
    d = pd.concat(parts); d.columns = ["t", "open", "high", "low", "close", "vol", "takerbuy"]
    d["t"] = pd.to_datetime(d.t.where(d.t < 1e14, d.t / 1000), unit="ms", utc=True)
    d = d.drop_duplicates("t").set_index("t").sort_index(); d.to_csv(f"{OUT}/{SYM}_{kind}_15m.csv"); print(kind, len(d), d.index[0], d.index[-1])
