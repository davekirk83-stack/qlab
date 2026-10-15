"""
LIVE SCAN — run the registered book logic against right-now data.

The forward trackers read Binance's DAILY archives, so a day's action is only
scanned about two days later. That is fine for accumulating evidence and
useless for watching a live event. This runs the same logic against live
5-minute candles so we can see what the books would be doing now.

RESEARCH AND PAPER ONLY. This places nothing, connects to no account and holds
no credential. It reads public market data and prints what the rules say.
"""
import warnings; warnings.filterwarnings("ignore")
import json, urllib.request, time
import numpy as np, pandas as pd

COINS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "AVAX", "LINK", "LTC", "NEAR",
         "APT", "ARB", "OP", "SUI", "INJ", "TIA", "ADA", "BNB", "AAVE",
         "ATOM", "BCH", "DOT", "TRX", "UNI", "CRV", "ENA", "JUP", "TAO",
         "WIF", "SEI", "TON", "HYPE", "PUMP", "FARTCOIN", "ZEC"]
DROP = 0.02          # cascade v4 trigger
LIFT, HOLD = 0.008, 2     # on 5-minute bars, 10 minutes = 2 bars


def post(p):
    r = urllib.request.Request("https://api.hyperliquid.xyz/info",
                               data=json.dumps(p).encode(),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=40) as x:
        return json.load(x)


def candles(coin, hours=48, interval="5m"):
    s = int((pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours)).timestamp() * 1000)
    c = post({"type": "candleSnapshot",
              "req": {"coin": coin, "interval": interval, "startTime": s}})
    if not c:
        return None
    d = pd.DataFrame(c)
    for k in ("o", "c", "h", "l", "v"):
        d[k] = pd.to_numeric(d[k], errors="coerce")
    d["ts"] = pd.to_datetime(d.t, unit="ms")
    return d.sort_values("ts").reset_index(drop=True)


if __name__ == "__main__":
    print("LIVE SCAN — cascade v4 logic against right-now data")
    print("RESEARCH ONLY. No order, no account, no capital.\n")
    rows = []
    for c in COINS:
        try:
            d = candles(c)
        except Exception:
            continue
        if d is None or len(d) < 100:
            continue
        C, H, L = d.c.values, d.h.values, d.l.values
        n = len(C)
        r5 = np.full(n, np.nan); r5[1:] = C[1:] / C[:-1] - 1
        hi24 = H[-288:].max() if n > 288 else H.max()
        lo24 = L[-288:].min() if n > 288 else L.min()
        pos = (C[-1] - lo24) / (hi24 - lo24) if hi24 > lo24 else np.nan
        # hourly close_in_bar, the v4 filter
        hr = d.set_index("ts").resample("1h").agg(
            high=("h", "max"), low=("l", "min"), close=("c", "last")).dropna()
        cib = np.nan
        if len(hr) and hr.high.iloc[-1] > hr.low.iloc[-1]:
            cib = (hr.close.iloc[-1] - hr.low.iloc[-1]) / (hr.high.iloc[-1] - hr.low.iloc[-1])
        trig = np.flatnonzero(r5 <= -DROP)
        last_trig = trig[-1] if len(trig) else None
        rows.append(dict(coin=c, px=C[-1],
                         r1h=(C[-1] / C[-12] - 1) * 100 if n > 12 else np.nan,
                         r24=(C[-1] / C[-288] - 1) * 100 if n > 288 else np.nan,
                         pos24=pos, worst5m=np.nanmin(r5[-288:]) * 100,
                         n_trig=len(trig), cib=cib,
                         mins_since=(n - 1 - last_trig) * 5 if last_trig is not None else None))
        time.sleep(0.12)
    T = pd.DataFrame(rows).sort_values("r24")
    print(f"  {'coin':<10}{'price':>12}{'1h':>8}{'24h':>8}{'pos24':>7}"
          f"{'worst5m':>9}{'trig':>6}{'cib':>7}{'since':>8}")
    for _, r in T.iterrows():
        mark = ""
        if r.n_trig > 0 and r.cib == r.cib and r.cib >= 0.5:
            mark = "  <== v4 CONDITIONS MET"
        elif r.n_trig > 0:
            mark = "  (triggered, filter says no)"
        print(f"  {r.coin:<10}{r.px:>12,.4f}{r.r1h:>+7.2f}%{r.r24:>+7.2f}%"
              f"{r.pos24:>7.2f}{r.worst5m:>+8.2f}%{int(r.n_trig):>6}"
              f"{r.cib:>7.2f}{str(int(r.mins_since))+'m' if r.mins_since==r.mins_since and r.mins_since is not None else '-':>8}{mark}")
    print(f"\n  SUMMARY")
    print(f"    instruments scanned          {len(T)}")
    print(f"    with a >=2% five-minute bar in 48h: {(T.n_trig>0).sum()}")
    print(f"    median 24h move              {T.r24.median():+.2f}%")
    print(f"    median position in 24h range {T.pos24.median():.2f}")
    print(f"    instruments in the bottom fifth of their 24h range: "
          f"{(T.pos24<0.2).sum()}/{len(T)}")
