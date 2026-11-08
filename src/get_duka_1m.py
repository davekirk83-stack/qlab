"""Doc 191: Dukascopy daily 1-minute BID+ASK candle files -> 5-minute mid bars (and 1-min kept) for long history.
Usage: python get_duka_1m.py INSTR START END   -> data_long/<INSTR>_1m.csv, <INSTR>_5m.csv  (UTC)"""
import sys, os, lzma, time, urllib.request, datetime as dt, numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
INSTR, START, END = sys.argv[1], sys.argv[2], sys.argv[3]
OUT = "/home/claude/qlab-git/data_long"; os.makedirs(f"{OUT}/{INSTR}", exist_ok=True)
DT = np.dtype([("t", ">u4"), ("o", ">u4"), ("c", ">u4"), ("l", ">u4"), ("h", ">u4"), ("v", ">f4")])
def get(url):
    for a in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r: raw = r.read()
            return np.frombuffer(lzma.LZMADecompressor().decompress(raw), dtype=DT) if raw else None
        except Exception as e:
            if "404" in str(e): return None
            time.sleep(2 + 3 * a)
def day(d):
    f = f"{OUT}/{INSTR}/{d}.npz"
    if os.path.exists(f): return f
    b = get(f"https://datafeed.dukascopy.com/datafeed/{INSTR}/{d.year}/{d.month-1:02d}/{d.day:02d}/BID_candles_min_1.bi5")
    a = get(f"https://datafeed.dukascopy.com/datafeed/{INSTR}/{d.year}/{d.month-1:02d}/{d.day:02d}/ASK_candles_min_1.bi5")
    if b is None or a is None or len(b) != len(a): np.savez(f, x=np.zeros((0, 7))); return f
    x = np.column_stack([b["t"], (b["o"] + a["o"]) / 2, (b["h"] + a["h"]) / 2, (b["l"] + a["l"]) / 2, (b["c"] + a["c"]) / 2, b["v"] + a["v"], a["c"].astype(float) - b["c"]])
    np.savez(f, x=x); return f
days = [x.date() for x in pd.date_range(START, END) if x.weekday() != 5]
with ThreadPoolExecutor(max_workers=int(os.environ.get("W","48"))) as ex: files = list(ex.map(day, days))
fr = []
for d, f in zip(days, files):
    x = np.load(f)["x"]
    if len(x) == 0: continue
    df = pd.DataFrame(x[:, 1:], columns=["open", "high", "low", "close", "vol", "spread"], index=pd.Timestamp(d) + pd.to_timedelta(x[:, 0], unit="s"))
    fr.append(df[df.vol > 0])
m = pd.concat(fr); m.index = m.index.tz_localize("UTC"); m.index.name = "time"
scale = 1000.0 if m.close.median() > 1000 * 100 else 1.0   # integer points
# Dukascopy integer price: divide by 1000 for indices (USATECH 7188069 -> 7188.069)
m[["open", "high", "low", "close", "spread"]] /= 1000.0
m.to_csv(f"{OUT}/{INSTR}_1m.csv")
r = m.resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum", "spread": "mean"}).dropna(subset=["close"])
r.to_csv(f"{OUT}/{INSTR}_5m.csv"); print(INSTR, len(m), "1m rows", r.index[0], r.index[-1], "median close", r.close.median())
