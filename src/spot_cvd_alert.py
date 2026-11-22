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

def context(d, r):
    """Doc 231 / 248 follow-up (DK 22 Nov: "Keep it ... what can be improved"): 2021-26, the alert on its own is a coin flip, but its
    context matters. Bear regime (below the 200-day) + firing on a bounce: 12h mean -0.13% to -0.27%, down 53%, both halves.
    After a 24h flush (< -3%): next 12h +0.45% (bounce more likely). Everything else: coin flip."""
    try:
        dd = d.c.resample("1D").last()
        if len(dd) < 210:
            u = f"https://data-api.binance.vision/api/v3/klines?symbol={SYM}&interval=1d&limit=260"
            k = json.load(urllib.request.urlopen(u, timeout=20)); dd = pd.Series([float(x[4]) for x in k])
        sma = dd.iloc[:-1].tail(200).mean(); px = r["px"]
        w = d.iloc[-97:]; ret24 = px / w.c.iloc[0] - 1; pos = (px - w.l.min()) / max(w.h.max() - w.l.min(), 1e-9)
        if px < sma and (ret24 > 0.02 or pos >= 0.6):
            return "STRONGER: bear regime (below the 200-day) and firing on a bounce — historically leans down (12h avg -0.13% to -0.27%, 53% down). Good confirmation for a short plan at resistance."
        if ret24 < -0.03:
            return "CAUTION: fired after a 24h flush — historically a bounce is more likely (+0.45% avg next 12h). Not a short signal here."
        return "NEUTRAL: outside its useful context this alert is a coin flip (2021-26) — information only."
    except Exception as e:
        return f"context unavailable ({e})"

def check_up(d):
    """Mirror (DK 22 Nov: "the CVD rollover for upward reversals"): spot CVD SOLD down >= BUILD of 24h volume, then bought back
    >= GIVEBACK of it, the CVD low at least an hour old, last hour's delta positive, price still at/below the price at the CVD low."""
    w = d.iloc[-WIN:]; cvd = w.delta.cumsum(); vol = w.v.sum()
    ip = int(np.argmin(cvd.values)); top = cvd.values[:ip + 1].max(); low = cvd.values[ip]; now = cvd.values[-1]
    drop = top - low; back = (now - low) / drop if drop > 0 else 0
    r = dict(t=w.index[-1], px=w.c.iloc[-1], px_low=w.c.iloc[ip], low_t=w.index[ip], drop=drop, drop_pct=drop / vol,
             giveback=back, last_hour=w.delta.iloc[-4:].sum(), bars_since_low=len(w) - 1 - ip)
    r["fire"] = (r["drop_pct"] >= BUILD and back >= GIVEBACK and r["bars_since_low"] >= 4 and r["last_hour"] > 0 and r["px"] <= r["px_low"])
    return r

def context_up(d, r):
    """runs/research/cvd_rollup*.txt (2021-26): the roll-up on its own is a coin flip (long trigger -0.08%/trade). The one context that
    worked: price swept the 24h low in the last hour AND BTC is >= 6% under its 72h high (a flush): n14, +0.98%/trade, 71% win,
    both halves positive. Small sample - treat as a strong hint, not proof."""
    try:
        px = r["px"]; hi72 = d.h.iloc[-288:].max(); lo24_prev = d.l.iloc[-100:-4].min(); swept = d.l.iloc[-4:].min() <= lo24_prev * 1.001
        flush = px <= hi72 * 0.94
        if swept and flush:
            return f"STRONGER: fired right after a sweep of the 24h low, {100 * (1 - px / hi72):.0f}% under the 72h high (flush) — historically +0.98% avg, 71% wins (small sample, n14). Fits a flush-bid / scale-in long."
        if px >= d.c.iloc[-97] * 1.03:
            return "CAUTION: price already up >3% in 24h — a late roll-up, not a bottom signal."
        return "NEUTRAL: outside a flush + sweep the roll-up is a coin flip (2021-26) — information only."
    except Exception as e:
        return f"context unavailable ({e})"

def text_up(r):
    return (f"## {SYM} spot CVD rolling UP — {r['t']:%d %b %H:%M} UTC\n\n" + f"**{r.get('context', '')}**\n\n"
            f"Binance spot CVD was sold down {r['drop']:,.0f} BTC ({100 * r['drop_pct']:.1f}% of 24h volume) to a low at {r['low_t']:%d %b %H:%M} UTC "
            f"(price {r['px_low']:,.0f}) and has bought back {100 * r['giveback']:.0f}% of it. Last hour's spot delta {r['last_hour']:+,.0f} BTC. "
            f"Price now {r['px']:,.0f} (not yet above the selling low).\n\nSpot buyers absorbing at the lows. Check the liquidation clusters below and the 4h trigger. Not financial advice.\n")

def text(r):
    return (f"## {SYM} spot CVD rolling over — {r['t']:%d %b %H:%M} UTC\n\n" + f"**{r.get('context', '')}**\n\n"
            f"Binance spot CVD built +{r['rise']:,.0f} BTC ({100 * r['rise_pct']:.1f}% of 24h volume) to a peak at {r['peak_t']:%d %b %H:%M} UTC "
            f"(price {r['px_peak']:,.0f}) and has given back {100 * r['giveback']:.0f}% of it. Last hour's spot delta {r['last_hour']:+,.0f} BTC. "
            f"Price now {r['px']:,.0f}.\n\nKingfisher pattern: spot bid held price while shorts built; spot now being sold. "
            f"Check futures CVD, funding, OI and the liquidation clusters below (doc 230). Not financial advice.\n")

if __name__ == "__main__":
    d = bars()
    if sys.argv[1:] == ["backtest"]:
        last = lastu = None
        for i in range(WIN + 1, len(d) + 1):
            r = check(d.iloc[:i])
            if r["fire"] and (last is None or r["t"] - last > pd.Timedelta("12h")):
                last = r["t"]; fwd = d.c.iloc[i - 1:i + 48]
                print(f"DOWN {r['t']:%d %b %H:%M} px {r['px']:,.0f} rise {100 * r['rise_pct']:.1f}% give {100 * r['giveback']:.0f}% | next 12h low {100 * (fwd.min() / r['px'] - 1):+.1f}% high {100 * (fwd.max() / r['px'] - 1):+.1f}%")
            u = check_up(d.iloc[:i])
            if u["fire"] and (lastu is None or u["t"] - lastu > pd.Timedelta("12h")):
                lastu = u["t"]; fwd = d.c.iloc[i - 1:i + 48]; print(f"UP   {u['t']:%d %b %H:%M} px {u['px']:,.0f} [{context_up(d.iloc[:i], u)[:8]}] | next 12h low {100 * (fwd.min() / u['px'] - 1):+.1f}% high {100 * (fwd.max() / u['px'] - 1):+.1f}%")
        sys.exit()
    r = check(d)
    if r["fire"]: r["context"] = context(d, r)
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    if r["fire"]:
        os.makedirs("runs/alerts", exist_ok=True); open("runs/alerts/spot_cvd_alert.md", "w").write(text(r))
    u = check_up(d)
    if u["fire"]: u["context"] = context_up(d, u)
    print("UP:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in u.items()})
    if u["fire"]:
        os.makedirs("runs/alerts", exist_ok=True); open("runs/alerts/spot_cvd_rollup.md", "w").write(text_up(u))
