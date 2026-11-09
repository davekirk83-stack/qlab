"""Doc 195 — market search, round 1 (DK 9 Nov: "taking trades constantly across multiple markets and using a whole range of books").
HONEST BY CONSTRUCTION: every decision is made on a bar that has closed; entries are at that close (market) or at a price fixed before
the next bar opens (stop/limit); within a bar the stop is always assumed to come first. Fixed rules (no tuning here), costs included,
reported in both halves of each market's data. Markets: whatever 5-min IG/Dukascopy data we hold + Coinbase 15-min crypto (5 years).

SPIKE  the doc 191 CONT engine unchanged: 15-min bar range >= 3x the mean 15-min range of the prior 5 sessions; next bar extends the
       extreme by > 0.25 x range and closes beyond the spike close -> enter at that close with the spike; stop the confirming bar's opposite
       extreme; target 1x spike range; exit after 8 bars or at the session end.
ORB    opening-range breakout: range of the session's first 30 minutes; first 15-min close beyond it (before 3h into the session) -> enter
       at that close; stop the other side of the range; target 2R; exit at the session end.
"""
import os, sys, numpy as np, pandas as pd
ROOT = os.environ.get("QLAB_ROOT", "."); OUTF = f"{ROOT}/runs/market_search_1.txt"
LINES = []
def log(s): print(s, flush=True); LINES.append(s)

def load5(f):
    d = pd.read_csv(f); d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d.columns = [c.lower() for c in d.columns]
    return d[["open", "high", "low", "close"]].astype(float)

def session15(d, tz, o, c):
    lt = d.index.tz_convert(tz); m = lt.hour * 60 + lt.minute
    d = d[(m >= o) & (m < c)]
    q = d.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    lq = q.index.tz_convert(tz); q["day"] = lq.date; q["m"] = lq.hour * 60 + lq.minute - o
    return q

def walk(H, L, C, day, i0, side, e, stop, tgt, n):
    for k in range(i0 + 1, min(i0 + 1 + n, len(C))):
        if day[k] != day[i0]: return side * (C[k - 1] - e)
        if (side == 1 and L[k] <= stop) or (side == -1 and H[k] >= stop): return side * (stop - e)
        if (side == 1 and H[k] >= tgt) or (side == -1 and L[k] <= tgt): return side * (tgt - e)
    return side * (C[min(i0 + n, len(C) - 1)] - e)

def spike(q, cost):
    H, L, O, C = q.high.values, q.low.values, q.open.values, q.close.values; day = q.day.values; rng = H - L
    ref = pd.Series(rng).groupby(day).transform("mean")
    dm = pd.Series(rng, index=q.index).groupby(day).mean(); prior = dm.shift(1).rolling(5).mean(); ref = q.day.map(prior).values
    out = []; busy = -1
    for i in range(1, len(C) - 2):
        j = i + 1
        if i <= busy or day[j] != day[i] or not (ref[i] > 0) or rng[i] < 3 * ref[i]: continue
        s = 1 if C[i] > O[i] else -1 if C[i] < O[i] else 0
        if s == 0: continue
        ext = (H[j] - H[i]) / rng[i] if s == 1 else (L[i] - L[j]) / rng[i]
        if not (ext > 0.25 and s * (C[j] - C[i]) > 0): continue
        e = C[j]; stop = L[j] if s == 1 else H[j]; risk = s * (e - stop)
        if risk <= 0: continue
        r = walk(H, L, C, day, j, s, e, stop, e + s * rng[i], 8) - cost
        out.append((q.index[j], r / risk)); busy = j + 8
    return out

def orb(q, cost):
    H, L, O, C = q.high.values, q.low.values, q.open.values, q.close.values; day = q.day.values; m = q.m.values
    out = []; d0 = None
    for i in range(len(C) - 1):
        if day[i] != d0: d0 = day[i]; hi = lo = None; done = False
        if m[i] < 30:
            hi = H[i] if hi is None else max(hi, H[i]); lo = L[i] if lo is None else min(lo, L[i]); continue
        if done or hi is None or m[i] >= 180: continue
        s = 1 if C[i] > hi else -1 if C[i] < lo else 0
        if s == 0: continue
        e = C[i]; stop = lo if s == 1 else hi; risk = s * (e - stop)
        if risk <= 0: continue
        r = walk(H, L, C, day, i, s, e, stop, e + s * 2 * risk, 10 ** 6) - cost
        out.append((q.index[i], r / risk)); done = True
    return out

def show(name, book, res):
    if len(res) < 10: log(f"  {name:22s} {book:5s} n{len(res)} (too few)"); return
    t = pd.DataFrame(res, columns=["t", "R"]); h = t.t < t.t.iloc[len(t) // 2]
    a, b = t[h].R, t[~h].R; yrs = (t.t.iloc[-1] - t.t.iloc[0]).days / 365.25
    flag = "  <-- both halves positive" if a.mean() > 0.05 and b.mean() > 0.05 else ""
    log(f"  {name:22s} {book:5s} n{len(t):4d} ({len(t)/max(yrs,0.1):5.0f}/yr) {t.R.mean():+.3f}R win {100*(t.R>0).mean():3.0f}%  H1 {a.mean():+.3f} H2 {b.mean():+.3f}{flag}")

if __name__ == "__main__":
    IG = [("US Tech 100", "data_nq_cache/nq_5m.csv", "America/New_York", 570, 960, 1.0),
          ("US 500", "data_ig_cache/USA500IDXUSD_5m.csv", "America/New_York", 570, 960, 0.4),
          ("Wall Street", "data_ig_cache/USA30IDXUSD_5m.csv", "America/New_York", 570, 960, 2.4),
          ("Germany 40", "data_ig_cache/DEUIDXEUR_5m.csv", "Europe/Berlin", 540, 1050, 1.2),
          ("FTSE 100", "data_ig_cache/GBRIDXGBP_5m.csv", "Europe/London", 480, 990, 1.0),
          ("Gold (NY)", "data_ig_cache/XAUUSD_5m.csv", "America/New_York", 480, 1020, 0.3),
          ("Gold (London)", "data_ig_cache/XAUUSD_5m.csv", "Europe/London", 480, 990, 0.3),
          ("GBP/USD (London)", "data_ig_cache/GBPUSD_IG_5m.csv", "Europe/London", 420, 1020, 0.9),
          ("GBP/USD (NY)", "data_ig_cache/GBPUSD_IG_5m.csv", "America/New_York", 480, 1020, 0.9),
          ("USD/JPY (Tokyo)", "data_ig_cache/USDJPY_IG_5m.csv", "Asia/Tokyo", 540, 1080, 0.7),
          ("USD/JPY (NY)", "data_ig_cache/USDJPY_IG_5m.csv", "America/New_York", 480, 1020, 0.7)]
    log("MARKET SEARCH 1 — honest fixed rules, costs in, R per trade; H1/H2 = first/second half of each market's data")
    for name, f, tz, o, c, cost in IG:
        d = load5(f); q = session15(d, tz, o, c)
        log(f"{name}: {q.index[0].date()} .. {q.index[-1].date()}, cost {cost} pts round trip")
        show(name, "SPIKE", spike(q, cost)); show(name, "ORB", orb(q, cost))
    for sym in ("BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "DOGEUSD", "AVAXUSD", "LINKUSD"):
        f = f"/home/claude/qlab/data_15m/{sym}.csv"
        if not os.path.exists(f): continue
        d = pd.read_csv(f); d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d = d[["open", "high", "low", "close"]].astype(float)
        lg = np.log(d) * 10000                                          # basis points, so a fixed cost works across the price history
        for nm, tz, o, c in ((f"{sym} (UTC day)", "UTC", 0, 1440), (f"{sym} (US hours)", "America/New_York", 570, 960)):
            q = session15(lg, tz, o, c)
            log(f"{nm}: {q.index[0].date()} .. {q.index[-1].date()}, cost 20bp round trip")
            show(nm, "SPIKE", spike(q, 20.0)); show(nm, "ORB", orb(q, 20.0))
    open(OUTF, "w").write("\n".join(LINES) + "\n")
