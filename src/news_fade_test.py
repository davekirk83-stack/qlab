"""Doc 156 — "Version 3" news-day fade (L2WTrades, doc 155), tested as written (rule 188). Pre-registered 28 Oct 2026 before any result.
DK: "Yes".
EVENTS  FOMC statements (2pm New York) and CPI releases (8:30am New York), 2022 - Oct 2026. Instruments: BTC (Coinbase 5-minute)
        and the Nasdaq-100 (Dukascopy USATECHIDXUSD ticks -> 5-minute mid).
RULES   P = the pre-news level (last price before the release).
        "Wait for the initial spike to finish": W = 15 min (variant 30 min). The spike direction is the side with the larger excursion
        from P inside the first W minutes; the spike extreme X is tracked until entry.
        "Identify the fake move, enter the reversal after the retrace": after W, the first 5-minute bar that CLOSES beyond the previous
        bar's low (spike up; mirror for down) while price is still on the spike side of P. Enter at that close, against the spike.
        Stop = X (+0.02%). Target = P. Otherwise exit at the close 4 hours after the release.
        No trade if the spike side of P is regained before a trigger. Costs: BTC 0.10%/side, NQ 1 point/side.
CONTROLS (200 draws): (a) TIMING — same events, a random 5-minute entry time between W and +2h, against the spike, same stop
        rule (extreme so far) and target; (b) DIRECTION — same trigger times, but WITH the spike (target = P mirrored, same R distance).
Trials: 2 waits x 2 instruments = 4."""
import os, sys, json, lzma, time, datetime as dt, urllib.request, numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
ROOT = "/home/claude/qlab"; CACHE = f"{ROOT}/data_events"; os.makedirs(CACHE, exist_ok=True)
FOMC = """2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14 2023-02-01 2023-03-22 2023-05-03 2023-06-14
2023-07-26 2023-09-20 2023-11-01 2023-12-13 2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10 2026-01-28 2026-03-18 2026-04-29 2026-06-17
2026-07-29 2026-09-16 2026-10-28""".split()
CPI = """2022-01-12 2022-02-10 2022-03-10 2022-04-12 2022-05-11 2022-06-10 2022-07-13 2022-08-10 2022-09-13 2022-10-13 2022-11-10 2022-12-13
2023-01-12 2023-02-14 2023-03-14 2023-04-12 2023-05-10 2023-06-13 2023-07-12 2023-08-10 2023-09-13 2023-10-12 2023-11-14 2023-12-12
2024-01-11 2024-02-13 2024-03-12 2024-04-10 2024-05-15 2024-06-12 2024-07-11 2024-08-14 2024-09-11 2024-10-10 2024-11-13 2024-12-11
2025-01-15 2025-02-12 2025-03-12 2025-04-10 2025-05-13 2025-06-11 2025-07-15 2025-08-12 2025-09-11 2025-10-24 2025-12-18
2026-01-13 2026-02-13 2026-03-11 2026-04-10 2026-05-12 2026-06-10 2026-07-14 2026-08-12 2026-09-11 2026-10-14""".split()
EVENTS = [(d, "FOMC", pd.Timestamp(d + " 14:00", tz="America/New_York").tz_convert("UTC")) for d in FOMC] + \
         [(d, "CPI", pd.Timestamp(d + " 08:30", tz="America/New_York").tz_convert("UTC")) for d in CPI]
UA = {"User-Agent": "Mozilla/5.0"}

def btc_bars(T):
    f = f"{CACHE}/BTC_{T:%Y%m%d%H%M}.csv"
    if os.path.exists(f): return pd.read_csv(f, parse_dates=["t"]).set_index("t")
    a, b = T - pd.Timedelta(hours=2), T + pd.Timedelta(hours=5)
    url = f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=300&start={a:%Y-%m-%dT%H:%M:%SZ}&end={b:%Y-%m-%dT%H:%M:%SZ}"
    for k in range(4):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30)); break
        except Exception: time.sleep(1 + k)
    else: return None
    d = pd.DataFrame(r, columns=["t", "low", "high", "open", "close", "vol"]); d["t"] = pd.to_datetime(d.t, unit="s", utc=True)
    d = d.set_index("t").sort_index()[["open", "high", "low", "close"]]; d.to_csv(f); return d

def duk_hour(d, h):
    url = f"https://datafeed.dukascopy.com/datafeed/USATECHIDXUSD/{d.year}/{d.month-1:02d}/{d.day:02d}/{h:02d}h_ticks.bi5"
    for k in range(4):
        try: raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read(); break
        except Exception as e:
            if "404" in str(e): return None
            time.sleep(2 + k * 2)
    else: return None
    if not raw: return None
    try: data = lzma.LZMADecompressor().decompress(raw)
    except Exception: return None
    n = len(data) // 20
    if not n: return None
    arr = np.frombuffer(data[:n * 20], dtype=np.dtype([("ms", ">u4"), ("ask", ">u4"), ("bid", ">u4"), ("av", ">f4"), ("bv", ">f4")]))
    base = pd.Timestamp(dt.datetime(d.year, d.month, d.day, h), tz="UTC")
    return pd.DataFrame({"t": base + pd.to_timedelta(arr["ms"].astype(np.int64), unit="ms"), "mid": (arr["ask"] + arr["bid"]) / 2000.0})

def nq_bars(T):
    f = f"{CACHE}/NQ_{T:%Y%m%d%H%M}.csv"
    if os.path.exists(f): return pd.read_csv(f, parse_dates=["t"]).set_index("t")
    hrs = [T.floor("h") + pd.Timedelta(hours=k) for k in range(-2, 5)]
    parts = [p for p in (duk_hour(h, h.hour) for h in hrs) if p is not None]
    if not parts: return None
    tk = pd.concat(parts).set_index("t").mid
    d = tk.resample("5min").agg(["first", "max", "min", "last"]).dropna(); d.columns = ["open", "high", "low", "close"]
    d.to_csv(f); return d

def simulate(d, T, W, cost, mode="rule", rng=None):
    pre = d[d.index < T]; post = d[d.index >= T]
    if len(pre) < 3 or len(post) < 30: return None
    P = float(pre.close.iloc[-1]); end = T + pd.Timedelta(hours=4)
    w = post[post.index < T + pd.Timedelta(minutes=W)]
    if len(w) < 2: return None
    up_exc, dn_exc = w.high.max() - P, P - w.low.min()
    s = 1 if up_exc >= dn_exc else -1                         # spike direction
    X = w.high.max() if s == 1 else w.low.min()
    after = post[(post.index >= T + pd.Timedelta(minutes=W)) & (post.index < end)]
    H, L, C, idx = after.high.values, after.low.values, after.close.values, after.index
    if mode == "timing":
        cands = [k for k in range(1, len(C)) if idx[k] <= T + pd.Timedelta(hours=2)]
        if not cands: return None
        k0 = int(rng.choice(cands))
    entry_k = None
    for k in range(1, len(C)):
        X = max(X, H[k]) if s == 1 else min(X, L[k])
        if (C[k] - P) * s <= 0: return None                   # back through P before any trigger: no trade
        if mode == "timing":
            if k == k0: entry_k = k; break
            continue
        if (s == 1 and C[k] < L[k - 1]) or (s == -1 and C[k] > H[k - 1]): entry_k = k; break
    if entry_k is None: return None
    e = C[entry_k]; stop = X * (1 + 0.0002 * s); side = -s     # trade AGAINST the spike
    tgt = P
    if mode == "with":                                         # control: same trigger, trade WITH the spike, same distances
        side = s; stop = e - (stop - e); tgt = e + (e - P)
    risk = abs(stop - e)
    if risk <= 0: return None
    for k in range(entry_k + 1, len(C)):
        if (side == -1 and H[k] >= stop) or (side == 1 and L[k] <= stop): px = stop; break
        if (side == -1 and L[k] <= tgt) or (side == 1 and H[k] >= tgt): px = tgt; break
    else: px = C[-1]
    pnl = (px - e) * side - 2 * cost(e)
    return pnl / risk, (P - e) * side / risk

if __name__ == "__main__":
    with ThreadPoolExecutor(6) as ex:
        B = dict(zip([e for e in EVENTS], ex.map(lambda ev: btc_bars(ev[2]), EVENTS)))
        N = dict(zip([e for e in EVENTS], ex.map(lambda ev: nq_bars(ev[2]), EVENTS)))
    print("BTC events with data:", sum(v is not None for v in B.values()), " NQ:", sum(v is not None for v in N.values()), flush=True)
    lines = []
    for name, DATA, cost in (("BTC", B, lambda p: 0.001 * p), ("NQ", N, lambda p: 1.0)):
        for W in (15, 30):
            res = {}
            for mode in ("rule", "with"):
                r = [simulate(d, ev[2], W, cost, mode) for ev, d in DATA.items() if d is not None]
                res[mode] = [x for x in r if x is not None]
            R = np.array([x[0] for x in res["rule"]]); tR = np.array([x[1] for x in res["rule"]])
            byk = {k: [simulate(d, ev[2], W, cost)[0] for ev, d in DATA.items() if d is not None and ev[1] == k and simulate(d, ev[2], W, cost) is not None] for k in ("FOMC", "CPI")}
            tm = []
            for j in range(200):
                rng = np.random.default_rng(j)
                r = [simulate(d, ev[2], W, cost, "timing", rng) for ev, d in DATA.items() if d is not None]
                r = [x[0] for x in r if x is not None]
                if r: tm.append(np.mean(r))
            tm = np.array(tm); Rw = np.array([x[0] for x in res["with"]])
            txt = (f"{name} wait {W}m: trades {len(R)} of {sum(v is not None for v in DATA.values())} events | win {100*(R>0).mean():.0f}% avg {R.mean():+.2f}R "
                   f"median {np.median(R):+.2f}R | target size {np.median(tR):.1f}R (median) | FOMC {np.mean(byk['FOMC']) if byk['FOMC'] else float('nan'):+.2f}R n{len(byk['FOMC'])} "
                   f"CPI {np.mean(byk['CPI']) if byk['CPI'] else float('nan'):+.2f}R n{len(byk['CPI'])}\n   random entry time (same side/stop/target): median {np.median(tm):+.2f}R, rule beats {100*(tm < R.mean()).mean():.0f}% "
                   f"| same trigger WITH the spike: {Rw.mean():+.2f}R")
            lines.append(txt); print(txt, flush=True)
    open(f"{ROOT}/runs/news_fade_test.txt", "w").write("\n".join(lines) + "\n")
