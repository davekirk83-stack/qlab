"""
CONFLUENCE PATTERN BOOK — forward paper tracker.

MANDATE: research and paper trading only. No live order, brokerage or exchange
account, credential, authentication, or committed capital of any size, on any
signal, under any circumstance. This file reads a public archive and writes JSON.

Second forward-tracked strategy in the programme, alongside the cascade bounce
(cascade_paper.py). Same discipline: the spec is FIXED at registration, the kill
criterion is pre-registered and not amendable mid-run, and any change to the
spec voids the run and restarts the clock.

THE SPEC, FIXED AT REGISTRATION (2026-10-14) — docs 39 and 40
    universe    33 crypto perps, HOURLY bars
                (ETFs excluded: patterns lose at every score quartile, doc 39)
    patterns    double bottom, inverse head and shoulders, ascending triangle
                detected from ATR-prominence major pivots
                FLAGS EXCLUDED — measured -0.199R vs control, t=-12.46
    entry       the close that clears the pattern's neckline / resistance
    stop        the pattern's own structural low
    target      the pattern's own measured move
    gates       (a) confluence score in the TOP QUARTILE of the calibrated
                    distribution (weights frozen from the in-sample half)
                (b) the bar at the structural low closed in the BOTTOM THIRD
                    of its range  — doc 40, replicated in three datasets
    costs       8bp round trip assumed = 0.017R at the median 4.67% stop
    sizing      not specified — overlapping positions unmodelled

BACKTEST FOR REFERENCE (not a promise)
    all hourly patterns        n=18547   +0.006R
    top confluence quartile    n=  790   +0.055R   t=+1.66  (out-of-sample half)
    weak-low gate alone        n= 4364   +0.035R   t=+2.67
    flags (excluded)           n= 5218   -0.231R   t=-12.46

PRE-REGISTERED KILL CRITERION — not amendable mid-run
    minimum evidence   150 resolved trades or 6 months, whichever first
    PASS               mean > +0.017R (the cost line) AND gated beats ungated
    FAIL               mean <= 0 at n=150
    early kill         any 30-trade block worse than -0.40R mean
    not evidence       a good week; the first 50 trades; one large winner
    amendment          ANY change to universe, patterns, gates, stops, targets
                       or costs voids the run and restarts the clock

WHY THE BAR IS HIGHER THAN THE CASCADE'S
The cascade backtest carried t=+5.37 on a mechanism (forced liquidation into a
thin book). This carries t=+1.66 on a ranking whose component weights do not
agree between universes (doc 39). Weaker evidence, so more of it is required
before it means anything.
"""
import os, io, json, zipfile, urllib.request, datetime as dt
import numpy as np, pandas as pd
import structure as ST
import patterns_proper as PP
import confluence_scanner as CS

STATE = "/home/claude/qlab/runs/paper/patterns.json"
WEIGHTS = "/home/claude/qlab/runs/confluence/crypto_hourly_weights.json"
BASE = "https://data.binance.vision/data/futures/um/daily/klines"
H1 = "/home/claude/qlab/data_1h_33"

DETECTORS = [PP.d_double_bottom, PP.d_inv_hs, PP.d_asc_triangle]
COST_R = 0.017
MAXBARS = PP.MAXBARS

REGISTERED = {
    "registered_on": "2026-10-14",
    "spec_docs": ["39-patterns-done-properly", "40-candles-as-triggers"],
    "universe": "33 crypto perps, hourly",
    "patterns": ["double_bottom", "inv_hs", "asc_triangle"],
    "excluded": {"flag": "-0.199R vs control, t=-12.46",
                 "etf": "loses at every score quartile"},
    "gates": ["confluence score in top quartile",
              "structural low closed in bottom third of its range"],
    "minimum_evidence": "150 resolved trades or 6 months, whichever first",
    "pass": "mean > +0.017R (cost line) AND gated beats ungated",
    "fail": "mean <= 0 at n=150",
    "early_kill": "any 30-trade block worse than -0.40R mean",
    "not_evidence": ["a good week", "the first 50 trades", "one large winner"],
    "amendment": "any spec change voids the run and restarts the clock",
    "backtest_reference": {"all": 0.006, "top_quartile": 0.055,
                           "t": 1.66,
                           "caveat": "component weights unstable across "
                                     "universes; ranking works, attribution "
                                     "does not"},
}


def load_weights():
    if not os.path.exists(WEIGHTS):
        return None
    return json.load(open(WEIGHTS))


def weak_low(df, g):
    """Gate (b): did the bar at the structural low close in the bottom third?"""
    j = None
    L = df.low.values
    best = np.inf
    for k in range(max(0, g["bar"] - 200), g["bar"] + 1):
        d = abs(L[k] - g["stop"])
        if d < best:
            best, j = d, k
    if j is None:
        return False, np.nan
    h, l, c = df.high.values[j], L[j], df.close.values[j]
    if h - l <= 0:
        return False, np.nan
    pos = (c - l) / (h - l)
    return bool(pos < 0.3333), float(pos)


def scan_symbol(sym, W, cutoff, watermark=None):
    """Patterns completing STRICTLY AFTER this symbol's watermark.

    The original guard (`bar < len(df) - MAXBARS - 1`) admitted any pattern in
    the trailing 120 bars, i.e. 129 historical setups on day one. A forward
    journal must contain only what did not exist when it started."""
    p = f"{H1}/{sym}.csv"
    if not os.path.exists(p):
        return []
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
    df = df[~df.index.duplicated()]
    if len(df) < 500:
        return []
    try:
        lows, highs = PP.confirmed_pivots(df)
    except Exception:
        return []
    if len(lows) < 4 or len(highs) < 4:
        return []
    lows_i = [i for i, _ in lows]; highs_i = [i for i, _ in highs]
    a = ST.atr(df).bfill().values
    ma = df.close.rolling(200).mean().values
    v = df.volume.replace(0, np.nan) if "volume" in df.columns else None
    vr = (v / v.rolling(20).mean()).fillna(1.0).values if v is not None \
        else np.ones(len(df))
    grid = CS.level_grid(df, lows_i, highs_i)
    C = df.close.values
    out = []
    for det in DETECTORS:
        try:
            sigs = det(df, lows, highs)
        except Exception:
            continue
        for g in sigs:
            b = g["bar"]
            if watermark is not None and str(df.index[b]) <= watermark:
                continue                   # existed before we started watching
            r = PP.resolve(df, b, g["entry"], g["stop"], g["target"])
            if not r:
                continue
            d = CS.nearest_fast(grid, b, g["stop"])
            feat = dict(
                f_level=float(d <= 0.5 * a[b]) if a[b] > 0 else 0.0,
                f_trend=float(np.isfinite(ma[b]) and C[b] > ma[b]),
                f_volume=float(vr[b] > 1.5),
                f_rr=float(r["rr"] >= 1.5),
            )
            sc = W["base"] + W["pattern"].get(g["name"], 0.0) + \
                sum(W["weights"][k] * feat[k] for k in W["weights"])
            wl, pos = weak_low(df, g)
            out.append(dict(
                sym=sym, name=g["name"], ts=str(df.index[b]),
                entry=round(float(g["entry"]), 8),
                stop=round(float(g["stop"]), 8),
                target=round(float(g["target"]), 8),
                rr=round(float(r["rr"]), 3), score=round(float(sc), 5),
                low_pos=round(pos, 3) if pos == pos else None,
                gate_weak_low=wl, gate_score=bool(sc >= cutoff),
                taken=bool(wl and sc >= cutoff),
                resolved=int(r["resolved"]),
                R=(0.0 if r["resolved"] == 0
                   else (round(float(r["rr"]), 3) if r["win"] == 1 else -1.0)),
                win=(None if r["resolved"] == 0 else bool(r["win"] == 1)),
            ))
    return out


def cutoff_from_history():
    """Top-quartile threshold, FROZEN at registration.

    This used to be recomputed from the 18,547-row calibration CSV. That file is
    too large to carry in the project, so in a fresh scheduled session it did not
    exist, step() returned None, and the tracker recorded nothing — silently,
    every day. The threshold is now stored in the weights file, which means it is
    also genuinely frozen: recomputing it each run would have let the gate drift
    with the data, which is a spec amendment by the back door.

    The CSV path is kept only as a fallback for local work.
    """
    W = load_weights()
    if W is None:
        return None, None
    if "cutoff_top_quartile" in W:
        return float(W["cutoff_top_quartile"]), W
    f = "/home/claude/qlab/runs/confluence/crypto_hourly_setups.csv"
    if not os.path.exists(f):
        return None, None
    T = pd.read_csv(f)
    s = (W["base"] + T.name.map(lambda n: W["pattern"].get(n, 0.0))
         + sum(W["weights"][k] * T[k] for k in W["weights"]))
    return float(np.quantile(s, 0.75)), W


def load():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    return dict(registered=REGISTERED, started=str(dt.date.today()),
                seen=[], trades=[], watermarks={})


def step():
    cutoff, W = cutoff_from_history()
    if W is None:
        print("  calibration missing — run confluence_scanner.py first")
        return None
    s = load()
    s.setdefault("cutoff", cutoff)
    s.setdefault("watermarks", {})
    syms = [os.path.basename(f)[:-4]
            for f in sorted(__import__("glob").glob(f"{H1}/*.csv"))]
    seen = set(s["seen"])
    new = 0
    for sym in syms:
        p = f"{H1}/{sym}.csv"
        try:
            last = str(pd.read_csv(p, parse_dates=["date"])
                       .set_index("date").sort_index().index[-1])
        except Exception:
            continue
        if sym not in s["watermarks"]:
            s["watermarks"][sym] = last      # first sight: take nothing historical
            continue
        wm = s["watermarks"][sym]
        s["watermarks"][sym] = last
        for t in scan_symbol(sym, W, s["cutoff"], watermark=wm):
            key = f"{t['sym']}|{t['ts']}|{t['name']}"
            if key in seen:
                continue
            seen.add(key); s["trades"].append(t); new += 1
    s["seen"] = sorted(seen)[-20000:]
    json.dump(s, open(STATE, "w"), indent=1)
    print(f"  {new} new setups recorded "
          f"({sum(1 for t in s['trades'] if t['taken'])} taken in total)")
    return s


def report(s):
    T = pd.DataFrame(s["trades"])
    print("=" * 84)
    print(f"  CONFLUENCE PATTERN BOOK — forward paper, started {s['started']}")
    print("=" * 84)
    print("  Research only. No order, no account, no capital.\n")
    if not len(T):
        print("  no setups yet"); return
    for lab, sub in (("TAKEN (both gates)", T[T.taken]),
                     ("score gate only", T[T.gate_score & ~T.gate_weak_low]),
                     ("weak-low gate only", T[T.gate_weak_low & ~T.gate_score]),
                     ("all detected setups", T)):
        if len(sub) < 1:
            continue
        r = sub.R.values
        res = sub[sub.resolved == 1]
        se = r.std(ddof=1) / np.sqrt(len(r)) if len(r) > 1 else np.nan
        hit = res.win.mean() * 100 if len(res) else float("nan")
        print(f"  {lab:24s} n={len(r):4d}  resolved={len(res):4d}  "
              f"hit {hit:5.1f}%  {r.mean():+6.3f}R"
              + (f"  t={r.mean()/se:+5.2f}" if se and se == se and se > 0 else ""))
    n = int((T.taken & (T.resolved == 1)).sum())
    print(f"\n  evidence: {n}/150 resolved taken trades "
          f"({n/150*100:.0f}% of the pre-registered minimum)")
    print(f"  cost line: +{COST_R:.3f}R — the spec must clear this, not zero")
    if n < 150:
        print("  -> NO VERDICT. Below the minimum. This is not a result yet.")


if __name__ == "__main__":
    s = step()
    if s:
        report(s)
