"""Doc 219 — daily OHLCV for single shares (S&P 500 + FTSE 100 current constituents) from Yahoo, 2005 onwards, for the single-stock research
(DK 10:55: "you inherently believe there is no way to find new areas of profit"). Runs in GitHub Actions (data only, no trading).
Caveat: CURRENT constituents only -> survivorship bias (favours long strategies); short-term reversal / event tests are less affected."""
import os, io, time, urllib.request, pandas as pd, yfinance as yf
OUT = "data_stocks"; os.makedirs(OUT, exist_ok=True)
def table(url, col):
    html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode()
    for t in pd.read_html(io.StringIO(html)):
        if col in t.columns: return t
    raise RuntimeError(f"no table with {col} at {url}")
sp = table("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "Symbol")
us = [s.replace(".", "-") for s in sp.Symbol.astype(str)]
ft = table("https://en.wikipedia.org/wiki/FTSE_100_Index", "Ticker")
uk = [str(s).replace(".", "-") + ".L" if not str(s).endswith(".L") else str(s) for s in ft.Ticker]
pd.DataFrame({"ticker": us + uk, "index": ["SP500"] * len(us) + ["FTSE100"] * len(uk),
              "sector": list(sp.get("GICS Sector", [""] * len(us))) + list(ft.get("FTSE industry classification benchmark sector[25]", [""] * len(uk)))}).to_csv(f"{OUT}/universe.csv", index=False)
todo = [t for t in us + uk if not os.path.exists(f"{OUT}/{t}.csv.gz")]
print(len(us), "US +", len(uk), "UK;", len(todo), "to fetch", flush=True)
for i in range(0, len(todo), 50):
    chunk = todo[i:i + 50]
    for a in range(4):
        try: df = yf.download(chunk, start="2005-01-01", auto_adjust=True, group_by="ticker", progress=False, threads=True); break
        except Exception as e: print("retry", e, flush=True); time.sleep(30 * (a + 1))
    for t in chunk:
        try:
            d = df[t].dropna(how="all") if len(chunk) > 1 else df.dropna(how="all")
            if len(d) > 250: d.round(4).to_csv(f"{OUT}/{t}.csv.gz")
        except Exception as e: print(t, "skip", e)
    print(f"{min(i + 50, len(todo))}/{len(todo)}", flush=True); time.sleep(3)
print("files:", len([f for f in os.listdir(OUT) if f.endswith('.csv.gz')]))
