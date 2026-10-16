"""Twenty years of daily bars from Yahoo for the ETF universe - the episode
count a daily-bar test of the range book actually needs (doc 132).
Read-only public data. CAP-021: no account, no credential, no order."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, time, json, urllib.request
import pandas as pd
sys.path.insert(0, "/home/claude/qlab/src")
from ingest_etf import UNIVERSE
OUT = "/home/claude/qlab/data_etf20"

def fetch(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=25y"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
            j = json.load(r)
        res = j["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        d = pd.DataFrame({"open": q["open"], "high": q["high"], "low": q["low"],
                          "close": q["close"], "volume": q["volume"]},
                         index=pd.to_datetime(res["timestamp"], unit="s", utc=True))
        return d.dropna(subset=["close"]).astype(float)
    except Exception as e:
        return None

os.makedirs(OUT, exist_ok=True)
for i, sym in enumerate(UNIVERSE, 1):
    p = f"{OUT}/{sym}.csv"
    if os.path.exists(p) and len(pd.read_csv(p)) > 1000:
        print(f"  [{i}/{len(UNIVERSE)}] {sym:<6} have it", flush=True); continue
    d = fetch(sym); time.sleep(0.4)
    if d is None or len(d) < 500:
        print(f"  [{i}/{len(UNIVERSE)}] {sym:<6} too little", flush=True); continue
    d.to_csv(p)
    print(f"  [{i}/{len(UNIVERSE)}] {sym:<6} {len(d):>6,} days  {(d.index[-1]-d.index[0]).days/365.25:>4.1f}y  from {str(d.index[0])[:10]}", flush=True)
