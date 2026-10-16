"""
INDIVIDUAL STOCKS, 20+ YEARS DAILY — does the range book's equity edge widen?

Doc 133 showed the containment range book earns +0.28% an episode on ETFs
over twenty years. ETFs are baskets; their oscillation is the market's
oscillation. Individual stocks carry their own idiosyncratic noise - earnings
gaps, downgrades, buybacks - and the honest question is whether that noise is
more chop (good for the book) or more gap (bad: the break exit at the worst
tick eats gaps).

SURVIVORSHIP, said up front. Yahoo serves tickers that exist today. A panel of
today's names over-represents companies that did well, which flatters LONG
results and punishes SHORT results. Two mitigations: the universe below
deliberately includes long decliners that still trade (INTC, F, GE, C, BAC,
WBA, M, X, AAL, PARA, KSS, VZ, T), and the book is two-sided, so the bias
pulls the two sides in opposite directions rather than inflating the total.
It is a known gap, not a solved one.

~80 names, chosen for sector spread and at least 20 years of history where
possible. Read-only public data. CAP-021: no account, no credential, no order.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, time, json, urllib.request
import pandas as pd

OUT = "/home/claude/qlab/data_stocks20"
UNIVERSE = {
  "tech":      ["AAPL","MSFT","INTC","CSCO","ORCL","IBM","QCOM","TXN","AMD","NVDA","ADBE","HPQ"],
  "banks":     ["JPM","BAC","C","WFC","GS","MS","USB","AXP","BK","SCHW"],
  "energy":    ["XOM","CVX","COP","OXY","SLB","HAL","DVN","EOG","MRO","VLO"],
  "industrial":["GE","CAT","BA","HON","MMM","UPS","FDX","DE","EMR","X","AAL","F","GM"],
  "consumer":  ["WMT","HD","MCD","KO","PEP","PG","NKE","SBUX","TGT","COST","M","KSS","WBA","DIS","PARA"],
  "health":    ["JNJ","PFE","MRK","ABT","AMGN","GILD","BMY","LLY","UNH","MDT"],
  "telecom/util":["T","VZ","DUK","SO","NEE","D","EXC"],
  "materials": ["NEM","FCX","DD","DOW","NUE","AA"],
}
ALL = [s for v in UNIVERSE.values() for s in v]


def fetch(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=25y"
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
            j = json.load(r)
        res = j["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        d = pd.DataFrame({"open": q["open"], "high": q["high"], "low": q["low"],
                          "close": q["close"], "volume": q["volume"]},
                         index=pd.to_datetime(res["timestamp"], unit="s", utc=True))
        return d.dropna(subset=["close"]).astype(float)
    except Exception:
        return None


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    ok = 0
    for i, sym in enumerate(ALL, 1):
        p = f"{OUT}/{sym}.csv"
        if os.path.exists(p):
            try:
                if len(pd.read_csv(p)) > 1000:
                    ok += 1; continue
            except Exception: pass
        d = fetch(sym); time.sleep(0.4)
        if d is None or len(d) < 1000:
            print(f"  [{i}/{len(ALL)}] {sym:<6} too little", flush=True); continue
        d.to_csv(p); ok += 1
        print(f"  [{i}/{len(ALL)}] {sym:<6} {len(d):>6,} days  "
              f"{(d.index[-1]-d.index[0]).days/365.25:>4.1f}y  from {str(d.index[0])[:10]}", flush=True)
    print(f"\n{ok}/{len(ALL)} written to {OUT}")
