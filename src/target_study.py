"""
IMPROVEMENT STUDY 1 — the target is the weakest part of every strategy.

DK: "We are trying to improve this strategy every day. If you find any
deductions or new info to improve what we're doing, bring it on board."

THE DEDUCTION, from today's own numbers
Three separate results point at the same flaw:
  flags           26% hit at 2.3 R:R  -> -0.231R  (doc 39, killed)
  patterns        hit 53-72% but R:R 0.71-0.99   (doc 39)
  retests         hit 13-24% at R:R 6-9          (doc 42)
Every one of those uses the MEASURED MOVE as its target. When the measured move
is small the hit rate is high and the payoff is poor; when it is large the
payoff is great and almost nothing reaches it. That is not a target rule, it is
an accident of how far the base happened to be from the level.

So the target is doing real damage and no one has tested an alternative. This
study holds entry and stop FIXED — they are the parts that passed — and varies
only the exit.

CANDIDATES
  measured      the current rule: level + base height
  atr_N         N x ATR from entry, a volatility-scaled target
  rr_N          a fixed N:1 multiple of the actual stop distance
  struct        the next structural level above entry (structure.py) — DK's
                own instinct from doc 30, "are we going back to arbitrary TPs?"
  trail_N       no target: trail a stop N x ATR below the running high
  time_N        no target: exit at the close N bars later

Scored in R against each setup's OWN risk, so the comparison is honest across
instruments and across targets of different sizes. Same universe split as the
registered retest book: diagonals anywhere, ETF horizontals.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
import patterns_proper as PP
import retest as RT
from levels_general import load_universe

MAXBARS = 120


def exits(df, bar, entry, stop, measured, levels_above):
    """Return {name: R} for every candidate exit on one setup."""
    H, L, C = df.high.values, df.low.values, df.close.values
    a = ST.atr(df).bfill().values
    n = len(df)
    risk = entry - stop
    if risk <= 0 or not np.isfinite(risk):
        return None
    end = min(bar + 1 + MAXBARS, n)
    if end - bar < 10:
        return None
    out = {}

    def race(target):
        for j in range(bar + 1, end):
            if L[j] <= stop:
                return -1.0
            if H[j] >= target:
                return (target - entry) / risk
        return (C[end - 1] - entry) / risk        # unresolved: mark to market

    out["measured"] = race(measured)
    for k in (1, 2, 3, 4, 6):
        out[f"atr_{k}"] = race(entry + k * a[bar]) if a[bar] > 0 else np.nan
    for k in (1, 1.5, 2, 3, 5):
        out[f"rr_{k}"] = race(entry + k * risk)
    nxt = [p for p in levels_above if p > entry * 1.001]
    out["struct"] = race(min(nxt)) if nxt else np.nan

    # trailing stops — no target at all
    for k in (1, 2, 3):
        if a[bar] <= 0:
            out[f"trail_{k}"] = np.nan; continue
        peak, s, r = entry, stop, None
        for j in range(bar + 1, end):
            if L[j] <= s:
                r = (s - entry) / risk; break
            peak = max(peak, H[j])
            s = max(s, peak - k * a[j])
        out[f"trail_{k}"] = r if r is not None else (C[end - 1] - entry) / risk

    # pure time exits
    for k in (10, 20, 40, 80):
        j = min(bar + k, n - 1)
        hit = False
        for q in range(bar + 1, j + 1):
            if L[q] <= stop:
                out[f"time_{k}"] = -1.0; hit = True; break
        if not hit:
            out[f"time_{k}"] = (C[j] - entry) / risk
    return out


def collect(which):
    panel = load_universe(which)
    rows = []
    for s, df in panel.items():
        if len(df) < 600:
            continue
        try:
            lows, highs = PP.confirmed_pivots(df)
        except Exception:
            continue
        if len(lows) < 4 or len(highs) < 4:
            continue
        lows_i = [i for i, _ in lows]; highs_i = [i for i, _ in highs]
        try:
            import confluence_scanner as CS
            grid = CS.level_grid(df, lows_i, highs_i)
        except Exception:
            grid = {}
        H = df.high.values
        for diag, setups in ((True, RT.diagonal_setups(df, highs, lows)),
                             (False, RT.find_setups(df, highs, lows))):
            # registered spec: diagonals anywhere, horizontals on ETFs only
            if not diag and which != "etf":
                continue
            for u in setups:
                rb = u.get("retest_bar")
                if rb is None or u.get("failed"):
                    continue
                stop = u.get("retest_stop") or u["stop"]
                entry = df.close.values[rb]
                k = max(200, (rb // 50) * 50)
                lv = grid.get(k, np.array([]))
                e = exits(df, rb, entry, stop, u["target"], list(lv))
                if e is None:
                    continue
                e["sym"] = s; e["diagonal"] = diag
                rows.append(e)
    return pd.DataFrame(rows)


NAMES = (["measured"] + [f"atr_{k}" for k in (1, 2, 3, 4, 6)]
         + [f"rr_{k}" for k in (1, 1.5, 2, 3, 5)] + ["struct"]
         + [f"trail_{k}" for k in (1, 2, 3)]
         + [f"time_{k}" for k in (10, 20, 40, 80)])


def summarise(T, label):
    print("=" * 84)
    print(f"  {label}   n={len(T)} setups")
    print("=" * 84)
    rows = []
    for nm in NAMES:
        if nm not in T.columns:
            continue
        r = T[nm].dropna().values
        if len(r) < 60:
            continue
        se = r.std(ddof=1) / np.sqrt(len(r))
        rows.append((nm, len(r), r.mean(), r.mean() / se,
                     float((r > 0).mean()) * 100))
    rows.sort(key=lambda x: -x[2])
    base = dict((r[0], r[2]) for r in rows).get("measured", 0.0)
    for nm, n, m, t, w in rows:
        mark = "  <- current" if nm == "measured" else ""
        print(f"  {nm:12s} n={n:6d}  {m:+7.3f}R  t={t:+6.2f}  "
              f"win {w:5.1f}%   vs measured {m-base:+7.3f}R{mark}")
    print()
    return rows


if __name__ == "__main__":
    print("TARGET STUDY — entry and stop held FIXED, only the exit varies\n")
    all_T = []
    for u in ("crypto_hourly", "etf"):
        T = collect(u)
        if len(T) < 100:
            print(f"  {u}: too few\n"); continue
        summarise(T, u.upper())
        all_T.append(T)
    if all_T:
        A = pd.concat(all_T, ignore_index=True)
        summarise(A, "COMBINED")
        summarise(A[A.diagonal], "COMBINED — diagonals only")
