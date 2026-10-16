"""
THE GRAVEYARD — 56 delisted Hyperliquid perps, the deaths our panel is missing.

Doc 123 named survivorship as the binding doubt on the range book: the
five-year Coinbase panel holds only products listed TODAY, so every coin that
died is absent, and for a book that buys dips those are the dips that never
came back. A partial test on five slow-dying Coinbase delistings suggested the
bias ran the OTHER way - dying coins were three times better for a two-sided
book - but every one of those five traded for years before going, so the
sudden collapses were still missing.

Hyperliquid flags 56 delisted perps and serves their candle history. The list
is the graveyard those five could not represent:

  FTT      the FTX token, through the exchange's collapse
  USTC     Terra's broken stablecoin
  RNDR, MATIC, FTM, MKR   migrations and renames rather than failures
  SHIA, FRIEND, UNIBOT, MYRO, PANDORA, BLAST, MEW   the 2023-24 memecoin cycle,
           listed near their peak and delisted after they faded

That mixture matters: a migration is not a death, and conflating the two would
understate the damage. The test downstream must separate them, but the data
has to exist first.

Candles cap at 5,000 per request (~52 days at 15 minutes), so each coin is
paged backwards from its last trading day until the history runs out.

Read-only public market data. CAP-021: no account, no credential, no order.
"""
import warnings; warnings.filterwarnings("ignore")
import json, time, os, sys, urllib.request
import pandas as pd

API = "https://api.hyperliquid.xyz/info"
OUT = "/home/claude/qlab/data_hl_dead"
IV, CAP = "15m", 5000


def post(body, tries=4):
    for k in range(tries):
        try:
            r = urllib.request.Request(
                API, data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json",
                         "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(r, timeout=35) as f:
                return json.load(f)
        except Exception:
            time.sleep(1.5*(k+1))
    return None


def delisted():
    m = post({"type": "meta"})
    return [u["name"] for u in m.get("universe", [])] if m else [], \
           [u["name"] for u in m.get("universe", []) if u.get("isDelisted")] if m else []


def history(coin, years=5):
    """Page backwards from now until the history runs out."""
    end = int(time.time()*1000)
    floor = end - years*365*86400*1000
    out = []; cur = end; empty = 0
    while cur > floor:
        start = cur - CAP*15*60*1000
        r = post({"type": "candleSnapshot",
                  "req": {"coin": coin, "interval": IV,
                          "startTime": start, "endTime": cur}})
        time.sleep(0.25)
        if not r:
            empty += 1
            if empty > 3: break
            cur = start; continue
        empty = 0
        out.extend(r)
        oldest = min(x["t"] for x in r)
        if oldest >= cur - 1000: break      # no further back available
        cur = oldest - 1
        if len(out) > 220000: break
    if not out: return None
    d = pd.DataFrame(out).drop_duplicates(subset="t")
    d.index = pd.to_datetime(d.t, unit="ms", utc=True)
    d = d.rename(columns={"o": "open", "h": "high", "l": "low",
                          "c": "close", "v": "volume"})
    for c in ("open", "high", "low", "close", "volume"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d[["open", "high", "low", "close", "volume"]].sort_index()


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    _, dead = delisted()
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else len(dead)
    dead = dead[:lim]
    print(f"{len(dead)} delisted perps to fetch\n", flush=True)
    for i, c in enumerate(dead, 1):
        p = f"{OUT}/{c}.csv"
        if os.path.exists(p):
            try:
                if len(pd.read_csv(p)) > 2000:
                    print(f"  [{i}/{len(dead)}] {c:<10} have it", flush=True)
                    continue
            except Exception:
                pass
        t0 = time.time(); d = history(c)
        if d is None or len(d) < 2000:
            print(f"  [{i}/{len(dead)}] {c:<10} too little "
                  f"({0 if d is None else len(d)})", flush=True); continue
        d.to_csv(p)
        fall = (d.close.iloc[-1]/d.close.max()-1)*100
        print(f"  [{i}/{len(dead)}] {c:<10} {len(d):>7,} bars  "
              f"{str(d.index[0])[:10]} -> {str(d.index[-1])[:10]}  "
              f"peak-to-death {fall:>+6.0f}%  ({time.time()-t0:.0f}s)", flush=True)
