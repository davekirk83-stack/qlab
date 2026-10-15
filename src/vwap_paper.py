"""
VWAP DISLOCATION BOOK — forward paper tracker.

MANDATE: research and paper trading only. No live order, brokerage or exchange
account, credential, authentication, or committed capital of any size, on any
signal, under any circumstance. This file reads local archives and writes JSON.

Fourth registered strategy. Its history is the point: it was REJECTED on costs
(doc 51) and then recovered by fixing the implementation rather than the idea
(doc 52). The signal was always real; a 1.5 ATR stop on a 1-MINUTE bar is 0.19%
of price, so 8bp round trip cost 0.84R against a 0.10R edge. Moving to hourly
bars with wide stops makes the same edge cost 0.03R.

THE SPEC, FIXED AT REGISTRATION (2026-10-14) — doc 52
    universe    33 crypto perps, HOURLY bars
    indicator   ROLLING 72-hour volume-weighted price and volume-weighted SD.
                Rolling, not session-anchored: a session VWAP is statistically
                immature early in the day and measured NEGATIVE there
                (-0.118R over 42% of signals, doc 51). A rolling window is
                never immature, which removes the problem by construction
                rather than by a filter.
    signal      close <= 2.0 SD below the rolling VWAP
    entry       that close
    stop        4.0 ATR below entry  (WIDE ON PURPOSE: cost in R is
                2*fee/stop_distance, so a wide stop is what makes the edge
                survivable. Median stop 5.1% of price -> 8bp = 0.031R)
    exit        hold 96 hours, then exit at the close. No target.
    dedupe      one signal per 40 bars per symbol
    costs       8bp round trip assumed = 0.031R at the median stop

WHY IT SHOULD WORK
VWAP is the benchmark execution algorithms are graded against. A buy programme
running behind its benchmark is obliged to buy while price sits below VWAP —
mechanical demand, not sentiment. Nothing equivalent compels selling above it,
which is why the short side is NOT traded: it measured -0.002R. The asymmetry
was predicted by the mechanism before the result was seen (doc 50 rule 3).

BACKTEST FOR REFERENCE (not a promise) — time-matched controls throughout
    overall      n=1202  gross +0.318R  NET +0.286R  t=+4.67
    2025         n= 481  NET +0.270R  t=+3.56
    2026         n= 721  NET +0.299R  t=+3.37
    first half   n= 620  NET +0.163R  t=+2.69
    second half  n= 582  NET +0.419R  t=+3.87
    per symbol   26/33 beat the cost line
    the 1-week window FAILS the same tests (2025 +0.049R, first half -0.029R),
    which is evidence the 3-day result is not a lucky cell in the grid

PRE-REGISTERED KILL CRITERION — not amendable mid-run
    minimum evidence   120 MATURE trades (held the full 96h) or 6 months
    PASS               mean > +0.031R (the cost line, not zero) AND beats the
                       time-matched control
    FAIL               mean <= +0.031R at n=120
    early kill         any 25-trade block worse than -0.60R mean
    not evidence       a good week; the first 40 trades; one large winner
    amendment          ANY change to window, threshold, stop, hold or costs
                       voids the run and restarts the clock
"""
import os, glob, json, datetime as dt
import numpy as np, pandas as pd
import structure as ST

STATE = "/home/claude/qlab/runs/paper/vwap.json"
H1 = "/home/claude/qlab/data_1h_33"
WIN, THR, STOP_ATR, HOLD, GAP = 72, 2.0, 4.0, 96, 40
COST_R = 0.031

REGISTERED = {
    "registered_on": "2026-10-14",
    "spec_doc": "52-vwap-recovered-on-hourly",
    "history": "rejected on costs at 1-minute (doc 51), recovered by moving to "
               "hourly bars with wide stops (doc 52)",
    "universe": "33 crypto perps, hourly",
    "indicator": "rolling 72h volume-weighted price and SD (NOT session VWAP)",
    "signal": "close <= 2.0 SD below rolling VWAP",
    "stop": "4.0 ATR (wide on purpose — it is what makes cost survivable)",
    "exit": "hold 96 hours, no target",
    "minimum_evidence": "120 mature trades or 6 months",
    "pass": "mean > +0.031R (cost line) AND beats the time-matched control",
    "fail": "mean <= +0.031R at n=120",
    "early_kill": "any 25-trade block worse than -0.60R mean",
    "amendment": "any spec change voids the run and restarts the clock",
    "backtest": {"n": 1202, "gross": 0.318, "net": 0.286, "t": 4.67,
                 "y2025_net": 0.270, "y2026_net": 0.299,
                 "half1_net": 0.163, "half2_net": 0.419,
                 "symbols_beating_cost": "26/33"},
    "short_side_not_traded": "above-VWAP short measured -0.002R; the mechanism "
                             "predicts buy-side pressure only",
}


def load(path):
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    return df[~df.index.duplicated()]


def rolling_vwap(df, win=WIN):
    tp = (df.high + df.low + df.close) / 3
    v = df.volume.replace(0, np.nan)
    pv = (tp * v).rolling(win).sum(); cv = v.rolling(win).sum()
    vw = pv / cv
    var = ((tp - vw) ** 2 * v).rolling(win).sum() / cv
    return vw.values, np.sqrt(var.values)


def score(df, bar, entry, stop, hold=HOLD):
    """Stop-only, held `hold` bars. resolved=0 while still too young."""
    L, C = df.low.values, df.close.values
    risk = entry - stop
    if risk <= 0:
        return None
    last = bar + hold
    n = len(C)
    for j in range(bar + 1, min(last, n - 1) + 1):
        if L[j] <= stop:
            return dict(R=-1.0, win=0.0, resolved=1, bars=j - bar)
    if last > n - 1:
        return dict(R=float((C[n - 1] - entry) / risk), win=np.nan,
                    resolved=0, bars=n - 1 - bar)
    r = float((C[last] - entry) / risk)
    return dict(R=r, win=float(r > 0), resolved=1, bars=hold)


def state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    return dict(registered=REGISTERED, started=str(dt.date.today()),
                seen=[], trades=[], watermarks={})


def refresh_open(s):
    by = {}
    for t in s["trades"]:
        if t.get("mature"):
            continue
        by.setdefault(t["sym"], []).append(t)
    closed = 0
    for sym, items in by.items():
        p = f"{H1}/{sym}.csv"
        if not os.path.exists(p):
            continue
        df = load(p)
        idx = {str(x): i for i, x in enumerate(df.index)}
        for t in items:
            i = idx.get(t["ts"])
            if i is None:
                continue
            r = score(df, i, t["entry"], t["stop"])
            if not r:
                continue
            t.update(R=round(r["R"], 4), resolved=r["resolved"],
                     win=(None if r["resolved"] == 0 else bool(r["win"])),
                     bars_since=int(len(df) - 1 - i),
                     mature=bool(len(df) - 1 - i >= HOLD))
            if t["mature"]:
                closed += 1
    return closed


def step():
    s = state()
    s.setdefault("watermarks", {})
    closed = refresh_open(s)
    seen = set(s["seen"]); new = 0
    for p in sorted(glob.glob(f"{H1}/*.csv")):
        sym = os.path.basename(p)[:-4]
        try:
            df = load(p)
        except Exception:
            continue
        if "volume" not in df.columns or len(df) < 500:
            continue
        last_ts = str(df.index[-1])
        if sym not in s["watermarks"]:
            s["watermarks"][sym] = last_ts      # first sight: take no history
            continue
        wm = s["watermarks"][sym]; s["watermarks"][sym] = last_ts
        C = df.close.values; a = ST.atr(df).bfill().values; n = len(C)
        vw, sd = rolling_vwap(df)
        with np.errstate(invalid="ignore"):
            z = (C - vw) / np.where(sd > 0, sd, np.nan)
        prev = -10 ** 9
        for i in np.flatnonzero(z <= -THR):
            if i < 300 or a[i] <= 0 or i - prev < GAP:
                continue
            ts = str(df.index[i])
            if ts <= wm:
                continue
            prev = i
            stop = C[i] - STOP_ATR * a[i]
            r = score(df, i, C[i], stop)
            if not r:
                continue
            key = f"{sym}|{ts}"
            if key in seen:
                continue
            seen.add(key)
            s["trades"].append(dict(
                sym=sym, ts=ts, entry=round(float(C[i]), 8),
                stop=round(float(stop), 8), z=round(float(z[i]), 3),
                risk_pct=round(float(STOP_ATR * a[i] / C[i]), 5),
                R=round(r["R"], 4), resolved=r["resolved"],
                win=(None if r["resolved"] == 0 else bool(r["win"])),
                bars_since=int(n - 1 - i), mature=bool(n - 1 - i >= HOLD)))
            new += 1
    s["seen"] = sorted(seen)[-40000:]
    json.dump(s, open(STATE, "w"), indent=1)
    print(f"  {new} new signals, {closed} matured")
    return s


def report(s):
    T = pd.DataFrame(s["trades"])
    print("=" * 84)
    print(f"  VWAP DISLOCATION BOOK — forward paper, started {s['started']}")
    print("=" * 84)
    print("  Research only. No order, no account, no capital.\n")
    if not len(T):
        print("  no signals yet"); return
    M = T[T.mature.fillna(False)]
    print(f"  logged {len(T)}   mature {len(M)}   still open {len(T)-len(M)}")
    if len(M):
        r = M.R.values
        se = r.std(ddof=1) / np.sqrt(len(r)) if len(r) > 1 else np.nan
        print(f"  mature mean {r.mean():+.3f}R   net of cost "
              f"{r.mean()-COST_R:+.3f}R   win {float((r>0).mean())*100:.1f}%"
              + (f"   t={r.mean()/se:+.2f}" if se == se and se > 0 else ""))
    n = len(M)
    print(f"\n  evidence: {n}/120 mature trades")
    print(f"  cost line: +{COST_R:.3f}R — the spec must clear this, not zero")
    if n < 120:
        print("  -> NO VERDICT. Below the minimum. This is not a result yet.")


if __name__ == "__main__":
    report(step())
