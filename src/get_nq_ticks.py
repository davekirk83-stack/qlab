"""Dukascopy USATECHIDXUSD (Nasdaq-100 CFD) ticks -> 1-minute bars with a tick-rule delta.
Window = AuclairsDad's three months (2026-07-15 .. 2026-10-17), ALL hours (the overnight
Globex session is the point). Tick rule: an uptick is a buy, a downtick a sell, unchanged
inherits the last sign - the standard stand-in when aggressor side is not recorded.
Writes data_nq/nq_1m.csv: open, high, low, close (mid), n_ticks, up, down, delta, spread."""
import lzma, time, datetime as dt, urllib.request, os
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
BASE = "https://datafeed.dukascopy.com/datafeed"; INSTR = "USATECHIDXUSD"; POINT = 1000.0
OUT = "/home/claude/qlab/data_nq"; os.makedirs(OUT, exist_ok=True)
START, END = "2026-07-15", "2026-10-17"

def fetch_hour(args):
    d, h = args
    url = f"{BASE}/{INSTR}/{d.year}/{d.month-1:02d}/{d.day:02d}/{h:02d}h_ticks.bi5"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r: raw = r.read()
            break
        except Exception as e:
            if "404" in str(e): return None
            time.sleep(2 + attempt*3)
    else: return None
    if not raw: return None
    try: data = lzma.LZMADecompressor().decompress(raw)
    except Exception: return None
    n = len(data)//20
    if n == 0: return None
    arr = np.frombuffer(data[:n*20], dtype=np.dtype([("ms", ">u4"), ("ask", ">u4"), ("bid", ">u4"), ("av", ">f4"), ("bv", ">f4")]))
    base = np.datetime64(dt.datetime(d.year, d.month, d.day, h))
    return pd.DataFrame({"ts": base + arr["ms"].astype("timedelta64[ms]"), "ask": arr["ask"]/POINT, "bid": arr["bid"]/POINT})

if __name__ == "__main__":
    days = [x.date() for x in pd.date_range(START, END)]
    tasks = [(d, h) for d in days for h in range(24)]
    parts = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, df in enumerate(ex.map(fetch_hour, tasks)):
            if df is not None: parts.append(df)
            if i % 240 == 239: print(f"  {i+1}/{len(tasks)} hours, {sum(len(p) for p in parts):,} ticks", flush=True)
    t = pd.concat(parts).sort_values("ts"); t["mid"] = (t.ask + t.bid)/2
    sgn = np.sign(t.mid.diff().fillna(0).values)
    for i in range(1, len(sgn)):
        if sgn[i] == 0: sgn[i] = sgn[i-1]
    t["sgn"] = sgn; t = t.set_index("ts")
    b = pd.DataFrame({"open": t.mid.resample("1min").first(), "high": t.mid.resample("1min").max(),
                      "low": t.mid.resample("1min").min(), "close": t.mid.resample("1min").last(),
                      "n_ticks": t.mid.resample("1min").count(),
                      "up": (t.sgn > 0).resample("1min").sum(), "down": (t.sgn < 0).resample("1min").sum(),
                      "spread": (t.ask - t.bid).resample("1min").mean()}).dropna(subset=["close"])
    b["delta"] = b.up - b.down
    b.to_csv(f"{OUT}/nq_1m.csv"); print(f"{len(t):,} ticks -> {len(b):,} minutes, {b.index.min()} .. {b.index.max()} -> {OUT}/nq_1m.csv")
