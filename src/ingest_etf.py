"""
BEYOND CRYPTO — a diversified ETF universe for the range book.

DK: "Can we extend these systems into any other suitable areas? ... We haven't
     even looked at stocks & shares, or oil, commodities etc."

This is the strongest extension available and it is not a new strategy. It is
the book we already have, on markets that do not move together. Everything in
Capital currently rises and falls with one thing: crypto. Six books on one
asset class is one book wearing six hats, whatever the measured correlations
say on a quiet month.

WHY THESE MARKETS SHOULD SUIT IT BETTER, NOT WORSE. The range book earns when
price oscillates around a STABLE mean - doc 129 showed its mechanics invert on
an asset whose mean is rising fast. Crypto is the hostile case: enormous drift,
and the book still works. Commodities and index ETFs have far less drift and
more institutional mean-reversion behaviour, which is the condition the book
wants. The hypothesis is that it should do BETTER here, and that hypothesis is
cheap to falsify.

THE UNIVERSE, chosen so the legs are genuinely independent:
  energy        USO (oil), UNG (natural gas), XLE
  metals        GLD, SLV, CPER (copper), GDX (miners)
  agriculture   DBA, CORN, WEAT
  equity index  SPY, QQQ, IWM, DIA
  sectors       XLF, XLK, XLV, XLU, XLP, XLI
  bonds         TLT, IEF, HYG, LQD, TIP
  international EEM, EFA, FXI, EWJ, EWZ
  volatility    VXX
  currency      UUP, FXE

WHAT WILL HAVE TO CHANGE, and it is better to say so now. The book is
specified on 15-MINUTE bars. These are DAILY. Doc 111 already showed the
book's behaviour differs by timeframe - and it found 4-hour and daily to be
QUIET-market tools that beat 15-minute on per-trade return. So the daily
configuration must be re-derived rather than assumed, and that re-derivation
has to be walk-forwarded, not fitted on the whole sample (doc 128's lesson).

Read-only public market data. CAP-021: no account, no credential, no order.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, time, json
import urllib.request
import pandas as pd

OUT = "/home/claude/qlab/data_etf"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
      "Accept": "application/json"}

UNIVERSE = {
    "USO": "etf", "UNG": "etf", "XLE": "etf",
    "GLD": "etf", "SLV": "etf", "CPER": "etf", "GDX": "etf",
    "DBA": "etf", "CORN": "etf", "WEAT": "etf",
    "SPY": "etf", "QQQ": "etf", "IWM": "etf", "DIA": "etf",
    "XLF": "etf", "XLK": "etf", "XLV": "etf", "XLU": "etf",
    "XLP": "etf", "XLI": "etf", "XLB": "etf", "XLY": "etf",
    "TLT": "etf", "IEF": "etf", "HYG": "etf", "LQD": "etf", "TIP": "etf",
    "EEM": "etf", "EFA": "etf", "FXI": "etf", "EWJ": "etf", "EWZ": "etf",
    "VXX": "etf", "UUP": "etf", "FXE": "etf", "SLX": "etf", "XME": "etf",
}


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=UA), timeout=35) as r:
                return json.load(r)
        except Exception:
            time.sleep(1.5*(k+1))
    return None


def fetch(sym, cls, years=3):
    """Nasdaq serves roughly three years. One request, the simple UA curl
    uses - the browser-style headers above made it hang."""
    end = pd.Timestamp.utcnow().normalize()
    lo = end - pd.DateOffset(years=years)
    url = (f"https://api.nasdaq.com/api/quote/{sym}/historical"
           f"?assetclass={cls}&fromdate={lo.strftime('%Y-%m-%d')}"
           f"&todate={end.strftime('%Y-%m-%d')}&limit=9999")
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                timeout=30) as r:
            j = json.load(r)
        rows = j["data"]["tradesTable"]["rows"]
    except Exception:
        return None
    if not rows: return None
    d = pd.DataFrame(rows)
    def num(x):
        try: return float(str(x).replace("$", "").replace(",", ""))
        except Exception: return float("nan")
    out = pd.DataFrame({
        "open": d["open"].map(num), "high": d["high"].map(num),
        "low": d["low"].map(num), "close": d["close"].map(num),
        "volume": d["volume"].map(num)})
    out.index = pd.to_datetime(d["date"], format="%m/%d/%Y", errors="coerce", utc=True)
    out = out[out.index.notna()].sort_index()
    return out[out.close.notna()]


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    items = list(UNIVERSE.items())
    if len(sys.argv) > 1: items = items[:int(sys.argv[1])]
    print(f"{len(items)} instruments — energy, metals, agriculture, equity "
          f"indices, sectors, bonds, international, volatility, currency\n",
          flush=True)
    ok = 0
    for i, (sym, cls) in enumerate(items, 1):
        p = f"{OUT}/{sym}.csv"
        if os.path.exists(p):
            try:
                if len(pd.read_csv(p)) > 500:
                    print(f"  [{i}/{len(items)}] {sym:<6} have it", flush=True)
                    ok += 1; continue
            except Exception:
                pass
        t0 = time.time(); d = fetch(sym, cls)
        if d is None or len(d) < 500:
            print(f"  [{i}/{len(items)}] {sym:<6} too little "
                  f"({0 if d is None else len(d)})", flush=True); continue
        d.to_csv(p); ok += 1
        yrs = (d.index[-1]-d.index[0]).days/365.25
        print(f"  [{i}/{len(items)}] {sym:<6} {len(d):>6,} days  {yrs:>4.1f}y  "
              f"from {str(d.index[0])[:10]}  ({time.time()-t0:.0f}s)", flush=True)
    print(f"\n{ok} instruments written to {OUT}", flush=True)
