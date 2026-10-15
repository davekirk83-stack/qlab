"""
WIDE UNIVERSE FETCHER — 10y daily OHLCV across asset classes, via Nasdaq.

Why: the non-crypto side of the research universe was seven instruments (SPY,
gold, silver, four FX pairs). That is far too thin to say whether the system
works outside crypto, which the regime run showed is the open question that
matters most.

Routes tried and rejected:
  FMP full + light history .... plan-gated on the current subscription
  Alpha Vantage outputsize=full plan-gated
  Yahoo chart API ............. 429 on this container's IP, every host/header
  Stooq CSV ................... proof-of-work solved, then "Access denied"
                                (datacentre IP); HTML works but ~40 rows/page,
                                ~19,000 requests for a usable universe
  Nasdaq ...................... works, free, no key, hard cap of 10 years

10 years is enough for the job: it contains the Q4 2018 selloff, the March 2020
crash and the 2022 bear market, which is the regime variety the crypto sample
does not have.
"""
import os, sys, time, json, hashlib
import requests, pandas as pd

OUT = "/home/claude/qlab/data_wide"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

ETFS = """SPY QQQ IWM DIA MDY IJR VTI VTV VUG MTUM QUAL USMV SPLV
XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC
EFA EEM FXI EWJ EWZ EWG EWU INDA EWY EWT VGK ACWI
TLT IEF SHY LQD HYG AGG TIP BND EMB MUB
GLD SLV USO UNG DBA DBC CORN WEAT PPLT CPER URA
VNQ IYR VXX""".split()

STOCKS = """AAPL MSFT NVDA AMZN GOOGL META TSLA
JPM BAC GS MS C WFC AXP V MA
XOM CVX COP SLB
JNJ PFE UNH LLY MRK ABBV TMO ABT AMGN GILD
WMT HD COST PG KO PEP MCD NKE TGT LOW SBUX
BA CAT GE HON LMT RTX DE MMM UPS FDX
DIS NFLX CMCSA T VZ
INTC AMD CSCO ORCL CRM ADBE IBM QCOM TXN AMAT MU
F GM""".split()


def fetch(s, sym, assetclass):
    url = f"https://api.nasdaq.com/api/quote/{sym}/historical"
    p = dict(assetclass=assetclass, fromdate="2006-01-01",
             todate="2026-10-13", limit=99999)
    for a in range(4):
        try:
            r = s.get(url, params=p, timeout=45)
        except Exception:
            time.sleep(2 + 2 * a); continue
        if r.status_code != 200:
            time.sleep(2 + 2 * a); continue
        try:
            rows = r.json()["data"]["tradesTable"]["rows"]
        except Exception:
            return None
        if not rows or len(rows) < 500:
            return None
        def num(x):
            if x is None:
                return None
            x = str(x).replace("$", "").replace(",", "").strip()
            if x in ("", "N/A", "--"):
                return None
            try:
                return float(x)
            except ValueError:
                return None
        df = pd.DataFrame([dict(
            date=r_["date"], open=num(r_.get("open")), high=num(r_.get("high")),
            low=num(r_.get("low")), close=num(r_.get("close")),
            volume=num(r_.get("volume")) or 0.0) for r_ in rows])
        df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
        df = df.dropna(subset=["date", "close", "open", "high", "low"])
        df = df[df.close > 0].sort_values("date").drop_duplicates("date")
        return df if len(df) > 500 else None
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json",
                      "Accept-Language": "en-US,en;q=0.9"})
    plan = [(x, "etf") for x in ETFS] + [(x, "stocks") for x in STOCKS]
    man = {}
    ok = miss = skip = 0
    for sym, cls in plan:
        dst = f"{OUT}/{sym}.csv"
        if os.path.exists(dst):
            skip += 1; continue
        df = fetch(s, sym, cls)
        if df is None and cls == "etf":
            df = fetch(s, sym, "stocks")
        if df is None:
            print(f"  MISS {sym}", flush=True); miss += 1; time.sleep(0.3); continue
        df.to_csv(dst, index=False)
        man[sym] = dict(rows=len(df), start=str(df.date.min().date()),
                        end=str(df.date.max().date()), cls=cls,
                        source="nasdaq api/quote historical")
        ok += 1
        if ok % 15 == 0:
            print(f"  ... {ok} fetched", flush=True)
        time.sleep(0.35)
    mp = f"{OUT}/_manifest.json"
    old = json.load(open(mp)) if os.path.exists(mp) else {}
    old.update(man); json.dump(old, open(mp, "w"), indent=1)
    print(f"done: {ok} fetched, {skip} already present, {miss} missed")


if __name__ == "__main__":
    main()
