"""Binance Vision USD-M futures 1-minute klines WITH taker-buy volume (= order-flow delta).
Monthly zips, 2025-09 .. 2026-10. Writes data_1m_delta/<COIN>.csv with
t, open, high, low, close, vol, taker_buy, delta (= 2*taker_buy - vol). Read-only public archive."""
import io, os, sys, time, zipfile, urllib.request
import pandas as pd
OUT = "/home/claude/qlab/data_1m_delta"; os.makedirs(OUT, exist_ok=True)
COINS = sys.argv[1:] or ["BTC", "ETH", "SOL", "XRP", "DOGE", "LINK"]
MONTHS = pd.period_range("2025-09", "2026-10", freq="M")
COLS = ["t","open","high","low","close","vol","close_time","qvol","n","taker_buy","taker_quote","ignore"]
for c in COINS:
    parts = []
    for m in MONTHS:
        ym = m.strftime("%Y-%m")
        url = f"https://data.binance.vision/data/futures/um/monthly/klines/{c}USDT/1m/{c}USDT-1m-{ym}.zip"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r: b = r.read()
            z = zipfile.ZipFile(io.BytesIO(b)); d = pd.read_csv(z.open(z.namelist()[0]), header=None, names=COLS)
            if str(d.iloc[0, 0]).startswith("open"): d = d.iloc[1:]
            parts.append(d); print(f"  {c} {ym} {len(d):,}", flush=True)
        except Exception as e:
            print(f"  {c} {ym} MISSING ({str(e)[:40]})", flush=True)
        time.sleep(0.2)
    if not parts: continue
    d = pd.concat(parts); d = d[["t","open","high","low","close","vol","taker_buy"]].astype(float)
    d = d.drop_duplicates("t").sort_values("t"); d["delta"] = 2*d.taker_buy - d.vol
    d.to_csv(f"{OUT}/{c}.csv", index=False); print(f"{c}: {len(d):,} minutes -> {OUT}/{c}.csv", flush=True)
