"""
S&P 500 MINUTE DATA FOR CRASH REGIMES — from Dukascopy tick archive.

DK: "You get crashes on the S&P like the tariff and covid crashes. Study them."

The cross-asset finding (doc 35) was that the minute-scale cascade bounce needs
instruments with enough ABSOLUTE minute volatility for the bounce to clear the
spread — SPY's normal 5-minute SD is 0.067%, so a 3% five-minute fall is a
45-sigma event that never happens.

But that is the UNCONDITIONAL volatility. In a crash, index minute volatility
rises by an order of magnitude and the threshold becomes reachable. So the real
question is not "does this work on the S&P" but "does it work on the S&P WHEN
the S&P is behaving like crypto".

Windows fetched (US cash session, 13:00-21:00 UTC):
    COVID            2020-02-24 to 2020-04-03
    Tariff crash     2025-04-02 to 2025-04-15
    Yen carry unwind 2024-08-01 to 2024-08-09
    Volmageddon      2018-02-02 to 2018-02-12
    Calm control     2019-06-03 to 2019-06-14  (so the comparison is like-for-like)

bi5 format: LZMA-compressed, 20 bytes per tick, big-endian:
    uint32 ms offset from the hour · uint32 ask · uint32 bid · float32 ask vol
    · float32 bid vol
Index prices carry 3 decimals, so the integers are divided by 1000.
"""
import io, os, lzma, struct, time, datetime as dt
import urllib.request
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor

BASE = "https://datafeed.dukascopy.com/datafeed"
OUT = "/home/claude/qlab/data_spx"
INSTR = "USA500IDXUSD"
POINT = 1000.0

WINDOWS = {
    "covid":      ("2020-02-24", "2020-04-03"),
    "tariff":     ("2025-04-02", "2025-04-15"),
    "yen_carry":  ("2024-08-01", "2024-08-09"),
    "volmageddon": ("2018-02-02", "2018-02-12"),
    "calm":       ("2019-06-03", "2019-06-14"),
}
HOURS = range(13, 21)          # US cash session in UTC


def fetch_hour(args):
    inst, d, h = args
    url = f"{BASE}/{inst}/{d.year}/{d.month-1:02d}/{d.day:02d}/{h:02d}h_ticks.bi5"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            break
        except Exception as e:
            if "429" in str(e):
                time.sleep(3 + attempt * 4); continue
            if "404" in str(e):
                return None
            time.sleep(2)
    else:
        return None
    if not raw:
        return None
    try:
        data = lzma.LZMADecompressor().decompress(raw)
    except Exception:
        return None
    n = len(data) // 20
    if n == 0:
        return None
    base = np.datetime64(dt.datetime(d.year, d.month, d.day, h))
    arr = np.frombuffer(data[:n*20], dtype=np.dtype([
        ("ms", ">u4"), ("ask", ">u4"), ("bid", ">u4"),
        ("av", ">f4"), ("bv", ">f4")]))
    return pd.DataFrame({
        "ts": base + arr["ms"].astype("timedelta64[ms]"),
        "ask": arr["ask"] / POINT,
        "bid": arr["bid"] / POINT})


def build(label, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    days = [d.date() for d in pd.date_range(s, e) if d.weekday() < 5]
    tasks = [(INSTR, d, h) for d in days for h in HOURS]
    out = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for df in ex.map(fetch_hour, tasks):
            if df is not None and len(df):
                out.append(df)
    if not out:
        print(f"  {label}: no data"); return None
    t = pd.concat(out).sort_values("ts")
    t["mid"] = (t.ask + t.bid) / 2
    t["spread_bp"] = (t.ask - t.bid) / t.mid * 10000
    t = t.set_index("ts")
    m = pd.DataFrame({
        "open": t.mid.resample("1min").first(),
        "high": t.mid.resample("1min").max(),
        "low": t.mid.resample("1min").min(),
        "close": t.mid.resample("1min").last(),
        "ticks": t.mid.resample("1min").count(),
        "spread_bp": t.spread_bp.resample("1min").median(),
    }).dropna(subset=["close"])
    m = m[m.ticks > 0]
    os.makedirs(OUT, exist_ok=True)
    m.to_csv(f"{OUT}/{label}.csv")
    sd5 = (m.close / m.close.shift(5) - 1).std() * 100
    print(f"  {label:12s} {len(m):7d} minutes  {m.index.min().date()} -> "
          f"{m.index.max().date()}  5-min SD {sd5:.3f}%  "
          f"median spread {m.spread_bp.median():.1f}bp", flush=True)
    return m


if __name__ == "__main__":
    print(f"S&P 500 minute bars from Dukascopy tick data ({INSTR})\n")
    for lab, (a, b) in WINDOWS.items():
        build(lab, a, b)
