"""
FUNDING HISTORY FROM HYPERLIQUID — the raw material for a carry book.

Doc 32 tested funding carry on 8-HOURLY settlement, which is what most venues
use, and it did not survive costs. Hyperliquid settles HOURLY. That is not a
parameter change, it is eight times the collection frequency, and it was never
tested.

Read-only public market data. CAP-021: no account, no credential, no order.
"""
import warnings; warnings.filterwarnings("ignore")
import json, time, os, urllib.request
import pandas as pd

API = "https://api.hyperliquid.xyz/info"
OUT = "/home/claude/qlab/data_funding"


def post(body, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(
                API, data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json",
                         "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(1.2*(k+1))
    return None


def universe():
    m = post({"type": "meta"})
    if not m: return []
    return [(u["name"], bool(u.get("isDelisted"))) for u in m.get("universe", [])]


def funding(coin, days=400):
    """Hourly funding, walked back in chunks (the endpoint caps a response)."""
    end = int(time.time()*1000)
    start = end - days*86400*1000
    rows = []; t = start
    while t < end:
        r = post({"type": "fundingHistory", "coin": coin, "startTime": t})
        if not r: break
        rows.extend(r)
        last = max(x["time"] for x in r)
        if last <= t: break
        t = last + 1
        time.sleep(0.08)
        if len(rows) > 60000: break
    if not rows: return None
    d = pd.DataFrame(rows).drop_duplicates(subset="time")
    d["ts"] = pd.to_datetime(d.time, unit="ms", utc=True)
    d["fundingRate"] = pd.to_numeric(d.fundingRate, errors="coerce")
    d["premium"] = pd.to_numeric(d.premium, errors="coerce")
    return d.set_index("ts")[["fundingRate", "premium"]].sort_index()


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    uni = universe()
    live = [c for c, dead in uni if not dead]
    print(f"{len(uni)} perps, {len(live)} live\n", flush=True)
    import sys
    want = live[:int(sys.argv[1])] if len(sys.argv) > 1 else live[:40]
    for i, c in enumerate(want, 1):
        p = f"{OUT}/{c}.csv"
        if os.path.exists(p):
            print(f"  [{i}/{len(want)}] {c:<10} have it", flush=True); continue
        d = funding(c)
        if d is None or len(d) < 2000:
            print(f"  [{i}/{len(want)}] {c:<10} too little "
                  f"({0 if d is None else len(d)})", flush=True); continue
        d.to_csv(p)
        ann = d.fundingRate.mean()*24*365*100
        print(f"  [{i}/{len(want)}] {c:<10} {len(d):>6,} hrs  "
              f"{str(d.index[0])[:10]}  mean {ann:+.1f}%/yr", flush=True)
