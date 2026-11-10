"""Doc 222 — long histories for the 1900– assessment (DK 11:22: "extend your overall assessment back to 1900"; 11:23: "since 2001 has been a
perversion of the stock markets ... in the era of modern monetary policy"). Data only, runs in GitHub Actions.
  Stooq daily: Dow Jones Industrial Average (^DJI, from 1896), S&P 500 (^SPX), FTSE 100 (^UKX), DAX (^DAX), Nikkei (^NKX), gold (XAUUSD)
  Yahoo daily: ^GSPC from 1927 (close-only before 1962), ^DJI
  Shiller monthly (ie_data.xls): S&P composite price, dividend, earnings, CPI, long rate since 1871"""
import os, io, time, urllib.request, pandas as pd
OUT = "data_hist"; os.makedirs(OUT, exist_ok=True)
def get(url):
    for a in range(4):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=90).read()
        except Exception as e: print("retry", url, e, flush=True); time.sleep(10 * (a + 1))
    return None
for sym, nm in [("^dji", "DJI_stooq"), ("^spx", "SPX_stooq"), ("^ukx", "FTSE_stooq"), ("^dax", "DAX_stooq"), ("^nkx", "N225_stooq"), ("xauusd", "GOLD_stooq")]:
    raw = get(f"https://stooq.com/q/d/l/?s={sym}&i=d")
    if raw and raw[:4] != b"No d":
        open(f"{OUT}/{nm}.csv", "wb").write(raw); d = pd.read_csv(io.BytesIO(raw)); print(nm, len(d), d.iloc[0, 0], d.iloc[-1, 0], flush=True)
    else: print(nm, "no data", raw[:80] if raw else None)
try:
    import yfinance as yf
    for t, nm in [("^GSPC", "SPX_yahoo"), ("^DJI", "DJI_yahoo")]:
        d = yf.download(t, start="1900-01-01", auto_adjust=False, progress=False)
        if hasattr(d.columns, "levels"): d.columns = d.columns.get_level_values(0)
        d.to_csv(f"{OUT}/{nm}.csv"); print(nm, len(d), d.index[0], d.index[-1], flush=True)
except Exception as e: print("yahoo failed", e)
raw = get("http://www.econ.yale.edu/~shiller/data/ie_data.xls")
if raw:
    open(f"{OUT}/shiller_ie_data.xls", "wb").write(raw)
    try: x = pd.read_excel(io.BytesIO(raw), sheet_name="Data", skiprows=7); x.to_csv(f"{OUT}/shiller_monthly.csv", index=False); print("shiller", len(x))
    except Exception as e: print("shiller parse failed", e)
