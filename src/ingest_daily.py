"""
MULTI-YEAR DAILY HISTORY — the binding constraint on everything else.

Three independent lines converged on the same gap today:
  finding 89  Keltner edge is real in every period, profit only in some
  finding 93  the confluence ladder flips sign across the split and no
              market-wide gate recovers it, because the sample contains ONE
              regime change
  DK's own question about monthly and weekly bias: at 13 months a weekly bar
              gives ~56 observations per symbol and a monthly ~13

All three need years, not months. Binance returns HTTP 451 from here, so this
uses Coinbase Exchange, which serves daily candles back to 2015-2016 for the
majors and to listing for everything else.

Coinbase caps a request at 300 candles, so each symbol is paginated backwards
from today until the exchange stops returning data. Rate limit is ~10 requests
a second public; this stays well inside that.

Writes one CSV per product to data_daily/, in the same column shape the rest
of the lab expects (t in ms, open/high/low/close/volume), so every existing
module can read it without modification.
"""
import warnings; warnings.filterwarnings("ignore")
import json, os, time, urllib.request, urllib.error
import pandas as pd

OUT = "/home/claude/qlab/data_daily"
BASE = "https://api.exchange.coinbase.com"
GRAN = 86400
UA = {"User-Agent": "Mozilla/5.0"}


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503): time.sleep(1.5 * (k + 1)); continue
            if e.code == 404: return None
            raise
        except Exception:
            time.sleep(1.0 * (k + 1))
    return None


def products():
    p = get(f"{BASE}/products")
    if not p: return []
    out = []
    for x in p:
        if x.get("quote_currency") != "USD": continue
        if x.get("trading_disabled") or x.get("status") != "online": continue
        out.append(x["id"])
    return sorted(out)


def history(pid, start_ts=1420070400):
    """Page backwards 300 candles at a time until the exchange runs out."""
    rows = []
    end = int(time.time())
    while end > start_ts:
        beg = end - GRAN * 300
        url = (f"{BASE}/products/{pid}/candles?granularity={GRAN}"
               f"&start={beg}&end={end}")
        c = get(url)
        if not c: break
        rows.extend(c)
        oldest = min(x[0] for x in c)
        if oldest >= end - GRAN: break
        end = oldest - GRAN
        time.sleep(0.16)
        if len(rows) > 6000: break
    if not rows: return None
    d = pd.DataFrame(rows, columns=["ts", "low", "high", "open", "close", "volume"])
    d = d.drop_duplicates("ts").sort_values("ts")
    d["t"] = d.ts.astype("int64") * 1000
    return d[["t", "open", "high", "low", "close", "volume"]].reset_index(drop=True)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    ps = products()
    print(f"{len(ps)} USD products listed on Coinbase", flush=True)
    done = ok = 0
    summary = []
    for pid in ps:
        path = f"{OUT}/{pid.replace('-', '')}.csv"
        if os.path.exists(path):
            done += 1; continue
        try:
            d = history(pid)
        except Exception as e:
            print(f"  {pid:<14} ERROR {type(e).__name__}", flush=True); continue
        if d is None or len(d) < 400:
            continue
        d.to_csv(path, index=False)
        ok += 1
        yrs = (d.t.iloc[-1] - d.t.iloc[0]) / 86400000 / 365.25
        first = pd.to_datetime(d.t.iloc[0], unit="ms").date()
        summary.append((pid, len(d), yrs, str(first)))
        if ok % 10 == 0:
            print(f"  {ok} saved (latest {pid}: {len(d)} bars from {first})", flush=True)
    print(f"\nsaved {ok} new, {done} already present", flush=True)
    if summary:
        S = pd.DataFrame(summary, columns=["product", "bars", "years", "from"])
        S = S.sort_values("bars", ascending=False)
        print(f"\nlongest histories:")
        print(S.head(20).to_string(index=False))
        print(f"\nproducts with >= 4 years: {(S.years >= 4).sum()}")
        print(f"products with >= 2 years: {(S.years >= 2).sum()}")
        print(f"median history: {S.years.median():.1f} years")
        S.to_csv("/home/claude/qlab/runs/daily_coverage.csv", index=False)
