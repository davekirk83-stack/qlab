"""
FIVE YEARS OF 15-MINUTE BARS — the data every open question is waiting on.

The range book has been validated on thirteen months. That is enough to
measure a per-trade edge and nowhere near enough for the questions now in
front of it:

  DK's seasonality instinct. Doc 117 could not test it because thirteen
  months means ONE observation per calendar month. September reading +37.6%
  a day against November's +5.9% is a single year's weather. Five years makes
  it five observations, which is still thin but is at least a question.

  Walk-forward on the threshold. Doc 115 chose containment-above-median on
  the whole sample. Nobody has fitted it on early data and tested it on later.

  Whether any of it survives a different market. Thirteen months covers one
  regime. 2021's mania, the 2022 collapse and the 2023 grind are the honest
  test of a mean-reversion book.

WHY THIS IS CHEAP NOW AND WAS NOT BEFORE. The existing panel is MINUTE bars,
which cost ~8,760 requests per symbol for five years and put the job out of
reach. The book runs on FIFTEEN-minute bars. Coinbase serves those at 300
candles a request, so five years is ~584 requests per symbol - sixteen times
less. The minute data was only ever needed for the queue model.

Binance is geo-blocked from here (451). Coinbase answers (200), so the panel
is Coinbase USD spot, which also removes the survivorship question that
hangs over an exchange-chosen perp list: these are the products that existed
and kept trading, and delistings are visible as short histories rather than
silently absent.

Writes to data_15m/. Resumable - a symbol already complete is skipped, so
this can be interrupted and restarted.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, time, json
import urllib.request
import numpy as np, pandas as pd

OUT = "/home/claude/qlab/data_15m"
GRAN = 900                      # 15 minutes
MAX = 300                       # candles per request
YEARS = 5
BASE = "https://api.exchange.coinbase.com"
PAUSE = 0.12                    # ~8 requests a second, inside the public limit


def get(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "qlab/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if k == tries-1: return None
            time.sleep(1.5*(k+1))
    return None


def products(n):
    p = get(f"{BASE}/products")
    if not p: return []
    rows = [x for x in p if x.get("quote_currency") == "USD"
            and x.get("status") == "online" and not x.get("trading_disabled")
            and not x.get("auction_mode")]
    # rank by 24h volume so the panel is the liquid end, where the book trades
    stats = []
    for x in rows:
        pid = x["id"]
        s = get(f"{BASE}/products/{pid}/stats")
        time.sleep(PAUSE)
        if not s: continue
        try:
            vol = float(s.get("volume", 0))*float(s.get("last") or 0)
        except Exception:
            vol = 0.0
        if vol > 0: stats.append((pid, vol))
    stats.sort(key=lambda z: -z[1])
    return [p for p, _ in stats[:n]]


def fetch(pid, years=YEARS):
    end = pd.Timestamp.utcnow().floor("15min")
    start = end - pd.Timedelta(days=365*years)
    span = pd.Timedelta(seconds=GRAN*MAX)
    out = []
    t = end
    empty = 0
    while t > start:
        a = max(t-span, start)
        url = (f"{BASE}/products/{pid}/candles?granularity={GRAN}"
               f"&start={a.isoformat()}&end={t.isoformat()}")
        c = get(url)
        time.sleep(PAUSE)
        if c is None:
            empty += 1
            if empty > 6: break
            t = a; continue
        if len(c) == 0:
            empty += 1
            if empty > 25: break          # ran past the product's listing date
        else:
            empty = 0
            out.extend(c)
        t = a
    if not out: return None
    d = pd.DataFrame(out, columns=["t", "low", "high", "open", "close", "volume"])
    d = d.drop_duplicates(subset="t").sort_values("t")
    d.index = pd.to_datetime(d.t, unit="s", utc=True)
    return d[["open", "high", "low", "close", "volume"]].astype(float)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    os.makedirs(OUT, exist_ok=True)
    print(f"Listing Coinbase USD products by dollar volume...", flush=True)
    pids = products(n)
    print(f"{len(pids)} products. Target {YEARS} years of 15-minute bars each.\n",
          flush=True)
    done = 0
    for i, pid in enumerate(pids, 1):
        sym = pid.replace("-", "")
        path = f"{OUT}/{sym}.csv"
        if os.path.exists(path):
            try:
                ex = pd.read_csv(path)
                if len(ex) > 50_000:
                    print(f"  [{i}/{len(pids)}] {pid:<14} already have "
                          f"{len(ex):,} bars — skipped", flush=True)
                    done += 1; continue
            except Exception:
                pass
        t0 = time.time()
        d = fetch(pid)
        if d is None or len(d) < 5000:
            print(f"  [{i}/{len(pids)}] {pid:<14} too little history "
                  f"({0 if d is None else len(d)})", flush=True)
            continue
        d.to_csv(path)
        done += 1
        yrs = (d.index[-1]-d.index[0]).days/365.25
        print(f"  [{i}/{len(pids)}] {pid:<14} {len(d):>7,} bars  "
              f"{yrs:>4.1f}y  from {str(d.index[0])[:10]}  "
              f"({time.time()-t0:.0f}s)", flush=True)
    print(f"\n{done} symbols written to {OUT}", flush=True)
