"""
BINANCE SPOT CVD ROLL-OVER ALERT (DK 13 Nov: "set this as a general alert"; doc 229/230, Kingfisher "maintain with spot, dump spot").
Binance BTCUSDT spot, 15-min bars from the public data mirror. Delta per bar = taker buys - taker sells (BTC); CVD = running sum.
Fires when, inside the last 24 hours, spot CVD has BUILT (rise from its low to its peak >= BUILD x that window's volume)
and has then ROLLED OVER: it has given back >= GIVEBACK of that rise, the peak is at least an hour old, the last hour's
delta is negative and price is below the price at the CVD peak. This is the "dump spot" step after the spot bid held price up.
Usage: python src/spot_cvd_alert.py            -> live check; writes runs/alerts/spot_cvd_alert.md when it fires
       python src/spot_cvd_alert.py backtest   -> every bar of the last ~10 days, prints when it would have fired
"""
import sys, os, json, urllib.request, datetime as dt
import numpy as np, pandas as pd

SYM = os.environ.get("CVD_SYM", "BTCUSDT"); BUILD, GIVEBACK, WIN = 0.02, 0.40, 96   # 96 x 15 min = 24 h

def bars(n=1000):
    u = f"https://data-api.binance.vision/api/v3/klines?symbol={SYM}&interval=15m&limit={n}"
    k = json.load(urllib.request.urlopen(u, timeout=20))
    d = pd.DataFrame(k, columns="t o h l c v ct qv n tb tq x".split()).astype(float)
    d.index = pd.to_datetime(d.t, unit="ms", utc=True); d["delta"] = 2 * d.tb - d.v
    return d.iloc[:-1]                                             # drop the bar still forming

def check(d):
    w = d.iloc[-WIN:]; cvd = w.delta.cumsum(); vol = w.v.sum()
    ip = int(np.argmax(cvd.values)); lo = cvd.values[:ip + 1].min(); peak = cvd.values[ip]; now = cvd.values[-1]
    rise = peak - lo; give = (peak - now) / rise if rise > 0 else 0
    r = dict(t=w.index[-1], px=w.c.iloc[-1], px_peak=w.c.iloc[ip], peak_t=w.index[ip], rise=rise, rise_pct=rise / vol,
             giveback=give, last_hour=w.delta.iloc[-4:].sum(), bars_since_peak=len(w) - 1 - ip)
    r["fire"] = (r["rise_pct"] >= BUILD and give >= GIVEBACK and r["bars_since_peak"] >= 4 and r["last_hour"] < 0 and r["px"] < r["px_peak"])
    return r

def text(r):
    return (f"## {SYM} spot CVD rolling over — {r['t']:%d %b %H:%M} UTC\n\n"
            f"Binance spot CVD built +{r['rise']:,.0f} BTC ({100 * r['rise_pct']:.1f}% of 24h volume) to a peak at {r['peak_t']:%d %b %H:%M} UTC "
            f"(price {r['px_peak']:,.0f}) and has given back {100 * r['giveback']:.0f}% of it. Last hour's spot delta {r['last_hour']:+,.0f} BTC. "
            f"Price now {r['px']:,.0f}.\n\nKingfisher pattern: spot bid held price while shorts built; spot now being sold. "
            f"Check futures CVD, funding, OI and the liquidation clusters below (doc 230). Not financial advice.\n")

if __name__ == "__main__":
    d = bars()
    if sys.argv[1:] == ["backtest"]:
        last = None
        for i in range(WIN + 1, len(d) + 1):
            r = check(d.iloc[:i])
            if r["fire"] and (last is None or r["t"] - last > pd.Timedelta("12h")):
                last = r["t"]; fwd = d.c.iloc[i - 1:i + 48]
                print(f"{r['t']:%d %b %H:%M} px {r['px']:,.0f} rise {100 * r['rise_pct']:.1f}% give {100 * r['giveback']:.0f}% | next 12h low {100 * (fwd.min() / r['px'] - 1):+.1f}% high {100 * (fwd.max() / r['px'] - 1):+.1f}%")
        sys.exit()
    r = check(d); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    if r["fire"]:
        os.makedirs("runs/alerts", exist_ok=True); open("runs/alerts/spot_cvd_alert.md", "w").write(text(r))
