"""Altcoin scanner (DK 7 Nov: Nebraskangooner's 99-day smoothed MA as a first-pass filter). Top USDT alts on Binance spot by 24h volume.
Per coin: close, 99-day SMMA (RMA, alpha 1/99), % above/below, line slope over 10 days, days since the last cross, 30d and 90d return
minus BTC's. Writes JSON to stdout (or the path given)."""
import sys, json, time, datetime as dt, requests, pandas as pd, numpy as np
API = "https://data-api.binance.vision/api/v3"
SKIP = {"USDC", "FDUSD", "TUSD", "USDP", "DAI", "EUR", "EURI", "AEUR", "XUSD", "USD1", "BFUSD", "RLUSD", "PAXG", "WBTC", "WBETH", "BTC", "USDE", "PYUSD", "U", "GBP", "TRY", "BRL"}
N = int(sys.argv[2]) if len(sys.argv) > 2 else 40
t = requests.get(f"{API}/ticker/24hr", timeout=30).json()
rows = [x for x in t if x["symbol"].endswith("USDT") and x["symbol"][:-4] not in SKIP and float(x["quoteVolume"]) > 0]
rows.sort(key=lambda x: -float(x["quoteVolume"]))
def daily(sym):
    k = requests.get(f"{API}/klines", params=dict(symbol=sym, interval="1d", limit=1000), timeout=30).json()
    return pd.Series([float(x[4]) for x in k], index=pd.to_datetime([x[0] for x in k], unit="ms"))
btc = daily("BTCUSDT")
def stats(sym, c):
    sm = c.ewm(alpha=1/99, adjust=False).mean(); above = c > sm
    cross = above.ne(above.shift()); last = above.index[cross][-1] if cross.iloc[1:].any() else above.index[0]
    ret = lambda s, n: (s.iloc[-1] / s.iloc[-1 - n] - 1) * 100 if len(s) > n else None
    return dict(coin=sym[:-4], price=float(c.iloc[-1]), line=float(sm.iloc[-1]), dist=float((c.iloc[-1] / sm.iloc[-1] - 1) * 100),
                slope10=float((sm.iloc[-1] / sm.iloc[-11] - 1) * 100), above=bool(above.iloc[-1]), days_since_cross=int((c.index[-1] - last).days),
                r30=ret(c, 30), r90=ret(c, 90), days=len(c))
b = stats("BTCUSDT", btc)
out = []
for x in rows:
    if len(out) >= N: break
    try:
        c = daily(x["symbol"])
        if len(c) < 200: continue
        s = stats(x["symbol"], c); s["vol24"] = float(x["quoteVolume"])
        s["rs30"] = None if s["r30"] is None else s["r30"] - b["r30"]; s["rs90"] = None if s["r90"] is None else s["r90"] - b["r90"]
        out.append(s); time.sleep(0.1)
    except Exception as e: print(x["symbol"], e, file=sys.stderr)
res = {"asof": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "candle": str(btc.index[-1].date()), "btc": b, "coins": out}
s = json.dumps(res, indent=0)
if len(sys.argv) > 1 and sys.argv[1] != "-": open(sys.argv[1], "w").write(s)
else: print(s)
