"""
CASCADE BOUNCE — forward paper tracker.

MANDATE: research and paper trading only. No live order, brokerage or exchange
account, credential, authentication, or committed capital of any size, on any
signal, under any circumstance. This file reads a public archive and writes JSON.

HOW IT RUNS
Binance Vision publishes a daily 1-minute kline file per symbol. This job runs
once a day, fetches the most recent complete day, finds every cascade signal in
it, applies the level filter, simulates the trade bar by bar, and appends the
result to a journal. No live connection and no order path exists.

SPEC v2 — RE-REGISTERED 2026-10-14 (doc 53). v1 is void.

WHAT CHANGED AND WHY
v1 waited for the first green minute and bought the NEXT OPEN with a market
order. That chases the turn: the most expensive possible entry, at the moment
the book is thinnest. Doc 52 measured its breakeven slippage at ~24bp each way
against a median entry bar spanning 0.96% of price — i.e. probably not viable.

DK had already given the answer, twice, and it was not implemented:
    "Isn't this a place where you would try to scale into a position, perhaps?"
    "If it can bounce after the cascade, hold for 5 or 10 minutes, it then
     bounces significantly"

LADDERED ENTRY. On detection, rest limit bids at -0.5/-1.0/-1.5/-2.0/-2.5%
below the signal close. Each rung fills only if price trades through it, and
every fill is a MAKER fill. The deeper the flush, the more rungs fill and the
better the average entry. Measured head to head on the same events:

    slippage on market entries      v1 MARKET      v2 LADDER
       4bp                          +0.341%        +0.665%   win 77.1%
      15bp                          +0.156%        +0.641%
      40bp                          -0.207%        +0.586%
    paired difference +0.483pp to +0.994pp, t=+3.94 to +7.30

The ladder is near-IMMUNE to slippage (0.665% -> 0.586% across a tenfold change)
because maker fills do not pay the spread. It is also simply a better trade:
win rate 66.2% -> 77.1%. 17.6% of cascades never reach the first rung and are
correctly recorded as no-trades.

THE SPEC (v2)
    universe    18 crypto perps with sufficient absolute minute volatility
                (screen on 5-min SD, not on name or liquidity)
    signal      close falls >= 3% over 5 minutes
    ENTRY       LADDER of resting LIMIT bids at -0.5/-1.0/-1.5/-2.0/-2.5%
                below the signal bar's close. Rungs fill only if price trades
                through them, within 60 minutes. Position = however many rungs
                filled; average entry = mean of filled rungs. Maker fee only.
                If no rung fills, there is NO TRADE.
    LEVEL FILTER  the cascade low must be within 0.2% of a level visible from
                hourly bars BEFORE the cascade: prior day low, prior week low,
                fib retracement, liquidation band, or hourly swing low
    exits       TP +1.5% / SL -2.0% from the AVERAGE entry, 60-minute cap
    costs       maker 2bp on entry and on a TP exit; taker 5bp plus slippage
                on a stop exit. Real Binance USDT-M VIP 0 schedule.
    RISK        a deep flush fills every rung and leaves a full position in a
                falling market. This is the genuine risk of the method and is
                modelled, not assumed away.
    sizing      not yet specified — overlapping positions unmodelled

BACKTEST FOR REFERENCE (not a promise)
    unfiltered  n=497  +0.361%/trade  win 67.8%  t=+5.37
    filtered    n=248  +0.740%/trade  win 79.0%
    open air    n= 78  -0.392%/trade  win 44.9%   <- the filter must keep excluding these

PRE-REGISTERED KILL CRITERION — not amendable mid-run
    minimum evidence   100 closed trades or 6 months, whichever first
    PASS               mean > 0 net of costs AND filtered beats open-air
    FAIL               mean <= 0 at n=100
    early kill         any 20-trade block worse than -2% mean
    not evidence       a good week; the first 30 trades; a single large winner
    amendment          ANY change to universe, signal, filter, exits or costs
                       voids the run and restarts the clock
"""
import os, io, json, zipfile, urllib.request, datetime as dt
import numpy as np, pandas as pd

STATE = "/home/claude/qlab/runs/paper/cascade.json"
BASE = "https://data.binance.vision/data/futures/um/daily/klines"
H1 = "/home/claude/qlab/data_1h_33"
SYMS = ["SOLUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT",
        "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "INJUSDT",
        "TIAUSDT", "ADAUSDT", "FILUSDT", "ETHUSDT", "BNBUSDT", "BTCUSDT"]

DROP, WIN = 0.03, 5
RUNGS = (0.005, 0.010, 0.015, 0.020, 0.025)
MAKER, TAKER = 2.0/10000, 5.0/10000
TP, SL, MAXMIN, SLIP = 0.015, 0.020, 60, 0.0004
LEVEL_TOL = 0.002

REGISTERED = {
    "spec_version": 2,
    "registered_on": "2026-10-14",
    "v1_voided": "market entry at the first green minute; breakeven slippage "
                 "~24bp (doc 52). Replaced by laddered maker entry (doc 53).",
    "entry": "ladder of limit bids at -0.5/-1.0/-1.5/-2.0/-2.5% below signal close",
    "spec_docs": ["35-the-minute-scale-cascade-bounce",
                  "37-levels-refine-the-cascade-entry",
                  "53-laddered-entry"],
    "minimum_evidence": "100 closed trades or 6 months, whichever first",
    "pass": "mean > 0 net of costs AND filtered beats open-air",
    "fail": "mean <= 0 at n=100",
    "early_kill": "any 20-trade block worse than -2% mean",
    "not_evidence": ["a good week", "the first 30 trades", "a single large winner"],
    "amendment": "any change to universe, signal, filter, exits or costs voids the run",
    "backtest_reference": {"ladder_mean_4bp": 0.00665, "ladder_mean_40bp": 0.00586,
                           "market_mean_4bp": 0.00341, "market_mean_40bp": -0.00207,
                           "ladder_win": 0.771, "paired_edge_t": "+3.94 to +7.30",
                           "rungs_filled_mean": 2.93, "no_fill_share": 0.176,
                           "caveat": "13 months; ladder is near-immune to slippage "
                                     "because fills are maker"},
}

COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
        "qav", "trades", "tbbav", "tbqav", "ignore"]


def fetch_day(sym, day):
    url = f"{BASE}/{sym}/1m/{sym}-1m-{day}.zip"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
            df = pd.read_csv(z.open(z.namelist()[0]), header=None, names=COLS,
                             usecols=["open_time", "open", "high", "low", "close"])
    except Exception:
        return None
    if str(df.open_time.iloc[0]).startswith("open"):
        df = df.iloc[1:]
    df["dt"] = pd.to_datetime(pd.to_numeric(df.open_time, errors="coerce"), unit="ms")
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["dt", "close"]).set_index("dt").sort_index()


def levels_for(sym, when):
    """Levels from hourly bars strictly before `when`."""
    p = f"{H1}/{sym}.csv"
    if not os.path.exists(p):
        return []
    h = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
    h = h[h.index < when]
    if len(h) < 200:
        return []
    w = h.iloc[-400:]
    H, L, C = w.high.values, w.low.values, w.close.values
    out = []
    lo_i = int(np.argmin(L[-240:])) + max(0, len(L) - 240)
    hi_i = int(np.argmax(H[-240:])) + max(0, len(H) - 240)
    if hi_i > lo_i and H[hi_i] > L[lo_i]:
        a, b = L[lo_i], H[hi_i]
        for f in (0.382, 0.5, 0.618, 0.786):
            out.append((b - (b - a) * f, "fib"))
    piv = (w.low == w.low.rolling(7, center=True).min()).fillna(False).values
    pidx = np.flatnonzero(piv)
    if len(pidx) >= 3:
        p3 = pidx[-3:]
        A = np.polyfit(p3, L[p3], 1)
        out.append((A[0] * (len(w) - 1) + A[1], "trendline"))
    for j in pidx[-4:]:
        out.append((L[j], "prior_swing"))
    out.append((L[-24:].min(), "prior_day_low"))
    out.append((L[-168:].min(), "prior_week_low"))
    ref = float(np.mean(C[-48:]))
    for lev in (10, 25, 50, 100):
        out.append((ref * (1 - 1.0 / lev), f"liq_{lev}x"))
    return [(x, k) for x, k in out if np.isfinite(x) and x > 0]


def scan_day(sym, day):
    m = fetch_day(sym, day)
    if m is None or len(m) < 200:
        return []
    C, L, H, O = m.close.values, m.low.values, m.high.values, m.open.values
    mv = C / pd.Series(C).shift(WIN).values - 1
    sig = np.flatnonzero(mv < -DROP)
    out, last = [], -10**9
    for i in sig:
        if i <= last or i + MAXMIN + 5 >= len(C):
            continue
        # ---- LADDERED MAKER ENTRY (spec v2) ----
        ref = C[i]
        rung_px = [ref * (1 - r) for r in RUNGS]
        filled, first_fill = [], None
        for k in range(i, min(i + MAXMIN, len(C))):
            for rp in rung_px:
                if rp not in filled and L[k] <= rp:
                    filled.append(rp)
                    if first_fill is None:
                        first_fill = k
            if len(filled) == len(rung_px):
                break
        if not filled:
            continue                      # no rung filled: there was no trade
        low = L[i:max(i + 1, (first_fill or i) + 1)].min()
        lv = levels_for(sym, m.index[i])
        if lv:
            d, kind = min(((abs(low / p - 1), k) for p, k in lv), key=lambda x: x[0])
        else:
            d, kind = 9.9, "none"
        px = float(np.mean(filled)) * (1 + MAKER)
        T = px * (1 + TP); S = px * (1 - SL)
        ret, ex, how = None, None, None
        for k in range(first_fill + 1, min(first_fill + 1 + MAXMIN, len(C))):
            if L[k] <= S:
                ret = (S * (1 - SLIP - TAKER)) / px - 1; ex = k; how = "stop"; break
            if H[k] >= T:
                ret = (T * (1 - MAKER)) / px - 1; ex = k; how = "target"; break
        if ex is None:
            k = min(first_fill + MAXMIN, len(C) - 1)
            ret = (C[k] * (1 - MAKER)) / px - 1; ex = k; how = "time"
        out.append(dict(sym=sym, day=day, entry_time=str(m.index[first_fill]),
                        entry=round(float(px), 6), ret=round(float(ret), 6),
                        mins=int(ex - first_fill), exit=how,
                        rungs=len(filled),
                        level_dist=round(float(d), 5), nearest_level=kind,
                        taken=bool(d <= LEVEL_TOL)))
        last = ex
    return out


def load():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    return dict(registered=REGISTERED, started=str(dt.date.today()),
                days_done=[], trades=[])


def step(days_back=3):
    s = load()
    today = dt.date.today()
    for k in range(2, 2 + days_back):
        day = str(today - dt.timedelta(days=k))
        if day in s["days_done"]:
            continue
        found = []
        for sym in SYMS:
            found += scan_day(sym, day)
        s["days_done"].append(day)
        s["trades"] += found
        print(f"  {day}: {len(found)} signals "
              f"({sum(1 for x in found if x['taken'])} pass the level filter)", flush=True)
    s["days_done"] = sorted(set(s["days_done"]))[-400:]
    json.dump(s, open(STATE, "w"), indent=1)
    return s


def report(s):
    T = pd.DataFrame(s["trades"])
    print("=" * 78)
    print(f"  CASCADE BOUNCE — forward paper, started {s['started']}")
    print("=" * 78)
    print("  Research only. No order, no account, no capital.\n")
    if not len(T):
        print("  no signals yet"); return
    for lab, sub in (("TAKEN (within 0.2% of a level)", T[T.taken]),
                     ("skipped (open air)", T[~T.taken]),
                     ("all signals", T)):
        if len(sub) < 1:
            continue
        r = sub.ret.values
        se = r.std(ddof=1) / np.sqrt(len(r)) if len(r) > 1 else np.nan
        print(f"  {lab:34s} n={len(r):4d} mean {r.mean()*100:+7.3f}% "
              f"win {float((r>0).mean())*100:5.1f}%"
              + (f"  t={r.mean()/se:+5.2f}" if se and se == se and se > 0 else ""))
    n = int(T.taken.sum())
    print(f"\n  evidence: {n}/100 taken trades "
          f"({n/100*100:.0f}% of the pre-registered minimum), "
          f"{len(s['days_done'])} days scanned")
    if n < 100:
        print("  -> NO VERDICT. Below the minimum. This is not a result yet.")


if __name__ == "__main__":
    import sys
    s = step(days_back=int(sys.argv[1]) if len(sys.argv) > 1 else 3)
    report(s)
