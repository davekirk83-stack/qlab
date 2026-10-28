"""Hourly bars (Yahoo, last ~730 days, regular session) for the doc 150 universe. Prices adjusted to the daily file's split basis
by scaling each day's hourly bars to that day's daily close is NOT done; instead entries/exits are measured as ratios within the
hourly series, and daily indicators come from the daily file (both are split-adjusted by Yahoo for the hourly endpoint too)."""
import json, os, time, urllib.request, pandas as pd
from concurrent.futures import ThreadPoolExecutor
OUT = "/home/claude/qlab/data_stk_1h"; os.makedirs(OUT, exist_ok=True)
syms = json.load(open("/home/claude/qlab/data_stk2/hourly_universe.json")) + ["QQQ", "SPY"]
def get(s):
    p = f"{OUT}/{s}.csv"
    if os.path.exists(p): return s, "cached"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=730d&interval=60m&includePrePost=false"
    for k in range(3):
        try:
            j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
            r = j["chart"]["result"][0]; q = r["indicators"]["quote"][0]
            d = pd.DataFrame({"t": pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York"),
                              "open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "volume": q["volume"]}).dropna()
            d.to_csv(p, index=False); return s, len(d)
        except Exception as e:
            err = e; time.sleep(2 * (k + 1))
    return s, f"fail {err}"
with ThreadPoolExecutor(10) as ex: res = list(ex.map(get, syms))
print(sum(1 for _, x in res if not (isinstance(x, str) and x.startswith("fail"))), "ok;", [r for r in res if isinstance(r[1], str) and r[1].startswith("fail")][:10])
