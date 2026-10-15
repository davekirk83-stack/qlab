"""
DO CHART PATTERNS WORK AT ALL? — a general test across instruments and classes.

DK: "Investigate all of this level finding and resistance and trendline research
for application to all charts" ... "and patterns".

The level version of this test (levels_general.py) found that real levels do not
beat random fake levels anywhere. Patterns get the same treatment. patterns.py
already holds nine classical patterns written numerically; none of them have ever
been measured against a control.

THE TWO CONTROLS

1. RANDOM-DATE control. For each instrument, draw the same NUMBER of random bars
   the pattern fired on, from the same eligible window. If the pattern has no
   edge, it performs like its own random twin. This is the shadow book from
   paper.py applied to pattern detection.

2. BARRIER RACE, which needs no exit rule. P(+1 ATR before -1 ATR) over the next
   40 bars. Every earlier pattern verdict in this programme was contaminated by a
   fixed TP/SL geometry tuned on a different universe — doc 29's mistake. The
   race asks only whether price is more likely to go up first, which is the
   entry question on its own.

Also reported: forward return at 5/10/20 bars, and the confirmation wrappers
(volume, close strength, follow-through) since doc 24 found confirmation usually
costs more than it adds.

NO LOOKAHEAD. Patterns use only trailing windows. Outcomes use only later bars.
One signal per episode: a pattern that fires on consecutive bars counts once
(the standing rule from doc 33 — overlapping windows inflate t by ~10x).
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import patterns as PT
from levels_general import load_universe

RNG = np.random.default_rng(71)
GAP = 10          # bars that must pass before the same pattern counts again
FWD = (5, 10, 20)
RACE_BARS, RACE_K = 40, 1.0


def atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def dedupe(idx, gap=GAP):
    """One signal per episode."""
    out, last = [], -10**9
    for i in idx:
        if i - last >= gap:
            out.append(i); last = i
    return np.array(out, dtype=int)


def outcomes(df, idx, a):
    """Forward returns and the exit-free barrier race for each signal bar."""
    C, H, L = df.close.values, df.high.values, df.low.values
    n = len(C)
    rec = []
    for i in idx:
        if i + max(FWD) + RACE_BARS >= n or not np.isfinite(a[i]) or a[i] <= 0:
            continue
        r = {f"f{k}": C[i + k] / C[i] - 1 for k in FWD}
        up, dn = C[i] + RACE_K * a[i], C[i] - RACE_K * a[i]
        win = np.nan
        for j in range(i + 1, i + 1 + RACE_BARS):
            hit_u, hit_d = H[j] >= up, L[j] <= dn
            if hit_u and hit_d:
                win = 0.5; break          # same bar — unresolvable, split it
            if hit_u:
                win = 1.0; break
            if hit_d:
                win = 0.0; break
        r["race"] = win
        rec.append(r)
    return rec


def scan(panel, fn, args, conf=None):
    """Run one pattern over a whole universe. Returns (real, control) records."""
    real, ctrl = [], []
    for s, df in panel.items():
        if len(df) < 400:
            continue
        try:
            sig = fn(df, *args).fillna(0).values
        except Exception:
            continue
        if conf is not None:
            try:
                sig = sig * conf(df).fillna(0).values
            except Exception:
                continue
        a = atr(df).values
        warm = 120
        hits = dedupe(np.flatnonzero((sig > 0) & (np.arange(len(sig)) > warm)))
        if len(hits) == 0:
            continue
        real += outcomes(df, hits, a)
        # matched random control: same count, same eligible window
        lo, hi = warm, len(df) - max(FWD) - RACE_BARS - 1
        if hi > lo:
            fake = dedupe(np.sort(RNG.choice(np.arange(lo, hi),
                                             size=min(len(hits), hi - lo),
                                             replace=False)))
            ctrl += outcomes(df, fake, a)
    return real, ctrl


def line(lab, rec, pad=22):
    if len(rec) < 40:
        return None
    t = pd.DataFrame(rec)
    r = t.f10.values
    se = r.std(ddof=1) / np.sqrt(len(r))
    race = t.race.dropna()
    print(f"  {lab:{pad}s} n={len(r):5d}  "
          f"f5 {t.f5.mean()*100:+6.2f}%  f10 {r.mean()*100:+6.2f}%  "
          f"f20 {t.f20.mean()*100:+6.2f}%  t={r.mean()/se:+5.2f}  "
          f"race {race.mean()*100:5.1f}%")
    return dict(n=len(r), f10=r.mean(), race=race.mean() if len(race) else np.nan)


def run(which):
    panel = load_universe(which)
    print(f"\n{'='*104}")
    print(f"  {which.upper()}  —  {len(panel)} instruments")
    print(f"  race = P(+1 ATR before -1 ATR within 40 bars). 50% is a coin. "
          f"Control = matched random dates.")
    print(f"{'='*104}")
    rows = []
    for name, (fn, argsets) in PT.PATTERNS.items():
        for args in argsets:
            real, ctrl = scan(panel, fn, args)
            tag = f"{name}{list(args) if args else ''}"
            a = line(tag, real, pad=26)
            if a is None:
                continue
            b = line("    control", ctrl, pad=26)
            if b:
                print(f"    {'EDGE vs control':24s} "
                      f"f10 {(a['f10']-b['f10'])*100:+6.2f}pp   "
                      f"race {(a['race']-b['race'])*100:+5.1f}pp")
                rows.append(dict(universe=which, pattern=tag, n=a["n"],
                                 f10=a["f10"], race=a["race"],
                                 d_f10=a["f10"] - b["f10"],
                                 d_race=a["race"] - b["race"]))
            print()
    return rows


def confirms(which, keep):
    """Do the confirmation wrappers help the patterns that survived?"""
    panel = load_universe(which)
    if not keep:
        return
    print(f"\n{'='*104}")
    print(f"  CONFIRMATION WRAPPERS — {which.upper()}")
    print(f"{'='*104}")
    for name in keep:
        base = name.split("[")[0]
        fn, argsets = PT.PATTERNS[base]
        args = argsets[0]
        for cname, cfn in PT.CONFIRMS.items():
            real, _ = scan(panel, fn, args, conf=cfn)
            line(f"{base} + {cname}", real, pad=26)
        print()


if __name__ == "__main__":
    print("DO CHART PATTERNS WORK? — nine classical patterns vs matched random dates")
    all_rows = []
    for u in ("etf", "crypto_daily", "crypto_hourly"):
        all_rows += run(u)
    if all_rows:
        R = pd.DataFrame(all_rows)
        R.to_csv("/home/claude/qlab/runs/patterns_general.csv", index=False)
        print(f"\n{'='*104}")
        print("  SUMMARY — ranked by edge over control (10-bar forward)")
        print(f"{'='*104}")
        for _, r in R.sort_values("d_f10", ascending=False).head(14).iterrows():
            print(f"  {r.universe:14s} {r['pattern']:26s} n={r.n:5d}  "
                  f"edge {r.d_f10*100:+6.2f}pp   race edge {r.d_race*100:+5.1f}pp")
        print()
        pos = R[(R.d_f10 > 0) & (R.d_race > 0)]
        print(f"  patterns beating control on BOTH measures: {len(pos)} of {len(R)}")
        print(f"  (pure chance would give about {len(R)/4:.0f})")
