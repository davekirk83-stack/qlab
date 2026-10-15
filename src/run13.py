"""
RUN 13 — (A) BEAR-MARKET STRESS TEST and (B) MANAGEMENT-LAYER REFINEMENT.

A. THE TIDE-GOES-OUT TEST.
   The management layer earned +11.5%/trade on RANDOM entries across 2008-2026.
   That sample is dominated by huge uptrends. This isolates the falling periods
   and asks whether the plan bleeds or survives when the market is not helping.
   Regimes defined per-instrument (below its own 200d MA) AND by calendar for
   the known drawdowns: 2008 GFC, 2018 crypto winter, 2022 crypto winter / bear.

B. REFINEMENT.
   Run 12 showed ~91% of the return comes from management, not entry. So that is
   where the work belongs. Sweep the levers one at a time, measuring the effect
   on expectancy, median trade, win rate and — critically — BEAR-period result.
   A refinement that improves the bull number and worsens the bear number is not
   an improvement, it is leverage on a trend.
"""
import os, itertools, numpy as np, pandas as pd
import core as C
import levels as LV
from run10 import load_universe, atr, est_cost
from run12 import execute_plan

PANEL = load_universe()
COSTS = {s: est_cost(d) for s, d in PANEL.items()}

BEARS = [("2008 GFC", "2007-11-01", "2009-03-31"),
         ("2018 crypto winter", "2018-01-15", "2018-12-31"),
         ("2022 bear", "2021-11-15", "2022-12-31")]


def entry_fn(df):
    e = LV.l_break_prior_month_high(df)
    return pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)


def random_fn(df, rng, freq=0.02):
    return pd.Series((rng.random(len(df)) < freq).astype(float), index=df.index)


def collect(fn, **kw):
    rows = []
    for s, df in PANEL.items():
        try:
            e = fn(df)
        except Exception:
            continue
        if e.sum() == 0:
            continue
        for r, d in execute_plan(df, e, COSTS[s], **kw):
            rows.append((r, pd.Timestamp(d), s))
    d = pd.DataFrame(rows, columns=["ret", "date", "sym"])
    return d


def stat(r):
    r = np.asarray(r)
    if len(r) < 20:
        return None
    return dict(n=len(r), exp=float(r.mean()), med=float(np.median(r)),
                win=float((r > 0).mean()),
                t=float(r.mean() / (r.std() / np.sqrt(len(r)))) if r.std() > 0 else 0.0)


def regime_split(d):
    """Per-instrument regime: was the instrument above its own 200d MA at entry?"""
    bull, bear = [], []
    for s, df in PANEL.items():
        sub = d[d.sym == s]
        if not len(sub):
            continue
        ma = df.close.rolling(200).mean()
        above = (df.close > ma).reindex(sub.date).values
        bull.extend(sub.ret.values[above == True])
        bear.extend(sub.ret.values[above == False])
    return np.array(bull), np.array(bear)


def main():
    print("=" * 80)
    print("A.  BEAR-MARKET STRESS TEST")
    print("=" * 80)
    rng = np.random.default_rng(31)
    sig = collect(entry_fn)
    rnd = collect(lambda df: random_fn(df, rng))

    for label, d in (("SIGNAL entry", sig), ("RANDOM entry", rnd)):
        print(f"\n  {label}")
        full = stat(d.ret.values)
        print(f"    full sample      n={full['n']:5d}  exp {full['exp']*100:+8.3f}%  "
              f"med {full['med']*100:+7.3f}%  win {full['win']*100:5.1f}%")
        bull, bear = regime_split(d)
        for nm, arr in (("above 200d MA", bull), ("BELOW 200d MA", bear)):
            s = stat(arr)
            if s:
                print(f"    {nm:16s} n={s['n']:5d}  exp {s['exp']*100:+8.3f}%  "
                      f"med {s['med']*100:+7.3f}%  win {s['win']*100:5.1f}%")
        for nm, a, b in BEARS:
            m = (d.date >= a) & (d.date <= b)
            s = stat(d.ret.values[m.values])
            if s:
                print(f"    {nm:16s} n={s['n']:5d}  exp {s['exp']*100:+8.3f}%  "
                      f"med {s['med']*100:+7.3f}%  win {s['win']*100:5.1f}%  "
                      f"{'SURVIVES' if s['exp'] > 0 else 'BLEEDS'}")

    print()
    print("=" * 80)
    print("B.  MANAGEMENT REFINEMENT — one lever at a time")
    print("    (bull = above own 200d MA, bear = below. A change that helps bull")
    print("     and hurts bear is leverage on a trend, not an improvement.)")
    print("=" * 80)

    def report(label, **kw):
        d = collect(entry_fn, **kw)
        f = stat(d.ret.values)
        if not f:
            print(f"  {label:26s} too few trades"); return None
        bull, bear = regime_split(d)
        sb, sr = stat(bull), stat(bear)
        print(f"  {label:26s} exp {f['exp']*100:+8.3f}%  med {f['med']*100:+6.3f}%  "
              f"win {f['win']*100:5.1f}%  bull {sb['exp']*100 if sb else 0:+7.2f}%  "
              f"bear {sr['exp']*100 if sr else 0:+7.2f}%  n={f['n']}")
        return dict(label=label, exp=f["exp"], med=f["med"], win=f["win"],
                    bull=sb["exp"] if sb else 0, bear=sr["exp"] if sr else 0)

    rows = []
    print("\n  BASELINE")
    rows.append(report("baseline"))

    print("\n  STOP DISTANCE")
    for x in (1.0, 1.5, 2.0, 3.0):
        rows.append(report(f"stop {x} ATR", stop_atr=x))

    print("\n  TRAIL DISTANCE ON THE RUNNER")
    for x in (1.5, 2.5, 4.0, 6.0):
        rows.append(report(f"trail {x} ATR", trail_atr=x))

    print("\n  TP1 PLACEMENT")
    for x in (0.5, 1.0, 1.5, 2.0):
        rows.append(report(f"TP1 at {x}R", tp1_r=x))

    print("\n  TP2 FIB EXTENSION")
    for x in (1.272, 1.618, 2.0, 2.618):
        rows.append(report(f"TP2 fib {x}", tp2_k=x))

    print("\n  TIME STOP")
    for x in (20, 40, 60, 120):
        rows.append(report(f"time stop {x} bars", max_bars=x))

    print("\n  BREAKEVEN+ OFFSET AFTER TP1")
    for x in (0.0, 0.10, 0.25):
        rows.append(report(f"BE +{x}R", be_offset_r=x))

    rows = [r for r in rows if r]
    df = pd.DataFrame(rows)
    base = df[df.label == "baseline"].iloc[0]
    df["d_exp"] = df.exp - base.exp
    df["d_bear"] = df.bear - base.bear
    good = df[(df.d_exp > 0) & (df.d_bear >= 0)].sort_values("d_exp", ascending=False)
    print()
    print("=" * 80)
    print("  REFINEMENTS THAT IMPROVE EXPECTANCY **WITHOUT** WORSENING THE BEAR CASE")
    print("=" * 80)
    if len(good):
        for _, r in good.iterrows():
            print(f"    {r['label']:26s} exp {r['d_exp']*100:+.3f}pp   "
                  f"bear {r['d_bear']*100:+.3f}pp")
    else:
        print("    none — every expectancy gain came at the cost of the bear case")

    cum = C.ledger_bump(len(rows) + 2, "run13: bear stress + management refinement")
    print(f"\nLIFETIME TRIALS: {cum}")
    df.to_csv("/home/claude/qlab/runs/run13.csv", index=False)


if __name__ == "__main__":
    main()
